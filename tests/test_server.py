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
    assert "Build with" in client.get("/").text
    assert client.head("/").status_code == 200
    assert client.get("/guide/en").status_code == 200
    assert client.get("/guide/yo").status_code == 200
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
    assert body["asr_models"]["yoruba"] == "NCAIR1/Yoruba-ASR"


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
