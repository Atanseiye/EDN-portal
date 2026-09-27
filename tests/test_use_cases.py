import pytest
from fastapi.testclient import TestClient

import server.main as main
from ednai.models import Generation
from ednai.providers import NATLAS_MODEL_ID
from ednai.use_cases import USE_CASES, build_use_case_prompt, public_use_case_registry

client = TestClient(main.app)

EXPECTED = {
    "chatbot",
    "translation",
    "education",
    "culture",
    "government",
    "digital_inclusion",
    "research",
    "song",
}


def test_registry_exposes_all_official_use_case_workflows():
    registry = public_use_case_registry()
    assert set(registry["use_cases"]) == EXPECTED
    assert set(registry["languages"]) == {"english", "yoruba", "hausa", "igbo"}
    for slug in EXPECTED:
        assert registry["use_cases"][slug]["example_inputs"]


def test_translation_prompt_is_target_language_specific():
    system, user, language = build_use_case_prompt(
        "translation",
        "english",
        {
            "source_language": "english",
            "target_language": "yoruba",
            "text": "Welcome to EDNAi.",
        },
    )
    assert "Yorùbá" in system
    assert "Translate faithfully" in system
    assert "Welcome to EDNAi." in user
    assert language == "yoruba"


def test_government_workflow_requires_authoritative_grounding_for_specifics():
    system, _, _ = build_use_case_prompt(
        "government",
        "hausa",
        {
            "service": "Public application",
            "question": "What should I prepare?",
        },
    )
    assert "authoritative context" in system
    assert "responsible agency" in system
    assert "impersonate" in system


def test_song_workflow_is_text_only_and_original():
    system, _, _ = build_use_case_prompt(
        "song",
        "igbo",
        {
            "theme": "hope",
            "mood": "uplifting",
            "structure": "verse_chorus",
        },
    )
    assert "original song lyrics" in system
    assert "text-only" in system
    assert "audio synthesis" in system


def test_missing_required_input_fails_before_inference():
    client.post("/api/developer/login", json={"email": "demo@edn.com", "password": "12345"})
    response = client.post(
        "/v1/use-cases/education",
        json={"language": "english", "inputs": {"topic": "Energy"}},
    )
    assert response.status_code == 400
    assert "learner_level" in response.json()["detail"]


def test_unknown_use_case_is_404():
    client.post("/api/developer/login", json={"email": "demo@edn.com", "password": "12345"})
    response = client.post(
        "/v1/use-cases/not-real",
        json={"language": "english", "inputs": {}},
    )
    assert response.status_code == 404


def test_use_case_endpoint_executes_through_natlas_provider(monkeypatch):
    class FakeProvider:
        def generate(self, messages, *, model, temperature, max_tokens, json_mode):
            assert model == NATLAS_MODEL_ID
            assert messages[0].role == "system"
            assert messages[1].role == "user"
            return Generation(
                text="Structured N-ATLaS result",
                model=NATLAS_MODEL_ID,
                provider="test-natlas",
                latency_ms=12.5,
            )

    monkeypatch.setattr(main, "provider", FakeProvider())
    login = client.post(
        "/api/developer/login",
        json={"email": "demo@edn.com", "password": "12345"},
    )
    assert login.status_code == 200
    response = client.post(
        "/v1/use-cases/chatbot",
        json={
            "language": "yoruba",
            "inputs": {
                "message": "Kí ni API?",
                "persona": "developer assistant",
            },
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["use_case"] == "chatbot"
    assert body["language"] == "yoruba"
    assert body["model"] == NATLAS_MODEL_ID
    assert body["provider"] == "test-natlas"
    assert body["text"] == "Structured N-ATLaS result"
