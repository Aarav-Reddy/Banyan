"""Explicit transport documentation shared by the OpenAPI generator and typed client."""

from drf_spectacular.utils import (
    OpenApiParameter,
    extend_schema,
    extend_schema_view,
    inline_serializer,
)
from rest_framework import serializers

from . import serializers as s


def envelope(name, field):
    return inline_serializer(name=name, fields={"data": field, "meta": serializers.DictField()})


def object_request(name, fields):
    return inline_serializer(name=name, fields=fields)


def apply_schema():
    from philanthra.accounts import views as accounts

    from . import views as v

    def uuid(**kwargs):
        return serializers.UUIDField(**kwargs)

    def text(**kwargs):
        return serializers.CharField(**kwargs)

    def number(**kwargs):
        return serializers.IntegerField(**kwargs)

    lists = {
        v.OrganizationsView: s.OrganizationSerializer,
        v.PortfoliosView: s.PortfolioSerializer,
        v.ProgramsView: s.ProgramSerializer,
        v.CardsView: s.CardSerializer,
        v.SourcesView: s.SourceSerializer,
        v.SourceIssuesView: s.ArtifactSerializer,
        v.GrantsView: s.GrantSerializer,
        v.ObservationsView: s.ObservationSerializer,
        v.AnalysesView: s.ArtifactSerializer,
        v.ReviewsView: s.ArtifactSerializer,
        v.AlertsView: s.AlertSerializer,
        v.JobsView: s.JobSerializer,
        v.ImportsView: s.ImportSerializer,
    }
    details = {
        v.PortfolioDetailView: s.PortfolioSerializer,
        v.CardDetailView: s.CardSerializer,
        v.SourceDetailView: s.SourceSerializer,
        v.JobDetailView: s.JobSerializer,
        v.ImportDetailView: s.ImportSerializer,
        v.ReportView: s.ArtifactSerializer,
    }
    requests = {
        v.SourceIssuesView: {"source_id": uuid(), "title": text(), "issue": text(max_length=4000)},
        accounts.LoginView: {"username": text(), "password": text(write_only=True)},
        accounts.InvitationsView: {
            "email": serializers.EmailField(),
            "role": serializers.ChoiceField(choices=["analyst", "editor", "viewer", "reviewer"]),
        },
        accounts.RedeemView: {
            "token": text(),
            "username": text(),
            "password": text(write_only=True),
        },
        v.PortfoliosView: {
            "name": text(),
            "budget_cents": number(min_value=0),
            "currency": text(default="USD"),
            "candidates": serializers.ListField(
                child=inline_serializer(
                    name="AllocationCandidate",
                    fields={
                        "organization_id": uuid(),
                        "dimensions": serializers.DictField(
                            child=serializers.CharField(
                                allow_null=True, allow_blank=True, max_length=1000
                            ),
                            required=False,
                        ),
                        "cap_cents": number(min_value=0, allow_null=True, required=False),
                        "assumption_note": text(required=False),
                        "weight": serializers.DecimalField(
                            max_digits=12, decimal_places=4, required=False
                        ),
                        "minimum_cents": number(min_value=0, required=False),
                        "excluded": serializers.BooleanField(required=False),
                    },
                )
            ),
            "constraints": serializers.DictField(required=False),
        },
        v.ProgramsView: {
            "source_id": uuid(),
            "name": text(),
            "cause": text(),
            "intervention": text(),
            "population": text(),
            "geography": text(),
            "context": serializers.DictField(required=False),
        },
        v.CardsView: {
            "program_id": uuid(),
            "title": text(),
            "summary": text(required=False),
            "evidence_label": text(),
            "study_design": text(required=False),
            "implementation_steps": text(required=False),
            "barriers": text(required=False),
            "failures": text(required=False),
            "caveats": text(required=False),
            "attribution": text(required=False),
            "claims": serializers.ListField(child=serializers.DictField(), required=False),
        },
        v.SourcesView: {
            "title": text(),
            "cause": text(required=False),
            "geography": text(required=False),
            "locator": text(required=False),
        },
        v.GrantsView: {
            "source_id": uuid(),
            "purpose": serializers.ChoiceField(
                choices=[
                    "benchmarking",
                    "pooled_analysis",
                    "donor_access",
                    "publication",
                    "external_ai",
                ]
            ),
            "recipient_id": uuid(required=False, allow_null=True),
            "audience": serializers.ChoiceField(choices=["workspace", "public"]),
            "cause": text(),
            "geography": text(),
            "expires_at": serializers.DateTimeField(required=False, allow_null=True),
            "attribution": text(required=False),
            "external_processing": serializers.BooleanField(required=False),
        },
        v.AnalysesView: {
            "title": text(required=False),
            "observation_ids": serializers.ListField(child=uuid()),
            "cause": text(required=False),
            "geography": text(required=False),
        },
        v.SubmitView: {"revision": number(), "reviewer_id": number()},
        v.ReviewDetailView: {
            "revision": number(),
            "decision": serializers.ChoiceField(
                choices=["approved", "rejected", "changes_requested", "withdrawn"]
            ),
            "reason": text(),
        },
        v.ImportsView: {
            "file": serializers.FileField(),
            "mapping": serializers.JSONField(required=False),
        },
        v.RequestsView: {
            "kind": serializers.ChoiceField(
                choices=["sponsored_onboarding", "introduction", "identity_claim"]
            ),
            "note": text(),
            "target_id": uuid(required=False),
        },
        v.MetricsView: {
            "metric": text(),
            "value": serializers.DecimalField(max_digits=20, decimal_places=4),
            "denominator": serializers.DecimalField(
                max_digits=20, decimal_places=4, required=False, allow_null=True
            ),
            "period_start": serializers.DateField(),
            "period_end": serializers.DateField(),
            "collection_method": text(),
        },
    }
    session = inline_serializer(
        name="SessionData",
        fields={
            "user": inline_serializer(
                name="CurrentUser", fields={"id": number(), "username": text()}, allow_null=True
            ),
            "workspaces": serializers.ListField(
                child=inline_serializer(
                    name="SessionWorkspace",
                    fields={
                        "id": uuid(),
                        "name": text(),
                        "kind": text(),
                        "role": text(),
                        "organization_id": uuid(allow_null=True),
                    },
                )
            ),
            "csrfToken": text(),
            "demo_mode": serializers.BooleanField(),
        },
    )
    organization_detail = inline_serializer(
        name="OrganizationDetail",
        fields={
            "organization": s.OrganizationSerializer(),
            "filings": s.FilingSerializer(many=True),
            "financial_signals": serializers.DictField(),
            "programs": s.ProgramSerializer(many=True),
            "cards": s.CardSerializer(many=True),
        },
    )
    patches = {
        v.PortfolioDetailView: {
            "revision": number(),
            "allocations": serializers.ListField(
                child=inline_serializer(
                    name="AllocationEdit",
                    fields={"organization_id": uuid(), "amount_cents": number(min_value=0)},
                )
            ),
        },
        v.ProgramDetailView: {
            "revision": number(),
            "name": text(required=False),
            "cause": text(required=False),
            "intervention": text(required=False),
            "population": text(required=False),
            "geography": text(required=False),
            "context": serializers.DictField(required=False),
        },
        v.CardDetailView: {
            "revision": number(),
            **{
                field: text(required=False)
                for field in [
                    "title",
                    "implementation_steps",
                    "barriers",
                    "failures",
                    "caveats",
                    "attribution",
                ]
            },
        },
        v.ImportDetailView: {"mapping": serializers.DictField(child=text())},
        v.AlertDetailView: {
            "state": text(required=False),
            "feedback": text(required=False),
            "adoption_note": text(required=False),
        },
        v.SubscriptionsView: {
            field: serializers.BooleanField(required=False)
            for field in ["evidence", "financial", "stale"]
        },
        v.MetricsView: {"opted_in": serializers.BooleanField()},
        accounts.MembersView: {"id": uuid(), "role": text()},
    }
    classes = (
        set(lists)
        | set(details)
        | set(requests)
        | {getattr(v, name) for name in dir(v) if name.endswith("View") and name != "APIView"}
        | {accounts.SessionView, accounts.LogoutView, accounts.MembersView}
    )
    for cls in classes:
        annotations = {}
        for method in ["get", "post", "patch", "delete"]:
            if not hasattr(cls, method):
                continue
            if cls in {accounts.SessionView, accounts.LoginView, accounts.RedeemView}:
                response = session
            elif cls == v.OrganizationDetailView:
                response = organization_detail
            elif cls in lists:
                response = lists[cls](many=method == "get")
            elif cls in details:
                response = details[cls]()
            else:
                response = serializers.JSONField()
            kwargs = {
                "operation_id": cls.__name__.removesuffix("View") + "_" + method,
                "responses": envelope(cls.__name__ + method.title() + "Response", response),
                "tags": [
                    "session" if cls.__module__.startswith("philanthra.accounts") else "pilot"
                ],
                "description": (
                    cls.__doc__
                    or "Workspace-scoped operation. Unsafe requests require X-CSRFToken. Reauthorize sources and revisions on every use."
                ),
            }
            if method == "post":
                kwargs["request"] = object_request(cls.__name__ + "Request", requests.get(cls, {}))
            elif method == "patch":
                kwargs["request"] = object_request(
                    cls.__name__ + "PatchRequest", patches.get(cls, {})
                )
            if cls not in {accounts.SessionView, accounts.LoginView, accounts.RedeemView}:
                kwargs["parameters"] = [
                    OpenApiParameter("X-Workspace-ID", str, OpenApiParameter.HEADER, required=False)
                ]
            annotations[method] = extend_schema(**kwargs)
        extend_schema_view(**annotations)(cls)
