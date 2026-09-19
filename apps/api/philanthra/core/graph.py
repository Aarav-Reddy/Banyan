"""One-hop graph over persisted typed relationships, authorized before disclosure."""

from . import models as m
from .policy import can_source, visible_artifacts


def graph_rows(workspace, user, root=None, limit=100):
    visible = {a.id: a for a in visible_artifacts(workspace, user=user)}
    result = []
    seen = set()

    def add(identifier, artifact, source, start_type, start, end_type, end, relation):
        start, end = str(start), str(end)
        if len(result) >= limit or (root and root not in {start, end}) or identifier in seen:
            return
        if not can_source(source, workspace, artifact.purpose, artifact.cause, artifact.geography):
            return
        seen.add(identifier)
        result.append(
            {
                "id": identifier,
                "source_type": start_type,
                "source_id": start,
                "target_type": end_type,
                "target_id": end,
                "relation": relation,
                "artifact_id": str(artifact.id),
                "supporting_source_id": str(source.id),
            }
        )

    # Derived relationships use normalized foreign keys, never guessed textual matches.
    for artifact in visible.values():
        if artifact.kind == "portfolio":
            source = artifact.sources.filter(
                owner=workspace, parser_version="planning-input-v1"
            ).first()
            if source:
                for allocation in artifact.portfolio.allocations.select_related("organization")[
                    :100
                ]:
                    add(
                        f"allocation:{allocation.id}",
                        artifact,
                        source,
                        "organization",
                        allocation.organization_id,
                        "funder_workspace",
                        artifact.owner_id,
                        "proposed_allocation_no_transfer",
                    )
        if artifact.kind != "card":
            continue
        program = artifact.card.program
        for observation in m.Observation.objects.filter(program=program).select_related(
            "source", "outcome"
        )[:100]:
            add(
                f"outcome:{observation.id}",
                artifact,
                observation.source,
                "program",
                program.id,
                "outcome_definition",
                observation.outcome_id,
                "reports_aggregate_observation",
            )
        for cost in m.CostObservation.objects.filter(program=program).select_related("source")[
            :100
        ]:
            add(
                f"cost:{cost.id}",
                artifact,
                cost.source,
                "program",
                program.id,
                "cost_observation",
                cost.id,
                "reports_cost_in_source_period",
            )
        for funding in m.FundingRecord.objects.filter(
            organization=program.organization
        ).select_related("source")[:100]:
            add(
                f"funding:{funding.id}",
                artifact,
                funding.source,
                "organization",
                program.organization_id,
                "funder",
                funding.funder_id,
                f"reported_{funding.type}",
            )
        if len(result) >= limit:
            break
    query = m.GraphEdge.objects.filter(artifact_id__in=visible).select_related("supporting_source")
    if root:
        from django.db.models import Q

        query = query.filter(Q(source_id=root) | Q(target_id=root))
    for edge in query.order_by("id")[:1000]:
        add(
            str(edge.id),
            visible[edge.artifact_id],
            edge.supporting_source,
            edge.source_type,
            edge.source_id,
            edge.target_type,
            edge.target_id,
            edge.relation,
        )
    return result
