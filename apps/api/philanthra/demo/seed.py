"""Synthetic fixtures persisted through the same review and allocation services as the API."""

import hashlib
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import NAMESPACE_URL, uuid5

from django.contrib.auth import get_user_model
from django.db import transaction

from philanthra.core import models as m
from philanthra.core.services import (
    audit,
    create_artifact,
    create_portfolio,
    decide_review,
    submit_review,
)

CLOCK = datetime(2026, 9, 1, 12, tzinfo=UTC)
PASSWORD = "Demo-only-Banyan-2026!"
SEED_VERSION = "baltimore-food-v1"


def sid(value):
    return uuid5(NAMESPACE_URL, f"https://example.invalid/philanthra-demo/{value}")


def source(key, title, owner=None, **kwargs):
    return m.Source.objects.create(
        id=sid(f"source/{key}"),
        owner=owner,
        title=f"Fictional demo · {title}",
        kind="synthetic_demo",
        retrieved_at=CLOCK,
        parser_version="demo-fixture-v1",
        checksum=hashlib.sha256(key.encode()).hexdigest(),
        locator=f"seed/{key}",
        transformations=["Deterministic synthetic fixture; no real-world claim"],
        **kwargs,
    )


def grant(src, purpose, recipient=None, audience="public"):
    return m.DataGrant.objects.create(
        source=src,
        purpose=purpose,
        recipient=recipient,
        audience=audience,
        cause=src.cause,
        geography=src.geography,
        attribution="Fictional Banyan demonstration; no real organizations or studies.",
    )


@transaction.atomic
def seed_demo():
    # Serialize concurrent init jobs. Startup never resets or overwrites user-created records.
    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_advisory_xact_lock(72401926)")
    from philanthra.catalog.context import ensure_public_context

    ensure_public_context()
    if m.AuditEvent.objects.filter(action="demo.seed", object_id=SEED_VERSION).exists():
        from .upgrade import upgrade_early_fixture_periods

        upgrade_early_fixture_periods()
        return "Demo already seeded; existing records and user changes preserved."
    User = get_user_model()
    roles = [
        "foundation-admin",
        "foundation-analyst",
        "foundation-viewer",
        "second-foundation",
        "ngo-owner",
        "ngo-editor",
        "ngo-viewer",
        "reviewer",
        "platform-admin",
        "ngo2-owner",
        "ngo3-owner",
        "ngo4-owner",
    ]
    users = {}
    for username in roles:
        if User.objects.filter(username=username).exists():
            raise ValueError(
                "Reserved demo username already exists; refusing to overwrite credentials."
            )
        users[username] = User.objects.create_user(
            username=username,
            password=PASSWORD,
            email=f"{username}@demo.invalid",
            is_staff=username == "platform-admin",
        )
    foundation = m.Workspace.objects.create(
        id=sid("workspace/foundation1"),
        name="Demo · Tidemark Foundation",
        kind="foundation",
        plan="institutional_pilot",
        metrics_opt_in=True,
    )
    foundation2 = m.Workspace.objects.create(
        id=sid("workspace/foundation2"),
        name="Demo · Orchard Foundation",
        kind="foundation",
        plan="institutional_pilot",
    )
    for username, role in [
        ("foundation-admin", "administrator"),
        ("foundation-analyst", "analyst"),
        ("foundation-viewer", "viewer"),
        ("reviewer", "reviewer"),
        ("platform-admin", "administrator"),
    ]:
        m.Membership.objects.create(workspace=foundation, user=users[username], role=role)
    m.Membership.objects.create(
        workspace=foundation2, user=users["second-foundation"], role="administrator"
    )
    # Admin deliberately has no other workspace/private-source membership.
    context_source = source(
        "geography",
        "Illustrative service geography",
        period_start=date(2025, 1, 1),
        period_end=date(2025, 12, 31),
    )
    areas = []
    for i, (code, label) in enumerate(
        [
            ("21201", "Central Baltimore"),
            ("21202", "East Downtown"),
            ("21205", "East Baltimore"),
            ("21206", "Northeast Baltimore"),
            ("21207", "West Metro"),
            ("21215", "Northwest Baltimore"),
            ("21218", "North Baltimore"),
            ("21224", "Southeast Baltimore"),
        ]
    ):
        areas.append(
            m.Geography.objects.create(
                id=sid(f"area/{code}"),
                code=code,
                name=label,
                kind="reported_zip_service_area",
                latitude=Decimal("39.270") + Decimal(i // 4) * Decimal("0.035"),
                longitude=Decimal("-76.680") + Decimal(i % 4) * Decimal("0.025"),
                source=context_source,
                context={
                    "synthetic": True,
                    "map_basis": "schematic; not ZIP boundaries",
                    "poverty_estimate": None,
                    "poverty_missing_reason": "No ZIP-level measurement loaded. County context is separate.",
                    "boundary_vintage": None,
                },
            )
        )
    names = [
        "Aster Table",
        "Juniper Pantry",
        "Lantern Food Network",
        "Cedar Meal Collective",
        "Willow Community Kitchen",
        "Marigold Market",
        "Mosaic Food Access",
        "Harbor Seed Project",
        "Oriole Neighbors",
        "Compass Groceries",
        "Meadow Meal Partners",
        "Copperleaf Nutrition",
        "Daybreak Pantry",
        "Elm Street Food Lab",
        "Ginkgo Community Table",
        "Linden Harvest",
        "Paperboat Meals",
        "Rainbird Produce",
        "Sandpiper Kitchen",
        "Sunroom Food Exchange",
    ]
    international = [
        ("ET", "Demo · Highland Nutrition Learning"),
        ("MX", "Demo · Milpa Family Meals"),
        ("GT", "Demo · Valley Community Nutrition"),
        ("KE", "Demo · Coastal Pantry Learning"),
    ]
    organizations, workspaces, programs, card_sources = [], [], [], []
    for i in range(24):
        country, name = ("US", f"Demo · {names[i]}") if i < 20 else international[i - 20]
        org = m.Organization.objects.create(
            id=sid(f"org/{i + 1}"),
            name=name,
            mission="Fictional organization exploring reliable food access through community delivery and practical learning.",
            country=country,
            headquarters_zip=areas[i % 8].code if i < 20 else "",
            population="household",
            status="synthetic_demo",
            capacity_cents=None if i % 5 == 4 else (i + 2) * 500000,
            capacity_note="Unknown; donor planning assumption required."
            if i % 5 == 4
            else "Synthetic disclosed planning cap; not a verified funding request.",
        )
        m.ExternalIdentifier.objects.create(
            organization=org, namespace="philanthra_demo", value=f"{country.lower()}-{i + 1:03}"
        )
        ws = m.Workspace.objects.create(
            id=sid(f"workspace/ngo{i + 1}"),
            name=name,
            kind="ngo",
            organization=org,
            plan="contributor_free",
            metrics_opt_in=i < 4,
        )
        organizations.append(org)
        workspaces.append(ws)
        if i == 0:
            for username, role in [
                ("ngo-owner", "owner"),
                ("ngo-editor", "editor"),
                ("ngo-viewer", "viewer"),
            ]:
                m.Membership.objects.create(workspace=ws, user=users[username], role=role)
        elif i < 4:
            m.Membership.objects.create(workspace=ws, user=users[f"ngo{i + 1}-owner"], role="owner")
        if i < 20:
            m.ServiceArea.objects.create(
                organization=org,
                geography=areas[i % 8],
                source=context_source,
                basis="synthetic_reported",
            )
            if i % 3 == 0:
                m.ServiceArea.objects.create(
                    organization=org,
                    geography=areas[(i + 1) % 8],
                    source=context_source,
                    basis="synthetic_reported",
                )
            for year in (2020, 2021, 2022) if i == 12 else (2023, 2024, 2025):
                scale = Decimal(80000 + i * 65000)
                expenses = scale * (Decimal("1.05") ** (year - 2023))
                revenue = expenses * (Decimal("0.89") if i in (2, 7, 13) else Decimal("1.08"))
                caveats = []
                if i == 5 and year == 2024:
                    revenue *= 3
                    caveats = ["One-time synthetic restricted grant; growth is not comparable."]
                ratio = (
                    Decimal("0.95")
                    if i == 0
                    else Decimal("0.64")
                    if i == 1
                    else Decimal("0.70") + Decimal(i % 5) / 25
                )
                src = source(
                    f"filing/{i}/{year}",
                    f"{name} {year} financial fixture",
                    period_start=date(year, 1, 1),
                    period_end=date(year, 12, 31),
                )
                if i == 12:
                    src.retrieved_at = datetime(2023, 1, 1, tzinfo=UTC)
                    src.save()
                m.Filing.objects.create(
                    id=sid(f"filing/{i}/{year}"),
                    organization=org,
                    source=src,
                    form="990-EZ" if i == 9 else "990",
                    tax_year=year,
                    period_start=date(year, 1, 1),
                    period_end=date(year, 12, 31),
                    revenue=revenue.quantize(Decimal(".01")),
                    expenses=expenses.quantize(Decimal(".01")),
                    program_expenses=None
                    if i == 9
                    else (expenses * ratio).quantize(Decimal(".01")),
                    assets=scale * 2,
                    liabilities=scale * (Decimal("2.3") if i == 7 else Decimal(".4")),
                    cash=scale * Decimal(".15") if i % 3 else None,
                    caveats=caveats,
                )
                if i == 3 and year == 2024:
                    old = m.Filing.objects.get(id=sid(f"filing/{i}/{year}"))
                    old.active = False
                    old.save()
                    amended = source(
                        f"amended/{i}/{year}",
                        f"{name} amended {year} fixture",
                        period_start=date(year, 1, 1),
                        period_end=date(year, 12, 31),
                    )
                    m.Filing.objects.create(
                        organization=org,
                        source=amended,
                        form="990",
                        tax_year=year,
                        period_start=date(year, 1, 1),
                        period_end=date(year, 12, 31),
                        revision=2,
                        amended=True,
                        revenue=old.revenue + 5000,
                        expenses=old.expenses,
                        program_expenses=old.program_expenses,
                        assets=old.assets,
                        liabilities=old.liabilities,
                        cash=old.cash,
                        caveats=["Amended synthetic filing; original preserved."],
                    )
        src = source(
            f"program/{i}",
            f"{name} implementation record",
            owner=ws,
            geography="US-MD-Baltimore" if i < 20 else country,
        )
        card_sources.append(src)
        context = {
            "setting": "urban" if i < 20 else "rural",
            "delivery_mechanism": "community_delivery",
            "duration_days": 90,
            "infrastructure": "community kitchen" if i < 20 else None,
            "resource_level": "limited",
            "language": "English" if i < 20 else None,
            "public_services": None,
            "delivery_partner": "fictional community organization",
            "income_context": None,
            "constraints": ["Storage capacity", "Follow-up completion"],
            "country": country,
        }
        program = m.Program.objects.create(
            id=sid(f"program/{i}"),
            owner=ws,
            organization=org,
            source=src,
            name="Community food access and household follow-up",
            intervention="food_access",
            population="household",
            geography="US-MD-Baltimore" if i < 20 else country,
            context=context,
        )
        programs.append(program)
        grant(src, "donor_access")
        grant(src, "benchmarking")
        if i >= 20:
            m.DataGrant.objects.create(
                source=src,
                purpose="benchmarking",
                audience="public",
                cause=src.cause,
                geography="US-MD-Baltimore",
                attribution="Fictional international demonstration; contextual transfer requires adaptation.",
            )
        grant(src, "publication")
        label = (
            "early hypothesis"
            if i == 0
            else "quasi-experimental finding"
            if i == 1
            else "descriptive observation"
        )
        actor = (
            users["ngo-owner"]
            if i == 0
            else users.get(f"ngo{i + 1}-owner", users["foundation-admin"])
        )
        artifact = create_artifact(
            ws,
            actor,
            kind="card",
            title=f"{name}: household follow-up learning",
            geography=program.geography,
            sources=[src],
            payload={
                "context": context,
                "synthetic": True,
                "outcome_definition": "food_security_improved",
                "implementation_status": "discontinued" if i == 7 else "pilot",
                "followup_days": 90,
            },
        )
        m.Card.objects.create(
            artifact=artifact,
            program=program,
            evidence_label=label,
            study_design="quasi_experimental" if i == 1 else "observational",
            implementation_steps="1. Agree delivery times with households.\n2. Pair food access with fortnightly follow-up.\n3. Record a defined outcome at 90 days.",
            barriers="Transport reliability and incomplete follow-up.",
            failures="Discontinued evening pickup after low participation."
            if i == 7
            else "Some households did not complete follow-up; selection may affect results.",
            caveats="Entirely fictional demonstration. No causal or real-world effectiveness claim. Implementation learning requires local adaptation.",
            attribution=f"{name}; synthetic demonstration",
        )
        m.Claim.objects.create(
            artifact=artifact,
            text="Scheduled follow-up exposed delivery barriers in this fictional program.",
            source=src,
            locator="seed/implementation_steps",
            label="source-reported synthetic claim",
        )
        submit_review(artifact, actor, users["reviewer"].id, 1)
        decide_review(
            artifact,
            users["reviewer"],
            1,
            "approved",
            "Demo review event only; not real expert validation. Source and limitations inspected in synthetic fixture.",
        )
        edges = [
            ("organization", str(org.id), "program", str(program.id), "delivers"),
            ("program", str(program.id), "cause", "food_security", "addresses"),
            ("program", str(program.id), "intervention", "food_access", "uses"),
            ("program", str(program.id), "population", "household", "serves"),
            ("program", str(program.id), "geography", program.geography, "reported_service_area"),
            ("program", str(program.id), "evidence", str(artifact.id), "documented_by"),
        ]
        for st, si, tt, ti, relation in edges:
            m.GraphEdge.objects.create(
                artifact=artifact,
                source_type=st,
                source_id=si,
                target_type=tt,
                target_id=ti,
                relation=relation,
                supporting_source=src,
            )
    outcome = m.OutcomeDefinition.objects.create(
        id=sid("outcome/improved"),
        code="food_security_improved",
        name="Household food-security improvement at 90 days",
        definition="Synthetic binary indicator: household meets the predefined improvement threshold at follow-up. Not a validated instrument.",
        unit="proportion",
        direction="higher_is_better",
    )
    incompatible = m.OutcomeDefinition.objects.create(
        id=sid("outcome/meals"),
        code="meals_distributed",
        name="Meals distributed (output)",
        definition="Output count, incompatible with household outcomes.",
        unit="count",
        direction="higher_is_better",
    )
    for i in range(4):
        ws, program = workspaces[i], programs[i]
        src = source(
            f"outcomes/{i}",
            f"{organizations[i].name} aggregated cohorts",
            owner=ws,
            period_start=date(2023, 1, 1),
            period_end=date(2025, 3, 31),
        )
        for recipient in [foundation, ws, workspaces[0]]:
            for purpose in ("pooled_analysis", "publication", "benchmarking"):
                grant(src, purpose, recipient, "workspace")
        for j in range(15):
            # Main fixture: compatible disjoint cohorts, rates 50/60/70/80%, all complements >=10.
            denominator, numerator = 100, 50 + i * 10
            definition = outcome
            if j == 12:
                denominator, numerator = 12, 9  # complementary disclosure suppression
            if j == 13:
                definition = incompatible
            if j == 14:
                numerator = None  # collection suggestion fixture
            observation_year = 2024 if j == 12 else 2023 if j == 14 else 2025
            m.Observation.objects.create(
                id=sid(f"observation/{i}/{j}"),
                owner=ws,
                program=program,
                source=src,
                outcome=definition,
                numerator=numerator,
                denominator=denominator,
                cohort_id=f"demo-household-{i}-{j}",
                study_id=f"demo-study-{i}-{j}",
                independent=True,
                period_start=date(observation_year, 1, 1),
                period_end=date(observation_year, 3, 31),
                followup_months=3,
                comparator="none",
                study_design="observational",
                missingness="Numerator not collected"
                if j == 14
                else "Complete synthetic fixture; real attrition unknown",
                uncertainty="Not reported; no inferential interval",
                locator=f"row/{j + 1}",
            )
        m.CostObservation.objects.create(
            owner=ws,
            program=program,
            source=src,
            amount=Decimal(18000 + i * 1200),
            currency="USD",
            denominator=100,
            unit="household",
            period_start=date(2025, 1, 1),
            period_end=date(2025, 3, 31),
        )
    for index, (title, budget, indices) in enumerate(
        [
            ("Neighborhood food access", 10000000, [0, 1, 2]),
            ("Small grant, known caps", 500001, [3, 5]),
            ("Capacity assumptions needed", 7500000, [4, 9]),
        ]
    ):
        artifact = create_portfolio(
            foundation,
            users["foundation-admin"],
            {
                "name": title,
                "budget_cents": budget,
                "currency": "USD",
                "candidates": [
                    {
                        "organization_id": str(organizations[i].id),
                        "weight": str(1 + (i % 3)),
                        "cap_cents": organizations[i].capacity_cents,
                    }
                    for i in indices
                ],
                "constraints": {
                    "risk_preference": "include_capacity_building",
                    "priority": "equal opportunity with disclosed user weights",
                },
            },
        )
        if index == 0:
            for n in range(6):
                m.Alert.objects.create(
                    owner=foundation,
                    artifact=artifact,
                    title=[
                        "Fictional filing revision available",
                        "Planning assumptions need review",
                        "Source freshness needs checking",
                        "Potential collaboration to investigate",
                        "New implementation lesson available",
                        "Portfolio geographic coverage",
                    ][n],
                    explanation="Synthetic monitoring event. Inspect source snapshots before acting; recorded coverage is incomplete.",
                    fingerprint=f"demo-seed-alert-{n}",
                )
    for i in range(4):
        src = source(f"opportunity/{i}", f"Curated demo opportunity {i + 1}")
        m.Opportunity.objects.create(
            title=f"Demo · Food access learning grant {i + 1}",
            cause="food_security",
            geography="US-MD-Baltimore",
            eligibility="Fictional eligibility: Baltimore-area community food programs; no real grant is offered.",
            deadline=date(2026, 12, 1 + i),
            amount_cents=(i + 1) * 2500000,
            source=src,
        )
    for ws in [foundation, foundation2, *workspaces[:4]]:
        m.Subscription.objects.create(owner=ws)
    audit(
        foundation,
        users["foundation-admin"],
        "demo.seed",
        SEED_VERSION,
        clock=CLOCK.isoformat(),
        synthetic=True,
    )
    return "Seeded 24 fictional organizations, 60 aggregate observations, 24 reviewed demo cards, 3 portfolios and 6 alerts."
