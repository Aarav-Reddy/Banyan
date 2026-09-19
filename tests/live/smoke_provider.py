"""Explicit optional live check; filename excludes it from deterministic test discovery."""

import os

import pytest
from philanthra.explanations.provider import explain


@pytest.mark.live
def test_explicit_responses_smoke_uses_only_synthetic_evidence():
    if os.getenv("PHILANTHRA_LIVE_SMOKE") != "1":
        pytest.skip(
            "Set PHILANTHRA_LIVE_SMOKE=1 explicitly to authorize this optional network test."
        )
    model = os.getenv("PHILANTHRA_LLM_MODEL", "")
    key = os.getenv("OPENAI_API_KEY", "")
    if not model or not key:
        pytest.fail("Configure an application model and API key for the explicitly enabled smoke.")
    claim = {
        "id": "synthetic-smoke-claim",
        "text": "This fictional smoke-test program reported a delivery barrier; it is not a real study.",
        "source_id": "synthetic-smoke-source",
        "locator": "test/fictional-claim",
        "evidence_label": "early hypothesis",
        "active": True,
        "reviewed": True,  # Fixture boundary flag, not real human expert review.
        "external_processing": True,
    }
    result = explain([claim], provider="openai", model=model, key=key)
    assert result["mode"] == "generated_selection", "Live provider fell back; smoke did not pass."
    assert result["claims"][0]["claim_id"] == claim["id"]
    assert result["claims"][0]["text"] == claim["text"]
    assert result["claims"][0]["source_id"] == claim["source_id"]
