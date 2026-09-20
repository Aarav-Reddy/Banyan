import hashlib
import os
from urllib.parse import urlparse

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.cache import cache
from django.core.mail import send_mail
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.views.decorators.csrf import csrf_protect
from rest_framework.exceptions import APIException, NotFound, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.renderers import BaseRenderer, JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from philanthra.core import models as c
from philanthra.core.policy import can_artifact, workspace_for
from philanthra.core.serializers import CardSerializer
from philanthra.core.services import Conflict, audit, create_artifact, enqueue
from philanthra.ingestion import safe_csv

from .models import Bookmark, ContactConsent, IdentityClaim, WatchItem, WorkspaceProfile
from .services import add_watch, financial_benchmark, impact_report


def ok(data, status=200):
    return Response({"data": data, "meta": {}}, status=status)


def claim_data(claim):
    return {
        "id": str(claim.id),
        "artifact_id": str(claim.artifact_id),
        "organization": {"id": str(claim.organization_id), "name": claim.organization.name},
        "status": claim.artifact.status,
        "revision": claim.artifact.revision,
        "statement": claim.statement,
        "proof_source_id": str(claim.proof_source_id),
        "linked_revision": claim.linked_revision,
    }


class WorkspacesView(APIView):
    @transaction.atomic
    def post(self, request):
        # Existing authenticated invite-pilot accounts can create independent workspaces.
        get_user_model().objects.select_for_update().get(pk=request.user.pk)
        if c.Membership.objects.filter(user=request.user, role="owner").count() >= 10:
            raise ValidationError({"name": "Pilot limit: ten owned workspaces per account."})
        if set(request.data) - {"name", "kind"}:
            raise ValidationError(
                {"workspace": "Public identity linkage requires a separate reviewed claim."}
            )
        name = str(request.data.get("name", "")).strip()
        kind = request.data.get("kind")
        if not 1 <= len(name) <= 160 or kind not in {"ngo", "foundation"}:
            raise ValidationError({"workspace": "Provide a name and ngo or foundation kind."})
        workspace = c.Workspace.objects.create(
            name=name, kind=kind, plan="contributor_free" if kind == "ngo" else "foundation_pilot"
        )
        c.Membership.objects.create(workspace=workspace, user=request.user, role="owner")
        audit(workspace, request.user, "workspace.created", workspace.id)
        return ok(
            {
                "id": str(workspace.id),
                "name": name,
                "kind": kind,
                "role": "owner",
                "organization_id": None,
            },
            201,
        )


class IdentityClaimsView(APIView):
    def get(self, request):
        workspace = workspace_for(request)
        claims = IdentityClaim.objects.filter(artifact__owner=workspace).select_related(
            "artifact", "organization"
        )
        return ok(
            [claim_data(claim) for claim in claims if can_artifact(claim.artifact, workspace)]
        )

    @transaction.atomic
    def post(self, request):
        workspace = workspace_for(request, admin=True)
        if workspace.kind != "ngo" or workspace.organization_id:
            raise ValidationError(
                {"organization_id": "Use an unlinked NGO workspace for identity verification."}
            )
        organization = get_object_or_404(c.Organization, pk=request.data.get("organization_id"))
        source = get_object_or_404(
            c.Source, pk=request.data.get("proof_source_id"), owner=workspace, state="active"
        )
        statement = str(request.data.get("statement", "")).strip()
        if len(statement) < 20 or len(statement) > 4000:
            raise ValidationError(
                {"statement": "Describe the authority and source locator in 20–4000 characters."}
            )
        if source.upload_identifier == "manual-draft" and not source.locator:
            raise ValidationError(
                {"proof_source_id": "Identity evidence needs a retrievable proof locator."}
            )
        artifact = create_artifact(
            workspace,
            request.user,
            kind="identity_claim",
            title=f"Identity claim: {organization.name}",
            sources=[source],
            payload={
                "organization_id": str(organization.id),
                "statement": statement,
                "verification_scope": "Authority to represent this organization, subject to independent human review.",
            },
        )
        claim = IdentityClaim.objects.create(
            artifact=artifact, organization=organization, proof_source=source, statement=statement
        )
        return ok(claim_data(claim), 201)


class ServiceUnavailable(APIException):
    status_code = 503
    default_code = "unavailable"


@method_decorator(csrf_protect, name="dispatch")
class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = str(request.data.get("email", "")).strip()
        from django.core.validators import validate_email

        validate_email(email)
        public_origin = os.getenv("PHILANTHRA_PUBLIC_ORIGIN", "http://localhost:8080").rstrip("/")
        if settings.ENVIRONMENT == "production":
            if (
                os.getenv("PHILANTHRA_PASSWORD_RESET_EMAIL_ENABLED") != "1"
                or urlparse(public_origin).scheme != "https"
                or settings.EMAIL_BACKEND
                in {
                    "django.core.mail.backends.filebased.EmailBackend",
                    "django.core.mail.backends.console.EmailBackend",
                    "django.core.mail.backends.locmem.EmailBackend",
                    "django.core.mail.backends.dummy.EmailBackend",
                }
            ):
                raise ServiceUnavailable(
                    "Password reset email is not configured for this deployment."
                )
        throttle = (
            "reset:"
            + hashlib.sha256(
                (request.META.get("REMOTE_ADDR", "") + email.lower()).encode()
            ).hexdigest()
        )
        attempts = cache.get(throttle, 0)
        accepted = {
            "accepted": True,
            "message": "If an eligible account exists, password reset instructions have been requested. Contact your workspace administrator if no email arrives.",
        }
        if attempts >= 3:
            return ok(accepted, 202)
        cache.set(throttle, attempts + 1, 900)
        for user in get_user_model().objects.filter(email__iexact=email, is_active=True):
            if not user.has_usable_password():
                continue
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            link = f"{public_origin}/password-reset?uid={uid}&token={token}"
            try:
                send_mail(
                    "Reset your Philanthra password",
                    f"A password reset was requested for your Philanthra account.\n\nOpen {link}\n\nIf you did not request this, ignore this message. The link expires and becomes invalid after use.",
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    fail_silently=False,
                )
            except Exception:
                # Do not reveal whether an address exists when the configured mail boundary fails.
                cache.set("password_reset_delivery_unavailable", True, 900)
        return ok(accepted, 202)


@method_decorator(csrf_protect, name="dispatch")
class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    @transaction.atomic
    def post(self, request):
        user = None
        try:
            uid = force_str(urlsafe_base64_decode(str(request.data.get("uid", ""))))
            user = (
                get_user_model().objects.select_for_update().filter(pk=uid, is_active=True).first()
            )
        except (ValueError, TypeError, OverflowError, UnicodeDecodeError):
            pass
        token = str(request.data.get("token", ""))
        if not user or not default_token_generator.check_token(user, token):
            raise ValidationError({"token": "Invalid or expired password reset link."})
        password = request.data.get("password", "")
        validate_password(password, user=user)
        user.set_password(password)
        user.save(update_fields=["password"])
        return ok({"reset": True, "message": "Password updated. Sign in with the new password."})


class BookmarksView(APIView):
    def get(self, request):
        workspace = workspace_for(request)
        return ok(
            [
                {"id": str(bookmark.id), "artifact": CardSerializer(bookmark.artifact).data}
                for bookmark in Bookmark.objects.filter(owner=workspace).select_related("artifact")
                if can_artifact(bookmark.artifact, workspace)
            ]
        )

    def post(self, request):
        workspace = workspace_for(request, write=True)
        artifact = get_object_or_404(c.Artifact, pk=request.data.get("artifact_id"), kind="card")
        if not can_artifact(artifact, workspace):
            raise NotFound()
        bookmark, _ = Bookmark.objects.get_or_create(owner=workspace, artifact=artifact)
        return ok({"id": str(bookmark.id), "artifact_id": str(artifact.id)}, 201)


class BookmarkDetailView(APIView):
    def delete(self, request, pk):
        bookmark = get_object_or_404(Bookmark, pk=pk, owner=workspace_for(request, write=True))
        bookmark.delete()
        return ok({"deleted": True})


class WatchlistView(APIView):
    def get(self, request):
        workspace = workspace_for(request)
        return ok(
            [
                {
                    "id": str(w.id),
                    "organization_id": str(w.organization_id),
                    "organization_name": w.organization.name,
                    "last_checked_at": w.snapshot.updated_at,
                    "monitor_status": "watching",
                }
                for w in WatchItem.objects.filter(
                    owner=workspace, source__state="active"
                ).select_related("organization", "snapshot")
            ]
        )

    def post(self, request):
        workspace = workspace_for(request, write=True)
        org = get_object_or_404(c.Organization, pk=request.data.get("organization_id"))
        watch = add_watch(workspace, request.user, org)
        return ok(
            {
                "id": str(watch.id),
                "organization_id": str(org.id),
                "organization_name": org.name,
                "monitor_status": "watching",
            },
            201,
        )


class WatchDetailView(APIView):
    def delete(self, request, pk):
        watch = get_object_or_404(WatchItem, pk=pk, owner=workspace_for(request, write=True))
        watch.delete()
        return ok({"deleted": True})


class MonitorView(APIView):
    def post(self, request):
        workspace = workspace_for(request, write=True)
        # One pending recomputation per workspace; completed work uses a fresh idempotency key.
        pending = c.Job.objects.filter(
            owner=workspace, kind="pilot_monitor", state__in=["queued", "processing"]
        ).first()
        if pending:
            job = pending
        else:
            job = enqueue(
                workspace, "pilot_monitor", f"monitor:{workspace.id}:{timezone.now().isoformat()}"
            )
        return ok({"job_id": str(job.id), "state": job.state}, 202)


class CSVRenderer(BaseRenderer):
    media_type = "text/csv"
    format = "csv"
    charset = "utf-8"

    def render(self, data, accepted_media_type=None, renderer_context=None):
        return safe_csv(data if isinstance(data, list) else [data]).encode("utf-8")


class ImpactReportView(APIView):
    renderer_classes = [JSONRenderer, CSVRenderer]

    def get(self, request):
        workspace = workspace_for(request)
        report = impact_report(workspace)
        audit(workspace, request.user, "impact_report.exported", workspace.id)
        if request.query_params.get("format") == "csv":
            rows = []
            for row in report["observations"]:
                rows.append(
                    {
                        "record_type": "outcome",
                        **row,
                        "report_status": "draft",
                        "caveat": "Source reported aggregate; no causal attribution.",
                    }
                )
            for row in report["costs"]:
                rows.append(
                    {
                        "record_type": "cost",
                        **row,
                        "report_status": "draft",
                        "caveat": "Different units, currencies or periods are not combined.",
                    }
                )
            response = HttpResponse(safe_csv(rows), content_type="text/csv")
            response["Content-Disposition"] = (
                'attachment; filename="philanthra-impact-report-draft.csv"'
            )
            return response
        return ok(report)


class BenchmarkView(APIView):
    def get(self, request):
        return ok(financial_benchmark(workspace_for(request)))


def profile_data(profile):
    return {
        "mission": profile.mission,
        "cause": profile.cause,
        "population": profile.population,
        "service_area_codes": profile.service_area_codes,
        "context": profile.context,
        "revision": profile.revision,
        "visibility": "private workspace profile; service areas are owner-reported and not verified boundaries",
    }


class ProfileView(APIView):
    def get(self, request):
        workspace = workspace_for(request)
        if settings.DEMO_MODE and settings.DEMO_READ_ONLY:
            profile = WorkspaceProfile.objects.filter(owner=workspace).first() or WorkspaceProfile(
                owner=workspace
            )
        else:
            profile, _ = WorkspaceProfile.objects.get_or_create(owner=workspace)
        return ok(profile_data(profile))

    @transaction.atomic
    def patch(self, request):
        workspace = workspace_for(request, admin=True)
        profile, _ = WorkspaceProfile.objects.get_or_create(owner=workspace)
        profile = WorkspaceProfile.objects.select_for_update().get(pk=profile.pk)
        if request.data.get("revision") != profile.revision:
            raise Conflict()
        allowed = {"revision", "mission", "cause", "population", "service_area_codes", "context"}
        if set(request.data) - allowed:
            raise ValidationError({"profile": "Unsupported profile fields."})
        areas = request.data.get("service_area_codes", profile.service_area_codes)
        if (
            not isinstance(areas, list)
            or len(areas) > 30
            or any(not isinstance(code, str) for code in areas)
        ):
            raise ValidationError({"service_area_codes": "Provide up to 30 explicit area codes."})
        if set(areas) - set(
            c.Geography.objects.filter(
                code__in=areas, source__owner__isnull=True, source__state="active"
            ).values_list("code", flat=True)
        ):
            raise ValidationError(
                {
                    "service_area_codes": "Choose known public geography codes; ZIP and ZCTA are distinct."
                }
            )
        context = request.data.get("context", profile.context)
        if not isinstance(context, dict) or len(str(context)) > 10000:
            raise ValidationError({"context": "Provide a bounded context object."})
        for field in ["mission", "cause", "population", "service_area_codes", "context"]:
            if field in request.data:
                setattr(profile, field, request.data[field])
        profile.revision += 1
        profile.full_clean()
        profile.save()
        audit(workspace, request.user, "profile.updated", profile.id, revision=profile.revision)
        return ok(profile_data(profile))


class ContactView(APIView):
    def get(self, request):
        contact = ContactConsent.objects.filter(owner=workspace_for(request, admin=True)).first()
        return ok(
            {
                "name": contact.name,
                "email": contact.email,
                "enabled": contact.enabled,
                "revision": contact.revision,
            }
            if contact
            else {"name": "", "email": "", "enabled": False, "revision": 0}
        )

    @transaction.atomic
    def put(self, request):
        workspace = workspace_for(request, admin=True)
        contact, _ = ContactConsent.objects.get_or_create(
            owner=workspace, defaults={"email": "", "name": ""}
        )
        contact = ContactConsent.objects.select_for_update().get(pk=contact.pk)
        if request.data.get("revision") not in {0 if not contact.email else contact.revision}:
            raise Conflict()
        if not isinstance(request.data.get("enabled"), bool):
            raise ValidationError({"enabled": "Explicit contact consent required."})
        contact.name = str(request.data.get("name", ""))
        contact.email = str(request.data.get("email", ""))
        contact.enabled = request.data["enabled"]
        contact.revision += 1
        contact.full_clean()
        contact.save()
        return ok(
            {
                "name": contact.name,
                "email": contact.email,
                "enabled": contact.enabled,
                "revision": contact.revision,
            }
        )


class IntroductionInboxView(APIView):
    def get(self, request):
        workspace = workspace_for(request)
        return ok(
            [
                {
                    "id": str(item.id),
                    "from_workspace": item.owner.name,
                    "note": item.note,
                    "state": item.state,
                }
                for item in c.ServiceRequest.objects.filter(
                    target=workspace, kind="introduction"
                ).select_related("owner")
            ]
        )


class IntroductionDecisionView(APIView):
    def post(self, request, pk):
        workspace = workspace_for(request, admin=True)
        item = get_object_or_404(c.ServiceRequest, pk=pk, target=workspace, kind="introduction")
        state = request.data.get("state")
        if state not in {"accepted", "declined"}:
            raise ValidationError({"state": "Accept or decline the request."})
        item.state = state
        item.save()
        audit(workspace, request.user, "introduction.decided", item.id, state=state)
        return ok(
            {"id": str(item.id), "state": state, "delivery": "No outbound introduction was sent."}
        )


class IntroductionContactView(APIView):
    def get(self, request, pk):
        workspace = workspace_for(request)
        item = get_object_or_404(
            c.ServiceRequest, pk=pk, owner=workspace, kind="introduction", state="accepted"
        )
        contact = ContactConsent.objects.filter(owner=item.target, enabled=True).first()
        if not contact:
            raise NotFound()
        return ok(
            {
                "name": contact.name,
                "email": contact.email,
                "consent_revision": contact.revision,
                "delivery": "Permissioned contact for manual follow-up; no message was sent.",
            }
        )


class IdentityProofView(APIView):
    def get(self, request, pk):
        workspace = workspace_for(request)
        claim = get_object_or_404(IdentityClaim, artifact_id=pk)
        if not can_artifact(claim.artifact, workspace, user=request.user):
            raise NotFound()
        batch = c.ImportBatch.objects.filter(source=claim.proof_source).first()
        from philanthra.core.serializers import SourceSerializer

        audit(
            claim.artifact.owner,
            request.user,
            "identity.proof_viewed",
            claim.id,
            revision=claim.artifact.revision,
        )
        return ok(
            {
                "source": SourceSerializer(claim.proof_source).data,
                "statement": claim.statement,
                "document_preview": batch.preview
                if batch and batch.status == "quarantined"
                else [],
                "validation_status": batch.status if batch else "manual_attestation",
                "limitation": "Source text is untrusted evidence. The reviewer must independently verify authority; a manual attestation alone does not establish identity.",
            }
        )
