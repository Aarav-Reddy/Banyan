import os

from django.conf import settings
from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from philanthra.core.models import Source
from philanthra.core.policy import artifact_or_404, can_source, workspace_for
from philanthra.core.services import audit

from .provider import explain


class ExplanationView(APIView):
    @extend_schema(
        operation_id="explanation_create",
        request=None,
        responses={200: {"type": "object", "properties": {"data": {"type": "object"}}}},
    )
    @transaction.atomic
    def post(self, request, pk):
        ws = workspace_for(request)
        artifact = artifact_or_404(pk, ws, user=request.user)
        # Withdrawal and generation use the same source locks. No queued authorization cache.
        list(
            Source.objects.select_for_update().filter(dependency__artifact=artifact).order_by("id")
        )
        artifact = artifact_or_404(pk, ws, user=request.user)
        claims = []
        for claim in artifact.claims.select_related("source"):
            if can_source(claim.source, ws, artifact.purpose, artifact.cause, artifact.geography):
                claims.append(
                    {
                        "id": str(claim.id),
                        "text": claim.text,
                        "source_id": str(claim.source_id),
                        "locator": claim.locator,
                        "evidence_label": artifact.card.evidence_label
                        if hasattr(artifact, "card")
                        else claim.label,
                        "reviewed": artifact.status == "approved",
                        "active": claim.source.state == "active",
                        "external_processing": can_source(
                            claim.source, ws, "external_ai", artifact.cause, artifact.geography
                        ),
                    }
                )
        output = explain(
            claims,
            provider=settings.PHILANTHRA_LLM_PROVIDER,
            model=settings.PHILANTHRA_LLM_MODEL,
            key=os.getenv("OPENAI_API_KEY", ""),
        )
        audit(ws, request.user, "explanation.generated", artifact.id, mode=output["mode"])
        return Response({"data": output, "meta": {}})
