from fastapi.testclient import TestClient

from ednai.providers import NATLAS_MODEL_ID
from server.main import app

client = TestClient(app)


def test_health_and_model_discovery():
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["model"] == NATLAS_MODEL_ID

    models = client.get("/v1/models")
    assert models.status_code == 200
    assert models.json()["data"][0]["id"] == NATLAS_MODEL_ID


def test_playground_and_guides_are_real_pages():
    assert client.get("/").status_code == 200
    page = client.get("/").text
    assert "Build with" in page
    assert "Evaluation Workbench" in page
    assert "Dataset Studio" in page
    assert "Fine-tune Planner" in page
    assert "Runtime & SDK" in page
    assert "Speech Studio" in page
    assert "Use Case Studio" in page
    assert "8 N-ATLaS workflows" in page
    assert "Automatic Speech Recognition" in page
    assert "Device Speech Synthesis" not in page
    assert "Official NCAIR / N-ATLaS ASR only" in page
    assert "Developer launchpad" in page
    assert "Your first N-ATLaS request in minutes." in page
    assert "Try a template." in page
    assert 'id="commandPalette"' in page
    assert "/api/studio/starter.zip" in page
    assert client.head("/").status_code == 200
    assert client.get("/guide").status_code == 200
    assert client.get("/guide/en").status_code == 200
    assert client.get("/guide/yo").status_code == 200
    assert client.get("/guide/ha").status_code == 200
    assert client.get("/guide/ig").status_code == 200
    assert client.get("/challenge").status_code == 200


def test_wrong_model_is_rejected_before_inference():
    r = client.post(
        "/v1/generate",
        json={
            "model": "another/model",
            "messages": [{"role": "user", "content": "hello"}],
        },
    )
    assert r.status_code == 400
    assert "NCAIR1/N-ATLaS" in r.json()["detail"]


def test_capabilities_expose_direct_natlas_tooling():
    body = client.get("/v1/capabilities").json()
    assert body["model"] == NATLAS_MODEL_ID
    assert "python-sdk" in body["interfaces"]
    assert "use-case-studio" in body["interfaces"]
    assert set(body["use_cases"]) == {
        "chatbot",
        "translation",
        "education",
        "culture",
        "government",
        "digital_inclusion",
        "research",
        "song",
    }
    assert body["asr_models"]["yoruba"] == "NCAIR1/Yoruba-ASR"
    assert body["documentation_languages"] == ["english", "yoruba", "hausa", "igbo"]


def test_disabled_runtime_probe_fails_closed():
    r = client.post("/api/runtime/probe")
    assert r.status_code == 503


def test_disabled_runtime_fails_closed():
    r = client.post(
        "/v1/generate",
        json={
            "model": NATLAS_MODEL_ID,
            "messages": [{"role": "user", "content": "hello"}],
        },
    )
    assert r.status_code == 503


def test_readiness_is_not_green_without_direct_runtime():
    body = client.get("/api/challenge/readiness").json()
    assert body["problem_statement"] == "Developer Infrastructure"
    assert body["checks"]["direct_natlas_runtime_configured"] is False
    assert body["ready"] is False


def test_speech_capabilities_are_explicit_about_provenance():
    body = client.get("/v1/audio/capabilities").json()
    assert body["asr"]["official_natlas_components"] is True
    assert body["asr"]["languages"]["yoruba"] == "NCAIR1/Yoruba-ASR"
    assert "tts" not in body
    assert body["asr"]["official_natlas_components"] is True


def test_disabled_runtime_asr_fails_closed():
    response = client.post(
        "/v1/audio/transcriptions",
        data={"language": "yoruba"},
        files={"file": ("sample.wav", b"RIFF-test", "audio/wav")},
    )
    assert response.status_code == 503
    assert "official NCAIR ASR" in response.json()["detail"]
