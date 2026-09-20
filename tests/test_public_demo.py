import os
import runpy
from unittest.mock import patch
from uuid import UUID

import pytest
from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import URLPattern, URLResolver, get_resolver
from philanthra.core import models as m
from philanthra.demo.seed import PASSWORD, seed_demo
from philanthra.pilot.models import WorkspaceProfile
from rest_framework.test import APIClient


def api_paths(patterns=None, prefix=""):
    """Exercise the actual URL tree, including every newly registered API route."""
    for entry in patterns if patterns is not None else get_resolver().url_patterns:
        route = prefix + str(entry.pattern)
        if isinstance(entry, URLResolver):
            yield from api_paths(entry.url_patterns, route)
        elif isinstance(entry, URLPattern):
            yield "/" + route.replace("<uuid:pk>", str(UUID(int=1)))


def content_snapshot():
    return {
        model._meta.label: list(model.objects.order_by("pk").values())
        for label in ("core", "pilot", "catalog")
        for model in apps.get_app_config(label).get_models()
    }


@override_settings(DEMO_MODE=True, DEMO_READ_ONLY=True)
class PublicDemoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        seed_demo()

    def setUp(self):
        cache.clear()

    def sign_in(self, username):
        client = APIClient(enforce_csrf_checks=True)
        session = client.get("/api/v1/session/").json()["data"]
        self.assertTrue(session["demo_read_only"])
        response = client.post(
            "/api/v1/login/",
            {"username": username, "password": PASSWORD},
            format="json",
            HTTP_X_CSRFTOKEN=session["csrfToken"],
        )
        self.assertEqual(response.status_code, 200, response.content)
        session = response.json()["data"]
        self.assertEqual(session["user"]["username"], username)
        self.assertTrue(session["demo_read_only"])
        client.credentials(
            HTTP_X_CSRFTOKEN=session["csrfToken"],
            HTTP_X_WORKSPACE_ID=session["workspaces"][0]["id"],
        )
        return client

    def test_all_demo_roles_can_sign_in_read_and_sign_out(self):
        for username in ("foundation-admin", "ngo-owner", "reviewer"):
            with self.subTest(username=username):
                client = self.sign_in(username)
                before = content_snapshot()
                for path in ("/api/v1/organizations/", "/api/v1/dashboard/", "/api/v1/session/"):
                    response = client.get(path)
                    self.assertEqual(response.status_code, 200, response.content)
                self.assertEqual(content_snapshot(), before)
                self.assertEqual(client.post("/api/v1/logout/").status_code, 200)
                self.assertIsNone(client.get("/api/v1/session/").json()["data"]["user"])

    def test_every_route_denies_unsafe_methods_for_anonymous_demo_roles_and_staff(self):
        paths = list(api_paths())
        for username in (None, "foundation-admin", "ngo-owner", "reviewer", "platform-admin"):
            client = self.sign_in(username) if username else APIClient(enforce_csrf_checks=True)
            before = content_snapshot()
            users_before = list(get_user_model().objects.order_by("pk").values())
            for path in paths:
                for method in ("POST", "PATCH", "PUT", "DELETE"):
                    if method == "POST" and path in ("/api/v1/login/", "/api/v1/logout/"):
                        continue
                    with self.subTest(username=username, path=path, method=method):
                        response = client.generic(
                            method, path, "{}", content_type="application/json"
                        )
                        self.assertEqual(response.status_code, 403, response.content)
                        self.assertEqual(response.json()["error"]["code"], "demo_read_only")
            self.assertEqual(content_snapshot(), before)
            self.assertEqual(list(get_user_model().objects.order_by("pk").values()), users_before)

    def test_real_mutation_targets_and_forged_headers_cannot_bypass_guard(self):
        client = self.sign_in("ngo-owner")
        member = m.Membership.objects.get(user__username="ngo-owner")
        source = m.Source.objects.filter(owner=member.workspace).first()
        program = m.Program.objects.filter(owner=member.workspace).first()
        before = content_snapshot()
        attempts = [
            ("patch", f"/api/v1/programs/{program.id}/", {"name": "Defaced", "revision": 1}),
            ("post", f"/api/v1/sources/{source.id}/withdraw/", {}),
            ("patch", "/api/v1/members/", {"id": str(member.id), "role": "viewer"}),
            ("post", "/api/v1/invitations/", {"email": "visitor@example.invalid"}),
            ("post", "/api/v1/invitations/redeem/", {"username": "public-created"}),
            ("post", "/api/v1/pilot/password-reset/request/", {"email": "ngo-owner@demo.invalid"}),
            ("post", "/api/v1/pilot/password-reset/confirm/", {"password": "Replacement-abc123!"}),
            ("post", "/api/v1/pilot/workspaces/", {"name": "Defaced", "kind": "ngo"}),
        ]
        for method, path, payload in attempts:
            with self.subTest(path=path):
                response = getattr(client, method)(
                    path,
                    payload,
                    format="json",
                    HTTP_HOST="localhost",
                    HTTP_X_FORWARDED_HOST="localhost",
                    HTTP_X_HTTP_METHOD_OVERRIDE="GET",
                    HTTP_X_DEMO_READ_ONLY="0",
                )
                self.assertEqual(response.status_code, 403)
                self.assertEqual(response.json()["error"]["code"], "demo_read_only")
        self.assertEqual(content_snapshot(), before)

    def test_login_and_logout_still_require_csrf(self):
        client = APIClient(enforce_csrf_checks=True)
        self.assertEqual(
            client.post(
                "/api/v1/login/", {"username": "ngo-owner", "password": PASSWORD}, format="json"
            ).json()["error"]["code"],
            "csrf_failed",
        )
        client = self.sign_in("ngo-owner")
        client.credentials()
        self.assertEqual(client.post("/api/v1/logout/").status_code, 403)
        self.assertEqual(
            client.get("/api/v1/session/").json()["data"]["user"]["username"], "ngo-owner"
        )

    def test_get_and_head_defaults_do_not_create_subscription_or_profile_records(self):
        client = self.sign_in("ngo-owner")
        workspace = m.Membership.objects.get(user__username="ngo-owner").workspace
        m.Subscription.objects.filter(owner=workspace).delete()
        WorkspaceProfile.objects.filter(owner=workspace).delete()
        before = content_snapshot()
        for path in ("/api/v1/subscriptions/", "/api/v1/pilot/profile/"):
            self.assertEqual(client.get(path).status_code, 200)
            self.assertEqual(client.head(path).status_code, 200)
        self.assertEqual(content_snapshot(), before)

    def test_normal_demo_mode_retains_existing_writes(self):
        client = self.sign_in("ngo-owner")
        with override_settings(DEMO_READ_ONLY=False):
            self.assertFalse(client.get("/api/v1/session/").json()["data"]["demo_read_only"])
            response = client.post(
                "/api/v1/pilot/workspaces/", {"name": "Editable demo", "kind": "ngo"}, format="json"
            )
            self.assertEqual(response.status_code, 201, response.content)
            self.assertTrue(m.Workspace.objects.filter(name="Editable demo").exists())

    def test_read_only_setting_cannot_enable_demo_mode_elsewhere(self):
        client = self.sign_in("ngo-owner")
        with override_settings(DEMO_MODE=False):
            self.assertFalse(client.get("/api/v1/session/").json()["data"]["demo_read_only"])
            self.assertEqual(
                client.post(
                    "/api/v1/pilot/workspaces/",
                    {"name": "Normal pilot", "kind": "ngo"},
                    format="json",
                ).status_code,
                201,
            )


@pytest.mark.parametrize(
    "environment,flag,expected",
    [("demo", "1", True), ("demo", "0", False), ("test", "1", False), ("development", "1", False)],
)
def test_public_demo_environment_is_explicitly_opt_in(environment, flag, expected):
    with patch.dict(os.environ, {"PHILANTHRA_ENV": environment, "PHILANTHRA_DEMO_READ_ONLY": flag}):
        settings = runpy.run_path("apps/api/config/settings.py")
    assert settings["DEMO_READ_ONLY"] is expected
