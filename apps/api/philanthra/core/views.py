import hashlib
import json

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.postgres.search import SearchQuery, SearchVector
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from . import models as m
from . import serializers as s
from .policy import (
    artifact_or_404,
    can_artifact,
    can_source,
    source_or_404,
    validate_grant,
    visible_artifacts,
    workspace_for,
)
from .services import (
    Conflict,
    audit,
    create_artifact,
    create_portfolio,
    decide_review,
    enqueue,
    filing_input,
    observation_input,
    submit_review,
    withdraw,
)


def ok(data, status=200, **meta):
    return Response({"data": data, "meta": meta}, status=status)


def integer(value, field, minimum=0, maximum=10**15):
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise ValidationError({field: f"An integer between {minimum} and {maximum} is required."})
    return value


def listing(request, rows, serializer=None):
    try:
        page = max(1, int(request.query_params.get("page", 1)))
        size = min(100, max(1, int(request.query_params.get("page_size", 100))))
    except ValueError as exc:
        raise ValidationError({"page": "Invalid pagination."}) from exc
    total = len(rows)
    selected = rows[(page - 1) * size : page * size]
    return ok(
        serializer(selected, many=True, context={"workspace": workspace_for(request)}).data
        if serializer
        else selected,
        total=total,
        page=page,
        page_size=size,
    )


class OrganizationsView(APIView):
    def get(self, request):
        ws = workspace_for(request)
        query = m.Organization.objects.all().order_by("name")
        for parameter, field in [
            ("cause", "cause"),
            ("country", "country"),
            ("population", "population__icontains"),
        ]:
            if request.query_params.get(parameter):
                query = query.filter(**{field: request.query_params[parameter]})
        if request.query_params.get("q"):
            query = query.annotate(search=SearchVector("name", "mission", config="english")).filter(
                search=SearchQuery(
                    request.query_params["q"], search_type="websearch", config="english"
                )
            )
        location = request.query_params.get("location") or request.query_params.get("zip")
        if location:
            query = query.filter(
                service_areas__geography__code=location,
                service_areas__source__owner__isnull=True,
                service_areas__source__state="active",
            ).distinct()
        rows = list(query)
        size = request.query_params.get("size")
        if size in {"small", "medium", "large"}:
            bounds = {
                "small": (0, 500000),
                "medium": (500000, 2000000),
                "large": (2000000, 10**20),
            }[size]
            rows = [
                o
                for o in rows
                if (
                    f := o.filings.filter(
                        active=True, source__owner__isnull=True, source__state="active"
                    )
                    .order_by("-tax_year")
                    .first()
                )
                and f.revenue is not None
                and bounds[0] <= f.revenue < bounds[1]
            ]
        budget = request.query_params.get("budget_cents")
        if budget:
            try:
                if int(budget) <= 0:
                    rows = []
            except ValueError as exc:
                raise ValidationError({"budget_cents": "Use integer minor units."}) from exc
        risk = request.query_params.get("risk", "all")
        if risk not in {"all", "avoid_repeated_deficits", "capacity_building"}:
            raise ValidationError(
                {"risk": "Choose all, avoid_repeated_deficits or capacity_building."}
            )
        if risk != "all":
            from django.conf import settings

            from philanthra.analytics.finance import financial_signals

            selected = []
            for org in rows:
                filings = list(
                    org.filings.filter(
                        active=True, source__owner__isnull=True, source__state="active"
                    ).select_related("source")
                )
                result = financial_signals(
                    [filing_input(f) for f in filings],
                    as_of="2026-09-01" if settings.DEMO_MODE else timezone.now().date().isoformat(),
                )
                repeated = any(
                    signal["code"] == "repeated_deficits" and signal["state"] == "flag"
                    for signal in result["signals"]
                )
                if (risk == "capacity_building" and repeated) or (
                    risk == "avoid_repeated_deficits" and not repeated
                ):
                    selected.append(org)
            rows = selected
        outcome = request.query_params.get("outcome_definition")
        horizon = request.query_params.get("horizon_days")
        if horizon:
            try:
                horizon = int(horizon)
                if not 1 <= horizon <= 3650:
                    raise ValueError()
            except ValueError as exc:
                raise ValidationError(
                    {"horizon_days": "Use a supported 1–3650 day horizon."}
                ) from exc
        if outcome or horizon:
            eligible = set()
            for observation in m.Observation.objects.select_related("source", "outcome", "program"):
                if not can_source(
                    observation.source,
                    ws,
                    "donor_access",
                    observation.program.cause,
                    observation.program.geography,
                ):
                    continue
                if outcome and observation.outcome.code != outcome:
                    continue
                if horizon and observation.followup_months * 30 > horizon:
                    continue
                eligible.add(observation.program.organization_id)
            for artifact in visible_artifacts(ws, kind="card"):
                if artifact.status != "approved":
                    continue
                if outcome and artifact.payload.get("outcome_definition") != outcome:
                    continue
                followup = artifact.payload.get("followup_days")
                if horizon and (not isinstance(followup, int) or followup > horizon):
                    continue
                eligible.add(artifact.card.program.organization_id)
            rows = [org for org in rows if org.id in eligible]
        response = listing(request, rows, s.OrganizationSerializer)
        response.data["meta"]["filter_caveats"] = [
            "Missing financial history is unknown, not evidence of financial resilience.",
            "Outcome and horizon filters require permissioned observed outcomes; absent reporting is not ineffectiveness.",
        ]
        return response


class OrganizationDetailView(APIView):
    def get(self, request, pk):
        ws = workspace_for(request)
        org = get_object_or_404(m.Organization, pk=pk)
        filings = list(
            org.filings.filter(source__owner__isnull=True, source__state="active")
            .select_related("source")
            .order_by("tax_year", "revision")
        )
        from django.conf import settings

        from philanthra.analytics.finance import financial_signals

        signals = financial_signals(
            [filing_input(f) for f in filings],
            as_of="2026-09-01"
            if getattr(settings, "DEMO_MODE", False)
            else timezone.now().date().isoformat(),
        )
        programs = [
            p
            for p in org.programs.select_related("source")
            if can_source(p.source, ws, "donor_access", p.cause, p.geography)
        ]
        cards = [
            a
            for a in visible_artifacts(ws, kind="card", user=request.user)
            if a.card.program.organization_id == org.id
        ]
        return ok(
            {
                "organization": s.OrganizationSerializer(org, context={"workspace": ws}).data,
                "filings": s.FilingSerializer(filings, many=True).data,
                "financial_signals": signals,
                "programs": s.ProgramSerializer(programs, many=True).data,
                "cards": s.CardSerializer(cards, many=True, context={"workspace": ws}).data,
            }
        )


class CompareView(APIView):
    def get(self, request):
        workspace_for(request)
        ids = request.query_params.get("ids", "").split(",")
        if not 2 <= len(set(ids)) <= 4:
            raise ValidationError({"ids": "Compare two to four distinct organizations."})
        orgs = list(m.Organization.objects.filter(id__in=ids))
        if len(orgs) != len(set(ids)):
            raise NotFound()
        return ok(
            {
                "organizations": s.OrganizationSerializer(
                    orgs, many=True, context={"workspace": workspace_for(request)}
                ).data,
                "caveats": [
                    "Compare matching fiscal periods and currencies; program spending is not impact.",
                    "Missing values remain unknown.",
                ],
            }
        )


class GeographyView(APIView):
    def get(self, request):
        workspace_for(request)
        return ok(
            [
                {
                    "id": str(g.id),
                    "code": g.code,
                    "name": g.name,
                    "kind": g.kind,
                    "latitude": str(g.latitude) if g.latitude is not None else None,
                    "longitude": str(g.longitude) if g.longitude is not None else None,
                    "context": g.context,
                    "source_id": str(g.source_id),
                }
                for g in m.Geography.objects.filter(
                    source__owner__isnull=True, source__state="active"
                )
            ]
        )


class PortfoliosView(APIView):
    def get(self, request):
        ws = workspace_for(request)
        rows = [a for a in visible_artifacts(ws, kind="portfolio") if a.owner_id == ws.id]
        return listing(request, rows, s.PortfolioSerializer)

    def post(self, request):
        ws = workspace_for(request, write=True)
        if ws.kind != "foundation":
            raise PermissionDenied("Foundation workspace required.")
        integer(request.data.get("budget_cents"), "budget_cents")
        if request.data.get("currency", "USD") != "USD":
            raise ValidationError({"currency": "The pilot allocator supports USD only."})
        return ok(s.PortfolioSerializer(create_portfolio(ws, request.user, request.data)).data, 201)


class PortfolioDetailView(APIView):
    def get(self, request, pk):
        ws = workspace_for(request)
        artifact = artifact_or_404(pk, ws, kind="portfolio")
        if artifact.owner_id != ws.id:
            raise NotFound()
        return ok(s.PortfolioSerializer(artifact, context={"workspace": ws}).data)

    @transaction.atomic
    def patch(self, request, pk):
        ws = workspace_for(request, write=True)
        artifact = artifact_or_404(pk, ws, kind="portfolio")
        if artifact.owner_id != ws.id:
            raise NotFound()
        list(
            m.Source.objects.select_for_update()
            .filter(dependency__artifact=artifact)
            .order_by("id")
        )
        artifact = m.Artifact.objects.select_for_update().get(pk=pk)
        if not can_artifact(artifact, ws):
            raise NotFound()
        if request.data.get("revision") != artifact.revision:
            raise Conflict()
        portfolio = artifact.portfolio
        edits = request.data.get("allocations", [])
        existing = {str(a.organization_id): a for a in portfolio.allocations.all()}
        if {str(row.get("organization_id")) for row in edits} != set(existing) or len(edits) != len(
            existing
        ):
            raise ValidationError({"allocations": "Supply each existing candidate exactly once."})
        total = 0
        constraints = {c["id"]: c for c in portfolio.constraints.get("candidates", [])}
        for row in edits:
            allocation = existing[str(row["organization_id"])]
            amount = integer(row.get("amount_cents"), "amount_cents", maximum=allocation.cap_cents)
            constraint = constraints.get(str(row["organization_id"]))
            if constraint is None or (constraint.get("excluded") and amount != 0):
                raise ValidationError(
                    {"allocations": "Excluded or unrecognized candidates cannot receive funds."}
                )
            if amount < constraint.get("minimum_cents", 0):
                raise ValidationError(
                    {
                        "allocations": "Amount is below the frozen minimum. Revise the plan constraints explicitly."
                    }
                )
            allocation.amount_cents = amount
            total += amount
        if total > portfolio.budget_cents:
            raise ValidationError({"allocations": "Allocation exceeds budget."})
        for allocation in existing.values():
            allocation.save()
        portfolio.unallocated_cents = portfolio.budget_cents - total
        portfolio.save()
        artifact.revision += 1
        artifact.status = "draft"
        artifact.payload = {
            "manual_edit": True,
            "unallocated_cents": portfolio.unallocated_cents,
            "method_version": "manual-constrained-v1",
        }
        artifact.save()
        audit(ws, request.user, "portfolio.edited", artifact.id, revision=artifact.revision)
        return ok(s.PortfolioSerializer(artifact, context={"workspace": ws}).data)


class ProgramsView(APIView):
    def get(self, request):
        ws = workspace_for(request)
        return listing(
            request,
            list(m.Program.objects.filter(owner=ws, source__state="active")),
            s.ProgramSerializer,
        )

    @transaction.atomic
    def post(self, request):
        ws = workspace_for(request, write=True)
        if not ws.organization_id:
            raise ValidationError({"organization": "Verified workspace organization required."})
        source = get_object_or_404(
            m.Source.objects.select_for_update(),
            id=request.data.get("source_id"),
            owner=ws,
            state="active",
        )
        fields = {
            k: request.data[k]
            for k in ["name", "cause", "intervention", "population", "geography", "context"]
            if k in request.data
        }
        for key in ["name", "cause", "intervention", "population", "geography"]:
            if not isinstance(fields.get(key), str) or not fields[key].strip():
                raise ValidationError({key: "Required."})
        if not isinstance(fields.get("context", {}), dict):
            raise ValidationError({"context": "A context object is required."})
        if fields["cause"] != source.cause or fields["geography"] != source.geography:
            raise ValidationError(
                {"source_id": "Program cause and geography must match its source consent scope."}
            )
        program = m.Program.objects.create(
            owner=ws, organization=ws.organization, source=source, **fields
        )
        enqueue(
            ws,
            "recommendations",
            f"profile:{program.id}:1",
            {"program_id": str(program.id)},
            source,
        )
        return ok(s.ProgramSerializer(program).data, 201)


class ProgramDetailView(APIView):
    @transaction.atomic
    def patch(self, request, pk):
        ws = workspace_for(request, write=True)
        program = get_object_or_404(m.Program, pk=pk, owner=ws, source__state="active")
        source = m.Source.objects.select_for_update().get(pk=program.source_id)
        if source.state != "active":
            raise NotFound()
        program = m.Program.objects.select_for_update().get(pk=program.pk)
        if request.data.get("revision") != program.revision:
            raise Conflict()
        for field in ["name", "cause", "intervention", "population", "geography", "context"]:
            if field in request.data:
                setattr(program, field, request.data[field])
        if program.cause != program.source.cause or program.geography != program.source.geography:
            raise ValidationError(
                {
                    "source_id": "Use a new scoped source to change cause or geography; grants cannot be broadened."
                }
            )
        if not isinstance(program.context, dict):
            raise ValidationError({"context": "A context object is required; empty means unknown."})
        program.revision += 1
        program.full_clean(exclude=["context"])
        program.save()
        # A profile update changes the source snapshot, invalidating previous claims.
        source = m.Source.objects.select_for_update().get(pk=program.source_id)
        source.revision += 1
        source.save()
        from .services import source_revision_changed

        source_revision_changed(source)
        m.Artifact.objects.filter(dependencies__source=source).update(status="invalidated")
        enqueue(
            ws,
            "recommendations",
            f"profile:{program.id}:{program.revision}",
            {"program_id": str(program.id)},
            source,
        )
        return ok(s.ProgramSerializer(program).data)


EVIDENCE_LABELS = {
    "descriptive observation",
    "correlation",
    "quasi-experimental finding",
    "randomized evaluation",
    "repeated cross-organization pattern",
    "expert-reviewed operational lesson",
    "early hypothesis",
}


class CardsView(APIView):
    def get(self, request):
        ws = workspace_for(request)
        rows = visible_artifacts(ws, kind="card", user=request.user)
        q = request.query_params.get("q", "").lower()
        if q:
            permitted = {a.id for a in rows}
            matches = set(
                m.Artifact.objects.filter(id__in=permitted)
                .annotate(
                    search=SearchVector(
                        "title",
                        "card__program__intervention",
                        "card__implementation_steps",
                        config="english",
                    )
                )
                .filter(search=SearchQuery(q, search_type="websearch", config="english"))
                .values_list("id", flat=True)
            )
            rows = [a for a in rows if a.id in matches]
        return listing(request, rows, s.CardSerializer)

    @transaction.atomic
    def post(self, request):
        ws = workspace_for(request, write=True)
        program = get_object_or_404(
            m.Program, pk=request.data.get("program_id"), owner=ws, source__state="active"
        )
        label = request.data.get("evidence_label", "descriptive observation")
        if label not in EVIDENCE_LABELS:
            raise ValidationError({"evidence_label": "Unsupported evidence label."})
        design = request.data.get("study_design", "observational")
        if label == "randomized evaluation" and design != "randomized":
            raise ValidationError(
                {"study_design": "Randomized evidence requires a reported randomized design."}
            )
        claims = request.data.get("claims", [])
        if not isinstance(claims, list) or len(claims) > 50:
            raise ValidationError({"claims": "At most 50 sourced claims."})
        sources = {program.source_id: program.source}
        for claim in claims:
            source = source_or_404(claim.get("source_id"), ws)
            sources[source.id] = source
            if not claim.get("locator") or not claim.get("text"):
                raise ValidationError({"claims": "Every claim needs text and a source locator."})
        artifact = create_artifact(
            ws,
            request.user,
            kind="card",
            title=request.data.get("title", program.name),
            sources=list(sources.values()),
            payload={"summary": str(request.data.get("summary", ""))},
            cause=program.cause,
            geography=program.geography,
        )
        m.Card.objects.create(
            artifact=artifact,
            program=program,
            evidence_label=label,
            study_design=design,
            **{
                k: str(request.data.get(k, ""))
                for k in ["implementation_steps", "barriers", "failures", "caveats", "attribution"]
            },
        )
        for claim in claims:
            m.Claim.objects.create(
                artifact=artifact,
                source_id=claim["source_id"],
                text=claim["text"],
                locator=claim["locator"],
                label=claim.get("label", label),
            )
        for target_type, target_id, relation in [
            ("program", str(program.id), "describes"),
            ("organization", str(program.organization_id), "implemented_by"),
            ("cause", program.cause, "addresses"),
            ("population", program.population, "serves"),
            ("geography", program.geography, "located_in"),
        ]:
            m.GraphEdge.objects.create(
                artifact=artifact,
                source_type="evidence",
                source_id=str(artifact.id),
                target_type=target_type,
                target_id=target_id,
                relation=relation,
                supporting_source=program.source,
            )
        return ok(s.CardSerializer(artifact, context={"workspace": ws}).data, 201)


class CardDetailView(APIView):
    def get(self, request, pk):
        ws = workspace_for(request)
        return ok(
            s.CardSerializer(
                artifact_or_404(pk, ws, user=request.user, kind="card"), context={"workspace": ws}
            ).data
        )

    @transaction.atomic
    def patch(self, request, pk):
        ws = workspace_for(request, write=True)
        artifact = artifact_or_404(pk, ws, kind="card")
        if artifact.owner_id != ws.id:
            raise NotFound()
        list(
            m.Source.objects.select_for_update()
            .filter(dependency__artifact=artifact)
            .order_by("id")
        )
        artifact = m.Artifact.objects.select_for_update().get(pk=pk)
        if not can_artifact(artifact, ws):
            raise NotFound()
        if request.data.get("revision") != artifact.revision:
            raise Conflict()
        if "title" in request.data:
            artifact.title = str(request.data["title"])
        card = artifact.card
        for field in ["implementation_steps", "barriers", "failures", "caveats", "attribution"]:
            if field in request.data:
                setattr(card, field, str(request.data[field]))
        card.save()
        artifact.revision += 1
        artifact.status = "draft"
        artifact.save()
        m.Alert.objects.filter(artifact=artifact).update(state="invalidated")
        return ok(s.CardSerializer(artifact, context={"workspace": ws}).data)


class SourceIssuesView(APIView):
    def get(self, request):
        ws = workspace_for(request)
        return listing(
            request,
            visible_artifacts(ws, kind="source_issue", user=request.user),
            s.ArtifactSerializer,
        )

    def post(self, request):
        ws = workspace_for(request, write=True)
        source = source_or_404(request.data.get("source_id"), ws)
        issue = str(request.data.get("issue", "")).strip()
        if not issue or len(issue) > 4000:
            raise ValidationError(
                {"issue": "A substantive issue of at most 4,000 characters is required."}
            )
        artifact = create_artifact(
            ws,
            request.user,
            kind="source_issue",
            title=str(request.data.get("title", "Source issue for review"))[:240],
            sources=[source],
            payload={
                "issue": issue,
                "scope": "Review of source quality; approval is not an automatic source correction.",
            },
            cause=source.cause,
            geography=source.geography,
        )
        return ok(s.ArtifactSerializer(artifact, context={"workspace": ws}).data, 201)


class SourcesView(APIView):
    def get(self, request):
        ws = workspace_for(request)
        rows = [
            source
            for source in m.Source.objects.filter(state="active").order_by("-retrieved_at")
            if can_source(source, ws)
        ]
        return listing(request, rows, s.SourceSerializer)

    def post(self, request):
        ws = workspace_for(request, write=True)
        title = str(request.data.get("title", "")).strip()
        if not title:
            raise ValidationError({"title": "Required."})
        source = m.Source.objects.create(
            owner=ws,
            title=title,
            kind="ngo_contributed",
            retrieved_at=timezone.now(),
            parser_version="manual-v1",
            checksum=hashlib.sha256(title.encode()).hexdigest(),
            upload_identifier="manual-draft",
            cause=request.data.get("cause", "food_security"),
            geography=request.data.get("geography", "US-MD-Baltimore"),
            locator=str(request.data.get("locator", "manual draft")),
        )
        return ok(s.SourceSerializer(source).data, 201)


class SourceDetailView(APIView):
    def get(self, request, pk):
        ws = workspace_for(request)
        return ok(s.SourceSerializer(source_or_404(pk, ws)).data)


class GrantsView(APIView):
    def get(self, request):
        ws = workspace_for(request)
        return listing(
            request, list(m.DataGrant.objects.filter(source__owner=ws)), s.GrantSerializer
        )

    @transaction.atomic
    def post(self, request):
        ws = workspace_for(request, admin=True)
        validate_grant(request.data)
        source = get_object_or_404(
            m.Source.objects.select_for_update(),
            pk=request.data.get("source_id"),
            owner=ws,
            state="active",
        )
        if request.data["cause"] != source.cause or request.data["geography"] != source.geography:
            raise ValidationError(
                {"scope": "The pilot only supports the source exact cause and geography scope."}
            )
        recipient = None
        if request.data.get("recipient_id"):
            recipient = get_object_or_404(m.Workspace, pk=request.data["recipient_id"])
        expires = request.data.get("expires_at")
        if expires:
            from django.utils.dateparse import parse_datetime

            expires = parse_datetime(expires)
            if not expires or timezone.is_naive(expires) or expires <= timezone.now():
                raise ValidationError({"expires_at": "Use a future timestamp with timezone."})
        grant = m.DataGrant.objects.create(
            source=source,
            recipient=recipient,
            purpose=request.data["purpose"],
            audience=request.data.get("audience", "workspace"),
            cause=request.data["cause"],
            geography=request.data["geography"],
            expires_at=expires,
            attribution=request.data.get("attribution", ""),
            external_processing=request.data.get("external_processing", False),
        )
        audit(ws, request.user, "grant.created", grant.id, purpose=grant.purpose)
        return ok(s.GrantSerializer(grant).data, 201)


class GrantDetailView(APIView):
    @transaction.atomic
    def delete(self, request, pk):
        ws = workspace_for(request, admin=True)
        grant = get_object_or_404(m.DataGrant, pk=pk, source__owner=ws)
        m.Source.objects.select_for_update().get(pk=grant.source_id)
        grant = m.DataGrant.objects.select_for_update().get(pk=pk)
        grant.active = False
        grant.revision += 1
        grant.save()
        from philanthra.pilot.services import after_source_withdrawal

        after_source_withdrawal(grant.source)
        ids = m.Dependency.objects.filter(source=grant.source).values_list("artifact_id", flat=True)
        m.Artifact.objects.filter(id__in=ids).update(status="invalidated")
        m.Alert.objects.filter(artifact_id__in=ids).update(state="invalidated")
        audit(ws, request.user, "grant.revoked", grant.id)
        return ok({"revoked": True})


class WithdrawView(APIView):
    def post(self, request, pk):
        ws = workspace_for(request, admin=True)
        source = get_object_or_404(m.Source, pk=pk, owner=ws)
        result = withdraw(source, request.user)
        return ok(
            {
                "id": str(result.id),
                "status": result.status,
                "source_id": str(source.id),
                "access": "denied immediately",
                "backup_limitation": "Previously downloaded exports cannot be recalled. Backups require documented operator expiry.",
            }
        )


class ObservationsView(APIView):
    def get(self, request):
        ws = workspace_for(request)
        # Source-level external cell disclosure must meet complementary thresholds.
        rows = [
            o
            for o in m.Observation.objects.select_related("source", "outcome", "program")
            if o.owner_id == ws.id and o.source.state == "active"
        ]
        return listing(request, rows, s.ObservationSerializer)


class AnalysesView(APIView):
    def get(self, request):
        return listing(
            request,
            visible_artifacts(workspace_for(request), kind="analysis", user=request.user),
            s.ArtifactSerializer,
        )

    @transaction.atomic
    def post(self, request):
        ws = workspace_for(request, write=True)
        ids = request.data.get("observation_ids", [])
        if not isinstance(ids, list) or not 1 <= len(ids) <= 100:
            raise ValidationError({"observation_ids": "Choose 1–100 observations."})
        source_ids = m.Observation.objects.filter(pk__in=ids).values_list("source_id", flat=True)
        list(m.Source.objects.select_for_update().filter(pk__in=source_ids).order_by("id"))
        rows = list(
            m.Observation.objects.filter(pk__in=ids).select_related("source", "outcome", "program")
        )
        if len(rows) != len(set(ids)):
            raise NotFound()
        cause = request.data.get("cause", "food_security")
        geography = request.data.get("geography", "US-MD-Baltimore")
        if not all(can_source(o.source, ws, "pooled_analysis", cause, geography) for o in rows):
            raise NotFound()
        # A release is a fixed complete cohort set, never an arbitrary private-data slice.
        first = rows[0]
        compatible = m.Observation.objects.filter(
            outcome=first.outcome,
            period_start=first.period_start,
            period_end=first.period_end,
            program__cause=cause,
            program__geography=geography,
        ).select_related("source", "outcome", "program")
        eligible = {
            o.id
            for o in compatible
            if can_source(o.source, ws, "pooled_analysis", cause, geography)
        }
        if {o.id for o in rows} != eligible:
            raise ValidationError(
                {
                    "observation_ids": "Choose the complete fixed outcome/period/cause/geography cohort set. Arbitrary slices are disabled."
                }
            )
        from philanthra.analytics.pooling import pool_observations

        result = pool_observations([observation_input(o) for o in rows])
        artifact = create_artifact(
            ws,
            request.user,
            kind="analysis",
            title=request.data.get("title", "Descriptive pooled analysis"),
            sources=list({o.source_id: o.source for o in rows}.values()),
            payload=result,
            purpose="pooled_analysis",
            cause=cause,
            geography=geography,
        )
        return ok(s.ArtifactSerializer(artifact, context={"workspace": ws}).data, 201)


class AnalysisCandidatesView(APIView):
    def get(self, request):
        ws = workspace_for(request)
        rows = []
        for o in m.Observation.objects.select_related("source", "outcome", "program"):
            if can_source(o.source, ws, "pooled_analysis", o.program.cause, o.program.geography):
                # Metadata only; no numerator/denominator/private count exposure.
                rows.append(
                    {
                        "id": str(o.id),
                        "program_name": o.program.name,
                        "organization_id": str(o.program.organization_id),
                        "outcome_definition": o.outcome.definition,
                        "period_start": o.period_start,
                        "period_end": o.period_end,
                        "source_kind": o.source.kind,
                    }
                )
        return listing(request, rows)


class SubmitView(APIView):
    def post(self, request, pk):
        ws = workspace_for(request, write=True)
        artifact = artifact_or_404(pk, ws)
        if artifact.owner_id != ws.id:
            raise NotFound()
        return ok(
            s.ArtifactSerializer(
                submit_review(
                    artifact,
                    request.user,
                    request.data.get("reviewer_id"),
                    request.data.get("revision"),
                )
            ).data
        )


class ReviewersView(APIView):
    def get(self, request):
        workspace_for(request)
        return ok(
            [
                {"id": u.id, "username": u.username}
                for u in get_user_model()
                .objects.filter(is_active=True, memberships__role="reviewer")
                .exclude(pk=request.user.pk)
                .distinct()
            ]
        )


class ReviewsView(APIView):
    def get(self, request):
        ws = workspace_for(request)
        rows = [
            a
            for a in m.Artifact.objects.filter(
                status="approved"
                if request.query_params.get("status") == "approved"
                else "pending_review",
                assignments__reviewer=request.user,
            ).distinct()
            if a.assignments.filter(reviewer=request.user, revision=a.revision).exists()
            and can_artifact(a, ws, user=request.user)
        ]
        return listing(request, rows, s.ArtifactSerializer)


class ReviewDetailView(APIView):
    def post(self, request, pk):
        ws = workspace_for(request)
        artifact = artifact_or_404(pk, ws, user=request.user)
        return ok(
            s.ArtifactSerializer(
                decide_review(
                    artifact,
                    request.user,
                    request.data.get("revision"),
                    request.data.get("decision", ""),
                    str(request.data.get("reason", "")),
                )
            ).data
        )


class GraphView(APIView):
    def get(self, request):
        from .graph import graph_rows

        ws = workspace_for(request)
        root = request.query_params.get("root")
        if root and len(root) > 160:
            raise ValidationError({"root": "A bounded entity identifier is required."})
        return ok(
            {
                "edges": graph_rows(ws, request.user, root),
                "limit": 100,
                "note": "One-hop, source-backed relationships; at most100 edges. Planning funder edges are proposals, not completed grants. No private totals or inferred effectiveness.",
            }
        )


class AlertsView(APIView):
    def get(self, request):
        from .policy import can_alert

        ws = workspace_for(request)
        rows = [
            a
            for a in m.Alert.objects.filter(owner=ws).select_related("artifact")
            if can_alert(a, ws)
        ]
        return listing(request, rows, s.AlertSerializer)


class AlertDetailView(APIView):
    def patch(self, request, pk):
        from .policy import can_alert

        ws = workspace_for(request, write=True)
        alert = get_object_or_404(m.Alert, pk=pk, owner=ws)
        if not can_alert(alert, ws):
            raise NotFound()
        if "state" in request.data:
            if request.data["state"] not in {"read", "dismissed", "saved", "adopted", "resolved"}:
                raise ValidationError({"state": "Unsupported state."})
            if (
                request.data["state"] == "adopted"
                and not str(request.data.get("adoption_note", "")).strip()
            ):
                raise ValidationError({"adoption_note": "Describe the actual pilot adoption."})
            alert.state = request.data["state"]
        if "feedback" in request.data:
            if request.data["feedback"] not in {"useful", "not_useful", "inaccurate", ""}:
                raise ValidationError({"feedback": "Unsupported feedback."})
            alert.feedback = request.data["feedback"]
        if "adoption_note" in request.data:
            alert.adoption_note = str(request.data["adoption_note"])
        alert.save()
        return ok(s.AlertSerializer(alert).data)


class SubscriptionsView(APIView):
    def get(self, request):
        workspace = workspace_for(request)
        if settings.DEMO_MODE and settings.DEMO_READ_ONLY:
            item = m.Subscription.objects.filter(owner=workspace).first() or m.Subscription(
                owner=workspace
            )
        else:
            item, _ = m.Subscription.objects.get_or_create(owner=workspace)
        return ok({k: getattr(item, k) for k in ["evidence", "financial", "stale"]})

    def patch(self, request):
        item, _ = m.Subscription.objects.get_or_create(owner=workspace_for(request, admin=True))
        for field in ["evidence", "financial", "stale"]:
            if field in request.data:
                if not isinstance(request.data[field], bool):
                    raise ValidationError({field: "Boolean required."})
                setattr(item, field, request.data[field])
        item.save()
        return ok({k: getattr(item, k) for k in ["evidence", "financial", "stale"]})


class AuditView(APIView):
    def get(self, request):
        ws = workspace_for(request, admin=True)
        return listing(
            request,
            [
                {
                    "id": str(e.id),
                    "action": e.action,
                    "object_id": e.object_id,
                    "created_at": e.created_at,
                    "metadata": e.metadata,
                }
                for e in m.AuditEvent.objects.filter(owner=ws).order_by("-created_at")[:1000]
            ],
        )


class JobsView(APIView):
    def get(self, request):
        return listing(
            request,
            list(m.Job.objects.filter(owner=workspace_for(request)).order_by("-created_at")),
            s.JobSerializer,
        )


class JobDetailView(APIView):
    def get(self, request, pk):
        return ok(
            s.JobSerializer(get_object_or_404(m.Job, pk=pk, owner=workspace_for(request))).data
        )


class ImportsView(APIView):
    def get(self, request):
        return listing(
            request,
            list(
                m.ImportBatch.objects.filter(owner=workspace_for(request), source__state="active")
            ),
            s.ImportSerializer,
        )

    @transaction.atomic
    def post(self, request):
        ws = workspace_for(request, write=True)
        upload = request.FILES.get("file")
        if not upload or upload.size > 5 * 1024 * 1024:
            raise ValidationError({"file": "Provide a file no larger than 5 MiB."})
        extension = upload.name.rsplit(".", 1)[-1].lower()
        if extension not in {"csv", "xlsx", "txt", "pdf"}:
            raise ValidationError({"file": "CSV, XLSX, text, or PDF required."})
        raw = upload.read(5 * 1024 * 1024 + 1)
        if len(raw) > 5 * 1024 * 1024:
            raise ValidationError({"file": "File exceeds limit."})
        checksum = hashlib.sha256(raw).hexdigest()
        # Serialize idempotency checks for concurrent deliveries in this tenant.
        m.Workspace.objects.select_for_update().get(pk=ws.pk)
        existing = m.ImportBatch.objects.filter(owner=ws, checksum=checksum).first()
        if existing:
            if existing.source.state != "active":
                raise ValidationError(
                    {"file": "This source was withdrawn. Its original import cannot be reused."}
                )
            return ok(s.ImportSerializer(existing).data)
        mapping = request.data.get("mapping", {})
        if isinstance(mapping, str):
            try:
                mapping = json.loads(mapping)
            except ValueError as exc:
                raise ValidationError({"mapping": "Invalid JSON mapping."}) from exc
        if not isinstance(mapping, dict):
            raise ValidationError({"mapping": "Object required."})
        source = m.Source.objects.create(
            owner=ws,
            title=upload.name[:200],
            kind="ngo_contributed",
            retrieved_at=timezone.now(),
            parser_version="quarantine-v1",
            checksum=checksum,
            upload_identifier=checksum,
        )
        batch = m.ImportBatch.objects.create(
            owner=ws,
            created_by=request.user,
            source=source,
            filename=upload.name[:200],
            format=extension,
            checksum=checksum,
            raw=raw,
            mapping=mapping,
        )
        job = enqueue(
            ws, "parse_import", f"parse:{batch.id}:1", {"batch_id": str(batch.id)}, source
        )
        audit(ws, request.user, "upload.quarantined", batch.id)
        return ok({**s.ImportSerializer(batch).data, "job_id": str(job.id)}, 202)


class ImportDetailView(APIView):
    def get(self, request, pk):
        return ok(
            s.ImportSerializer(
                get_object_or_404(
                    m.ImportBatch, pk=pk, owner=workspace_for(request), source__state="active"
                )
            ).data
        )

    @transaction.atomic
    def patch(self, request, pk):
        ws = workspace_for(request, write=True)
        batch = get_object_or_404(m.ImportBatch, pk=pk, owner=ws, source__state="active")
        source = m.Source.objects.select_for_update().get(pk=batch.source_id)
        if source.state != "active":
            raise NotFound()
        batch = m.ImportBatch.objects.select_for_update().get(pk=batch.pk)
        if batch.status in {"completed", "expired"}:
            raise Conflict("Committed imports are immutable.")
        mapping = request.data.get("mapping")
        if not isinstance(mapping, dict):
            raise ValidationError({"mapping": "Object required."})
        batch.mapping = mapping
        batch.status = "queued"
        batch.save()
        source = m.Source.objects.select_for_update().get(pk=batch.source_id)
        source.revision += 1
        source.save()
        from .services import source_revision_changed

        source_revision_changed(source)
        job = enqueue(
            ws,
            "parse_import",
            f"parse:{batch.id}:{source.revision}",
            {"batch_id": str(batch.id)},
            source,
        )
        return ok({**s.ImportSerializer(batch).data, "job_id": str(job.id)}, 202)


class ImportCommitView(APIView):
    @transaction.atomic
    def post(self, request, pk):
        ws = workspace_for(request, write=True)
        batch = get_object_or_404(m.ImportBatch, pk=pk, owner=ws, source__state="active")
        source = m.Source.objects.select_for_update().get(pk=batch.source_id)
        if source.state != "active":
            raise NotFound()
        if batch.status == "completed":
            return ok(s.ImportSerializer(batch).data)
        if batch.status != "validated":
            raise ValidationError(
                {
                    "status": "Resolve validation errors before committing. Quarantined reports require manual evidence drafting."
                }
            )
        job = enqueue(
            ws,
            "commit_import",
            f"commit:{batch.id}:{batch.source.revision}",
            {"batch_id": str(batch.id)},
            batch.source,
        )
        return ok({"job_id": str(job.id), "status": job.state}, 202)


class ImportRejectedView(APIView):
    def get(self, request, pk):
        batch = get_object_or_404(
            m.ImportBatch, pk=pk, owner=workspace_for(request), source__state="active"
        )
        from philanthra.ingestion import safe_csv

        response = HttpResponse(safe_csv(batch.diagnostics), content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="validation-issues.csv"'
        return response


class OpportunitiesView(APIView):
    def get(self, request):
        ws = workspace_for(request)
        program = list(m.Program.objects.filter(owner=ws))
        rows = []
        for o in m.Opportunity.objects.select_related("source").order_by("deadline"):
            if not can_source(o.source, ws, "donor_access", o.cause, o.geography):
                continue
            matched = any(p.cause == o.cause and p.geography == o.geography for p in program)
            rows.append(
                {
                    "id": str(o.id),
                    "title": o.title,
                    "cause": o.cause,
                    "geography": o.geography,
                    "eligibility": o.eligibility,
                    "deadline": o.deadline,
                    "amount_cents": o.amount_cents,
                    "source": s.SourceSerializer(o.source).data,
                    "matched": matched,
                    "explanation": "Cause and geography match; confirm all eligibility with the funder."
                    if matched
                    else "No complete cause/geography match in your stored programs.",
                    "freshness": "expired" if o.deadline < timezone.now().date() else "open",
                }
            )
        return listing(request, rows)


class RequestsView(APIView):
    def get(self, request):
        ws = workspace_for(request)
        return ok(
            [
                {
                    "id": str(r.id),
                    "kind": r.kind,
                    "note": r.note,
                    "state": r.state,
                    "target_id": str(r.target_id) if r.target_id else None,
                }
                for r in m.ServiceRequest.objects.filter(owner=ws)
            ]
        )

    def post(self, request):
        ws = workspace_for(request, write=True)
        kind = request.data.get("kind")
        if kind not in {"sponsored_onboarding", "introduction", "identity_claim"}:
            raise ValidationError({"kind": "Unsupported request."})
        note = str(request.data.get("note", "")).strip()
        if not note:
            raise ValidationError({"note": "Explain your request."})
        target = None
        if request.data.get("target_id"):
            permitted_recipients = {
                a.owner_id for a in visible_artifacts(ws) if a.status == "approved"
            }
            target = get_object_or_404(
                m.Workspace, pk=request.data["target_id"], id__in=permitted_recipients
            )
        r = m.ServiceRequest.objects.create(owner=ws, kind=kind, note=note, target=target)
        return ok(
            {
                "id": str(r.id),
                "kind": kind,
                "state": r.state,
                "delivery": "Stored for manual follow-up; no outbound message was sent.",
            },
            201,
        )


class DashboardView(APIView):
    def get(self, request):
        ws = workspace_for(request)
        programs = list(m.Program.objects.filter(owner=ws, source__state="active"))
        observations = list(m.Observation.objects.filter(owner=ws, source__state="active"))
        checklist = []
        if not programs:
            checklist.append("Add a program with population, intervention, geography and context.")
        if not observations:
            checklist.append(
                "Import aggregate outcomes with explicit definitions and follow-up periods."
            )
        if any(o.numerator is None for o in observations):
            checklist.append(
                "Collect missing outcome counts (numerators); no improvement rate is available without them."
            )
        if any(not o.outcome.definition.strip() for o in observations):
            checklist.append("Define the outcome before interpreting or comparing observations.")
        if any(not o.followup_months for o in observations):
            checklist.append("Record follow-up periods for comparable outcome interpretation.")
        if any(o.denominator is None for o in observations):
            checklist.append("Collect missing denominators before rate comparisons or pooling.")
        if any(not o.independent for o in observations):
            checklist.append("Document cohort independence; unknown overlap blocks pooling.")
        if any(not p.context for p in programs):
            checklist.append(
                "Add setting, infrastructure and resource context to improve transfer matching."
            )
        return ok(
            {
                "workspace": {
                    "id": str(ws.id),
                    "name": ws.name,
                    "kind": ws.kind,
                    "plan": ws.plan,
                    "metrics_opt_in": ws.metrics_opt_in,
                },
                "programs": s.ProgramSerializer(programs, many=True).data,
                "observation_count": len(observations),
                "data_quality": checklist,
                "entitlements": {"core_contributor": True, "billing_enabled": False},
                "limitations": [
                    "Benchmark coverage depends on compatible permissioned peers.",
                    "Program spending is not a measure of impact.",
                ],
            }
        )


class RecommendationsView(APIView):
    def get(self, request):
        ws = workspace_for(request)
        from philanthra.analytics.matching import match_transfer

        programs = list(m.Program.objects.filter(owner=ws, source__state="active"))
        cards = [
            a
            for a in visible_artifacts(ws, kind="card")
            if a.status == "approved" and a.owner_id != ws.id
        ]

        def profile(p):
            return {
                "cause": p.cause,
                "population": p.population,
                "intervention": p.intervention,
                "geography": p.geography,
                **p.context,
            }

        rows = [
            {
                "id": str(a.id),
                "source_ids": [str(x) for x in a.sources.values_list("id", flat=True)],
                "title": a.title,
                "evidence_label": a.card.evidence_label,
                "failures": a.card.failures,
                **profile(a.card.program),
            }
            for a in cards
        ]
        return ok(
            [
                {
                    "program_id": str(p.id),
                    "program_name": p.name,
                    "matches": match_transfer(
                        profile(p),
                        [
                            row
                            for row in rows
                            if all(
                                can_source(dep.source, ws, "benchmarking", p.cause, p.geography)
                                for dep in next(
                                    a for a in cards if str(a.id) == row["id"]
                                ).dependencies.select_related("source")
                            )
                        ],
                    ),
                }
                for p in programs
            ]
        )


METRICS = {
    "overlooked_grants": "Completed grants to previously overlooked grantees / all completed grants; donor attestation.",
    "high_need_funding": "Actual cents granted in identified high-need areas / all actual grant cents; donor attestation.",
    "research_minutes_saved": "Self-reported minutes saved against documented baseline / completed research tasks.",
    "alert_usefulness": "Alerts rated useful / alerts rated; voluntary feedback.",
    "insight_adoption": "Explicitly documented pilot adoptions / reviewed insights; owner report.",
    "data_quality_improvement": "Resolved validation issues / baseline issues; measured import feedback.",
    "cost_avoided": "Owner-reported implementation cost avoided; counterfactual unverified.",
    "outcome_change": "Measured post-adoption change; no causal attribution to Philanthra.",
    "continuing_contributors": "Consenting contributors active in both periods / prior period contributors.",
}


class MetricsView(APIView):
    def get(self, request):
        ws = workspace_for(request)
        events = list(m.PilotEvent.objects.filter(owner=ws).order_by("created_at", "id"))
        if request.query_params.get("format") == "csv":
            from philanthra.ingestion import safe_csv

            columns = [
                "metric",
                "definition",
                "value",
                "denominator",
                "period_start",
                "period_end",
                "collection_method",
                "source_kind",
                "ground_truth",
            ]
            rows = [
                {
                    "metric": e.metric,
                    "definition": METRICS[e.metric],
                    "value": str(e.value),
                    "denominator": str(e.denominator) if e.denominator is not None else "",
                    "period_start": e.period_start,
                    "period_end": e.period_end,
                    "collection_method": e.collection_method,
                    "source_kind": e.source_kind,
                    "ground_truth": "Fictional demo event; not traction"
                    if e.source_kind == "synthetic_demo"
                    else "Self-reported; not independently verified or causally attributed",
                }
                for e in events
            ]
            audit(ws, request.user, "metrics.exported", ws.id)
            response = HttpResponse(safe_csv(rows, columns), content_type="text/csv")
            response["Content-Disposition"] = 'attachment; filename="philanthra-pilot-metrics.csv"'
            return response
        return ok(
            {
                "opted_in": ws.metrics_opt_in,
                "definitions": METRICS,
                "events": [
                    {
                        "id": str(e.id),
                        "metric": e.metric,
                        "value": str(e.value),
                        "denominator": str(e.denominator) if e.denominator is not None else None,
                        "period_start": e.period_start,
                        "period_end": e.period_end,
                        "collection_method": e.collection_method,
                        "source_kind": e.source_kind,
                    }
                    for e in events
                ],
                "ground_truth": "unavailable"
                if not events
                else "self-reported; not independently verified",
                "warning": "Draft allocations, clicks, and synthetic events are not actual funding or traction.",
            }
        )

    def patch(self, request):
        ws = workspace_for(request, admin=True)
        value = request.data.get("opted_in")
        if not isinstance(value, bool):
            raise ValidationError({"opted_in": "Boolean required."})
        ws.metrics_opt_in = value
        ws.save()
        return ok({"opted_in": value})

    def post(self, request):
        ws = workspace_for(request, write=True)
        if not ws.metrics_opt_in:
            raise PermissionDenied("Workspace owner must opt in first.")
        if request.data.get("metric") not in METRICS:
            raise ValidationError({"metric": "Unknown metric."})
        fields = {
            k: request.data.get(k)
            for k in [
                "metric",
                "value",
                "denominator",
                "period_start",
                "period_end",
                "collection_method",
            ]
        }
        if not fields["collection_method"]:
            raise ValidationError(
                {"collection_method": "Describe actual collection and ground truth."}
            )
        from django.conf import settings

        event = m.PilotEvent(
            owner=ws,
            source_kind="synthetic_demo" if settings.DEMO_MODE else "ngo_contributed",
            **fields,
        )
        event.full_clean(exclude=["denominator"] if event.denominator is None else [])
        if event.period_start > event.period_end:
            raise ValidationError({"period_end": "Must be on or after the period start."})
        if event.denominator is not None and event.denominator <= 0:
            raise ValidationError({"denominator": "A supplied denominator must be positive."})
        if event.metric != "outcome_change" and event.value < 0:
            raise ValidationError({"value": "This measure requires a nonnegative value."})
        if event.metric in {
            "overlooked_grants",
            "high_need_funding",
            "alert_usefulness",
            "insight_adoption",
            "data_quality_improvement",
            "continuing_contributors",
        }:
            if event.denominator is None or event.value > event.denominator:
                raise ValidationError(
                    {"denominator": "Provide a positive total at least as large as the numerator."}
                )
        event.save()
        return ok({"id": str(event.id)}, 201)


class ReportView(APIView):
    def get(self, request, pk):
        ws = workspace_for(request)
        artifact = artifact_or_404(pk, ws, user=request.user)
        audit(ws, request.user, "artifact.exported", artifact.id, revision=artifact.revision)
        if request.query_params.get("format") == "csv":
            from philanthra.ingestion import safe_csv

            rows = []
            if artifact.kind == "portfolio":
                rows = [
                    {
                        "organization": a.organization.name,
                        "amount_cents": a.amount_cents,
                        "currency": artifact.portfolio.currency,
                        "review_status": artifact.status,
                        "source_kind": artifact.source_kind,
                        "source_ids": ";".join(
                            str(x) for x in artifact.sources.values_list("id", flat=True)
                        ),
                        "caveat": "Planning allocation; no money transferred.",
                    }
                    for a in artifact.portfolio.allocations.select_related("organization")
                ]
            elif artifact.kind == "analysis":
                rows = [
                    {
                        "title": artifact.title,
                        "review_status": artifact.status,
                        "source_kind": artifact.source_kind,
                        "analysis": json.dumps(artifact.payload),
                    }
                ]
            else:
                rows = [
                    {
                        "title": artifact.title,
                        "review_status": artifact.status,
                        "source_kind": artifact.source_kind,
                        "summary": artifact.payload.get("summary", ""),
                    }
                ]
            from .policy import artifact_attributions

            attribution = "; ".join(item["text"] for item in artifact_attributions(artifact, ws))
            for row in rows:
                row["required_attribution"] = attribution
            response = HttpResponse(safe_csv(rows), content_type="text/csv")
            response["Content-Disposition"] = 'attachment; filename="philanthra-report.csv"'
            return response
        return ok(
            s.PortfolioSerializer(artifact, context={"workspace": ws}).data
            if artifact.kind == "portfolio"
            else s.ArtifactSerializer(artifact, context={"workspace": ws}).data
        )


class ImportTemplateView(APIView):
    def get(self, request):
        workspace_for(request)
        from philanthra.ingestion import safe_csv

        common = [
            "record_type",
            "program_name",
            "cause",
            "intervention",
            "population",
            "geography",
            "period_start",
            "period_end",
        ]
        kind = request.query_params.get("kind", "outcome")
        if kind == "outcome":
            fields = common + [
                "outcome_code",
                "outcome_definition",
                "unit",
                "direction",
                "numerator",
                "denominator",
                "cohort_id",
                "study_id",
                "independent",
                "followup_months",
                "comparator",
                "study_design",
                "uncertainty",
                "missingness",
                "stratum",
            ]
        elif kind == "cost":
            fields = common + ["amount", "currency", "unit", "denominator"]
        else:
            raise ValidationError({"kind": "Choose outcome or cost."})
        response = HttpResponse(safe_csv([], fields), content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="philanthra-{kind}-template.csv"'
        return response
