from drf_spectacular.utils import (
    OpenApiParameter,
    extend_schema,
    extend_schema_view,
    inline_serializer,
)
from rest_framework import serializers as s

from philanthra.core.serializers import CardSerializer, SourceSerializer


def obj(name, fields, many=False):
    return inline_serializer(name=name, fields=fields, many=many)


def apply_schema():
    from . import views as v

    def text(**kwargs):
        return s.CharField(**kwargs)

    def uid(**kwargs):
        return s.UUIDField(**kwargs)

    def num(**kwargs):
        return s.IntegerField(**kwargs)

    def boolean(**kwargs):
        return s.BooleanField(**kwargs)

    request = {
        v.WorkspacesView: {"name": text(), "kind": s.ChoiceField(choices=["ngo", "foundation"])},
        v.IdentityClaimsView: {
            "organization_id": uid(),
            "proof_source_id": uid(),
            "statement": text(min_length=20, max_length=4000),
        },
        v.PasswordResetRequestView: {"email": s.EmailField()},
        v.PasswordResetConfirmView: {
            "uid": text(),
            "token": text(),
            "password": text(write_only=True),
        },
        v.BookmarksView: {"artifact_id": uid()},
        v.WatchlistView: {"organization_id": uid()},
        v.MonitorView: {},
        v.ProfileView: {
            "revision": num(),
            "mission": text(required=False),
            "cause": text(required=False),
            "population": text(required=False),
            "service_area_codes": s.ListField(child=text(), required=False),
            "context": s.DictField(required=False),
        },
        v.ContactView: {
            "revision": num(),
            "name": text(),
            "email": s.EmailField(),
            "enabled": boolean(),
        },
        v.IntroductionDecisionView: {"state": s.ChoiceField(choices=["accepted", "declined"])},
    }
    response = {
        v.IdentityProofView: obj(
            "PilotIdentityProof",
            {
                "source": SourceSerializer(),
                "statement": text(),
                "document_preview": s.ListField(child=s.DictField()),
                "validation_status": text(),
                "limitation": text(),
            },
        ),
        v.WorkspacesView: obj(
            "PilotWorkspace",
            {
                "id": uid(),
                "name": text(),
                "kind": text(),
                "role": text(),
                "organization_id": uid(allow_null=True),
            },
        ),
        v.IdentityClaimsView: obj(
            "PilotIdentityClaim",
            {
                "id": uid(),
                "artifact_id": uid(),
                "organization": obj("ClaimOrganization", {"id": uid(), "name": text()}),
                "status": text(),
                "revision": num(),
                "statement": text(),
                "proof_source_id": uid(),
                "linked_revision": num(allow_null=True),
            },
        ),
        v.PasswordResetRequestView: obj(
            "ResetAccepted", {"accepted": boolean(), "message": text()}
        ),
        v.PasswordResetConfirmView: obj("ResetComplete", {"reset": boolean(), "message": text()}),
        v.BookmarksView: obj("PilotBookmark", {"id": uid(), "artifact": CardSerializer()}),
        v.WatchlistView: obj(
            "PilotWatchItem",
            {
                "id": uid(),
                "organization_id": uid(),
                "organization_name": text(),
                "last_checked_at": s.DateTimeField(required=False),
                "monitor_status": text(),
            },
        ),
        v.MonitorView: obj("PilotMonitorJob", {"job_id": uid(), "state": text()}),
        v.ImpactReportView: obj(
            "PilotImpactReport",
            {
                "workspace": obj("ReportWorkspace", {"id": uid(), "name": text()}),
                "status": text(),
                "generated_at": s.DateTimeField(),
                "programs": s.ListField(child=s.DictField()),
                "observations": s.ListField(child=s.DictField()),
                "costs": s.ListField(child=s.DictField()),
                "cards": s.ListField(child=s.DictField()),
                "sources": SourceSerializer(many=True),
                "data_quality": s.ListField(child=s.DictField()),
                "source_kind": text(),
                "limitations": s.ListField(child=text()),
            },
        ),
        v.BenchmarkView: obj(
            "PilotBenchmark",
            {
                "status": text(),
                "reason": text(required=False),
                "method_version": text(required=False),
                "source_ids": s.ListField(child=uid(), required=False),
                "peer_organization_count": num(required=False),
                "median": text(required=False),
                "minimum": text(required=False),
                "maximum": text(required=False),
                "target_value": text(required=False),
                "difference_from_median": text(required=False),
                "limitations": s.ListField(child=text(), required=False),
            },
        ),
        v.ProfileView: obj(
            "PilotProfile",
            {
                "revision": num(),
                "mission": text(),
                "cause": text(),
                "population": text(),
                "service_area_codes": s.ListField(child=text()),
                "context": s.DictField(),
                "visibility": text(),
            },
        ),
        v.ContactView: obj(
            "PilotContactConsent",
            {"name": text(), "email": text(), "enabled": boolean(), "revision": num()},
        ),
        v.IntroductionInboxView: obj(
            "PilotIntroduction",
            {"id": uid(), "from_workspace": text(), "note": text(), "state": text()},
        ),
        v.IntroductionDecisionView: obj(
            "PilotIntroductionDecision", {"id": uid(), "state": text(), "delivery": text()}
        ),
        v.IntroductionContactView: obj(
            "PilotIntroductionContact",
            {
                "name": text(),
                "email": s.EmailField(),
                "consent_revision": num(),
                "delivery": text(),
            },
        ),
    }
    list_classes = {v.IdentityClaimsView, v.BookmarksView, v.WatchlistView, v.IntroductionInboxView}
    for cls in set(response) | {v.BookmarkDetailView, v.WatchDetailView}:
        methods = {}
        for method in ["get", "post", "patch", "put", "delete"]:
            if not hasattr(cls, method):
                continue
            data = response.get(cls, obj(cls.__name__ + "Deleted", {"deleted": boolean()}))
            if cls == v.BookmarksView and method == "post":
                data = obj("PilotBookmarkCreated", {"id": uid(), "artifact_id": uid()})
            if cls in list_classes and method == "get":
                data = s.ListField(child=data)
            options = {
                "operation_id": "pilot_" + cls.__name__.removesuffix("View") + "_" + method,
                "responses": obj(
                    cls.__name__ + method.title() + "Envelope",
                    {"data": data, "meta": s.DictField()},
                ),
                "tags": ["pilot"],
            }
            if method in {"post", "patch", "put"}:
                options["request"] = obj(
                    cls.__name__ + method.title() + "Request", request.get(cls, {})
                )
            if cls not in {
                v.PasswordResetRequestView,
                v.PasswordResetConfirmView,
                v.WorkspacesView,
            }:
                options["parameters"] = [
                    OpenApiParameter("X-Workspace-ID", str, OpenApiParameter.HEADER, required=False)
                ]
            methods[method] = extend_schema(**options)
        extend_schema_view(**methods)(cls)
