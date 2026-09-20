import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.password_validation import validate_password
from django.core.cache import cache
from django.db import transaction
from django.middleware.csrf import get_token
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from philanthra.core.models import Invitation, Membership
from philanthra.core.policy import workspace_for


def session_data(request):
    user = request.user
    return {
        "user": {"id": user.id, "username": user.username} if user.is_authenticated else None,
        "workspaces": [
            {
                "id": str(m.workspace_id),
                "name": m.workspace.name,
                "kind": m.workspace.kind,
                "role": m.role,
                "organization_id": str(m.workspace.organization_id)
                if m.workspace.organization_id
                else None,
            }
            for m in Membership.objects.filter(user=user).select_related("workspace")
        ]
        if user.is_authenticated
        else [],
        "csrfToken": get_token(request),
        "demo_mode": settings.DEMO_MODE,
        "demo_read_only": settings.DEMO_MODE and settings.DEMO_READ_ONLY,
    }


@method_decorator(ensure_csrf_cookie, name="dispatch")
class SessionView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"data": session_data(request), "meta": {}})


@method_decorator(csrf_protect, name="dispatch")
class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = str(request.data.get("username", ""))[:150]
        key = (
            "login:"
            + hashlib.sha256(
                (request.META.get("REMOTE_ADDR", "") + ":" + username).encode()
            ).hexdigest()
        )
        failures = cache.get(key, 0)
        if failures >= 10:
            raise PermissionDenied("Too many attempts. Try again in 15 minutes.")
        user = authenticate(request, username=username, password=request.data.get("password", ""))
        if user is None:
            cache.set(key, failures + 1, 900)
            raise PermissionDenied("Invalid credentials.")
        cache.delete(key)
        login(request, user)
        return Response({"data": session_data(request), "meta": {}})


class LogoutView(APIView):
    def post(self, request):
        logout(request)
        return Response({"data": {"logged_out": True}, "meta": {}})


class MembersView(APIView):
    def get(self, request):
        ws = workspace_for(request)
        return Response(
            {
                "data": [
                    {
                        "id": str(m.id),
                        "user_id": m.user_id,
                        "username": m.user.username,
                        "role": m.role,
                    }
                    for m in Membership.objects.filter(workspace=ws).select_related("user")
                ],
                "meta": {},
            }
        )

    def patch(self, request):
        ws = workspace_for(request, admin=True)
        member = Membership.objects.filter(workspace=ws, id=request.data.get("id")).first()
        if not member:
            raise PermissionDenied("Membership unavailable.")
        if member.role == "owner":
            raise ValidationError({"role": "Owner transfer requires a separate identity review."})
        role = request.data.get("role")
        if role not in {"administrator", "analyst", "editor", "viewer", "reviewer"}:
            raise ValidationError({"role": "Unsupported role."})
        if role == "reviewer" and not request.user.is_staff:
            raise PermissionDenied("Trusted reviewer provisioning requires a platform operator.")
        member.role = role
        member.save()
        return Response({"data": {"id": str(member.id), "role": role}, "meta": {}})


class InvitationsView(APIView):
    def post(self, request):
        ws = workspace_for(request, admin=True)
        role = request.data.get("role", "viewer")
        if role not in {"analyst", "editor", "viewer", "reviewer"}:
            raise ValidationError({"role": "Unsupported invitation role."})
        if role == "reviewer" and not request.user.is_staff:
            raise PermissionDenied("Trusted reviewer invitations require a platform operator.")
        from django.core.validators import validate_email

        email = request.data.get("email", "")
        validate_email(email)
        token = secrets.token_urlsafe(32)
        invitation = Invitation.objects.create(
            workspace=ws,
            email=email,
            role=role,
            token_hash=hashlib.sha256(token.encode()).hexdigest(),
            expires_at=timezone.now() + timedelta(days=3),
            invited_by=request.user,
        )
        return Response(
            {
                "data": {
                    "id": str(invitation.id),
                    "token": token,
                    "expires_at": invitation.expires_at,
                    "delivery": "Manual secure handoff; no email sent.",
                },
                "meta": {},
            },
            status=201,
        )


@method_decorator(csrf_protect, name="dispatch")
class RedeemView(APIView):
    permission_classes = [AllowAny]

    @transaction.atomic
    def post(self, request):
        invitation = (
            Invitation.objects.select_for_update()
            .filter(
                token_hash=hashlib.sha256(str(request.data.get("token", "")).encode()).hexdigest(),
                redeemed_at__isnull=True,
                expires_at__gt=timezone.now(),
            )
            .first()
        )
        if not invitation:
            raise ValidationError({"token": "Invalid or expired invitation."})
        username = str(request.data.get("username", "")).strip()
        password = request.data.get("password", "")
        if not username or get_user_model().objects.filter(username=username).exists():
            raise ValidationError({"username": "Choose an available username."})
        validate_password(password)
        user = get_user_model().objects.create_user(
            username=username, email=invitation.email, password=password
        )
        Membership.objects.create(user=user, workspace=invitation.workspace, role=invitation.role)
        invitation.redeemed_at = timezone.now()
        invitation.save()
        login(request, user)
        return Response({"data": session_data(request), "meta": {}}, status=201)
