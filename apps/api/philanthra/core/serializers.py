from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from . import models as m


class SourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = m.Source
        fields = [
            "id",
            "owner_id",
            "title",
            "kind",
            "source_url",
            "upload_identifier",
            "retrieved_at",
            "published_at",
            "period_start",
            "period_end",
            "parser_version",
            "checksum",
            "locator",
            "transformations",
            "revision",
            "state",
            "cause",
            "geography",
        ]


class FilingSerializer(serializers.ModelSerializer):
    source = SourceSerializer(read_only=True)

    class Meta:
        model = m.Filing
        fields = [
            "id",
            "source",
            "form",
            "tax_year",
            "period_start",
            "period_end",
            "revision",
            "amended",
            "active",
            "currency",
            "revenue",
            "expenses",
            "program_expenses",
            "assets",
            "liabilities",
            "cash",
            "caveats",
        ]


class ProgramSerializer(serializers.ModelSerializer):
    class Meta:
        model = m.Program
        fields = [
            "id",
            "owner_id",
            "organization_id",
            "source_id",
            "name",
            "cause",
            "intervention",
            "population",
            "geography",
            "context",
            "revision",
        ]


class OrganizationSerializer(serializers.ModelSerializer):
    service_areas = serializers.SerializerMethodField()
    latest_filing = serializers.SerializerMethodField()
    discovery_summary = serializers.SerializerMethodField()

    class Meta:
        model = m.Organization
        fields = [
            "id",
            "name",
            "mission",
            "source_kind",
            "country",
            "headquarters_zip",
            "cause",
            "population",
            "status",
            "capacity_cents",
            "capacity_note",
            "service_areas",
            "latest_filing",
            "discovery_summary",
        ]

    def get_service_areas(self, obj) -> list[dict]:
        return [
            {
                "code": a.geography.code,
                "name": a.geography.name,
                "kind": a.geography.kind,
                "basis": a.basis,
                "latitude": str(a.geography.latitude) if a.geography.latitude is not None else None,
                "longitude": str(a.geography.longitude)
                if a.geography.longitude is not None
                else None,
                "context": a.geography.context,
                "source_id": str(a.source_id),
            }
            for a in obj.service_areas.select_related("geography", "source").filter(
                source__owner__isnull=True,
                source__state="active",
                geography__source__owner__isnull=True,
                geography__source__state="active",
            )
        ]

    def get_discovery_summary(self, obj) -> dict:
        from django.conf import settings
        from django.utils import timezone

        from philanthra.analytics.finance import financial_signals

        from .policy import visible_artifacts
        from .services import filing_input

        filings = list(
            obj.filings.filter(
                active=True, source__owner__isnull=True, source__state="active"
            ).select_related("source")
        )
        signals = financial_signals(
            [filing_input(f) for f in filings],
            as_of="2026-09-01" if settings.DEMO_MODE else timezone.now().date().isoformat(),
        )
        last = signals["periods"][-1] if signals["periods"] else None
        workspace = self.context.get("workspace")
        if "approved_cards" not in self.context:
            self.context["approved_cards"] = (
                [a for a in visible_artifacts(workspace, kind="card") if a.status == "approved"]
                if workspace
                else []
            )
        cards = [
            a for a in self.context["approved_cards"] if a.card.program.organization_id == obj.id
        ]
        return {
            "program_spending_share": last["metrics"]["program_spending_share"]
            if last
            else {"value": None, "reason": "No comparable financial filing available"},
            "approved_evidence_cards": len(cards),
            "evidence_caveat": "Editorial review is not validation of effectiveness; unknown or unshared evidence is absent from this count.",
            "financial_flags": [s for s in signals["signals"] if s["state"] == "flag"],
            "missing_fields": last["missing_fields"] if last else ["financial_history"],
            "method_version": signals["method_version"],
            "source_ids": signals["source_ids"],
        }

    @extend_schema_field(FilingSerializer(allow_null=True))
    def get_latest_filing(self, obj):
        row = (
            obj.filings.filter(active=True, source__owner__isnull=True, source__state="active")
            .order_by("-tax_year")
            .first()
        )
        return FilingSerializer(row).data if row else None


class ArtifactSerializer(serializers.ModelSerializer):
    sources = serializers.SerializerMethodField()
    review = serializers.SerializerMethodField()
    attributions = serializers.SerializerMethodField()

    class Meta:
        model = m.Artifact
        fields = [
            "id",
            "owner_id",
            "kind",
            "title",
            "revision",
            "status",
            "purpose",
            "cause",
            "geography",
            "payload",
            "method_version",
            "policy_version",
            "source_kind",
            "created_at",
            "sources",
            "review",
            "attributions",
        ]

    @extend_schema_field(SourceSerializer(many=True))
    def get_sources(self, obj):
        # Shared analysis releases disclose citations only after complete authorization;
        # suppressed payloads never attach sensitive cohort diagnostics.
        if obj.kind == "analysis" and obj.payload.get("status") != "draft":
            return []
        return SourceSerializer(obj.sources.all(), many=True).data

    def get_review(self, obj) -> dict | None:
        review = obj.decisions.filter(revision=obj.revision).order_by("-created_at").first()
        return (
            {
                "reviewer_id": review.reviewer_id,
                "decision": review.decision,
                "reason": review.reason,
                "created_at": review.created_at,
                "revision": review.revision,
            }
            if review
            else None
        )

    def get_attributions(self, obj) -> list[dict]:
        from .policy import artifact_attributions

        return artifact_attributions(obj, self.context.get("workspace", obj.owner))


class CardSerializer(ArtifactSerializer):
    card = serializers.SerializerMethodField()

    class Meta(ArtifactSerializer.Meta):
        fields = ArtifactSerializer.Meta.fields + ["card"]

    def get_card(self, obj) -> dict:
        card = obj.card
        return {
            "id": str(card.id),
            "program": ProgramSerializer(card.program).data,
            "evidence_label": card.evidence_label,
            "study_design": card.study_design,
            "implementation_steps": card.implementation_steps,
            "barriers": card.barriers,
            "failures": card.failures,
            "caveats": card.caveats,
            "attribution": card.attribution,
        }


class PortfolioSerializer(ArtifactSerializer):
    portfolio = serializers.SerializerMethodField()

    class Meta(ArtifactSerializer.Meta):
        fields = ArtifactSerializer.Meta.fields + ["portfolio"]

    def get_portfolio(self, obj) -> dict:
        from .coverage import geographic_coverage

        p = obj.portfolio
        return {
            "id": str(p.id),
            "budget_cents": p.budget_cents,
            "currency": p.currency,
            "constraints": p.constraints,
            "unallocated_cents": p.unallocated_cents,
            "geographic_coverage": geographic_coverage(p),
            "allocations": [
                {
                    "id": str(a.id),
                    "organization_id": str(a.organization_id),
                    "organization_name": a.organization.name,
                    "amount_cents": a.amount_cents,
                    "cap_cents": a.cap_cents,
                    "weight": str(a.weight),
                    "explanation": a.explanation,
                }
                for a in p.allocations.select_related("organization").all()
            ],
        }


class ObservationSerializer(serializers.ModelSerializer):
    outcome_definition = serializers.CharField(source="outcome.definition", read_only=True)
    organization_id = serializers.UUIDField(source="program.organization_id", read_only=True)

    class Meta:
        model = m.Observation
        exclude = []


class GrantSerializer(serializers.ModelSerializer):
    class Meta:
        model = m.DataGrant
        fields = "__all__"


class ImportSerializer(serializers.ModelSerializer):
    source_id = serializers.UUIDField(read_only=True)

    class Meta:
        model = m.ImportBatch
        fields = [
            "id",
            "source_id",
            "program_id",
            "filename",
            "checksum",
            "format",
            "status",
            "mapping",
            "columns",
            "preview",
            "diagnostics",
            "created_at",
            "updated_at",
        ]


class JobSerializer(serializers.ModelSerializer):
    class Meta:
        model = m.Job
        fields = [
            "id",
            "kind",
            "state",
            "attempts",
            "max_attempts",
            "available_at",
            "error_code",
            "created_at",
            "updated_at",
        ]


class AlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = m.Alert
        fields = [
            "id",
            "artifact_id",
            "title",
            "explanation",
            "state",
            "feedback",
            "adoption_note",
            "created_at",
        ]
