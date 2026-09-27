import uuid

from fastapi.testclient import TestClient

import server.main as main
from ednai.models import Generation
from ednai.providers import NATLAS_MODEL_ID

client = TestClient(main.app)


def _login_demo():
    response = client.post(
        "/api/developer/login",
        json={"email": "demo@edn.com", "password": "12345"},
    )
    assert response.status_code == 200
    return response.json()


def test_demo_account_is_seeded_with_credit():
    body = _login_demo()
    assert body["account"]["email"] == "demo@edn.com"
    assert body["account"]["is_demo"] is True
    assert body["account"]["balance_microusd"] > 0


def test_api_key_secret_is_returned_once_and_list_only_has_prefix():
    _login_demo()
    created = client.post(
        "/api/developer/keys",
        json={
            "name": "test key",
            "scopes": ["inference.generate"],
        },
    )
    assert created.status_code == 200
    secret = created.json()["key"]
    assert secret.startswith("ednai_live_")

    me = client.get("/api/developer/me")
    assert me.status_code == 200
    matching = [x for x in me.json()["api_keys"] if x["id"] == created.json()["id"]][0]
    assert "key" not in matching
    assert matching["prefix"] == secret[:18]


def test_scoped_api_key_rejects_ungranted_feature():
    _login_demo()
    created = client.post(
        "/api/developer/keys",
        json={"name": "generate only", "scopes": ["inference.generate"]},
    ).json()

    response = client.post(
        "/v1/use-cases/chatbot",
        headers={"Authorization": f"Bearer {created['key']}"},
        json={
            "language": "english",
            "inputs": {"message": "Hello"},
        },
    )
    assert response.status_code == 403
    assert "usecases.run" in response.json()["detail"]


def test_exact_provider_tokens_are_charged_and_ledgered(monkeypatch):
    class FakeProvider:
        def generate(self, messages, *, model, temperature, max_tokens, json_mode):
            return Generation(
                text="API means application programming interface.",
                model=NATLAS_MODEL_ID,
                provider="test-natlas",
                usage={
                    "prompt_tokens": 100,
                    "completion_tokens": 25,
                    "total_tokens": 125,
                    "measurement": "tokenizer_exact",
                },
            )

    monkeypatch.setattr(main, "provider", FakeProvider())
    _login_demo()
    created = client.post(
        "/api/developer/keys",
        json={"name": "metered", "scopes": ["inference.generate"]},
    ).json()

    before = client.get("/api/developer/me").json()["account"]["balance_microusd"]
    response = client.post(
        "/v1/generate",
        headers={"Authorization": f"Bearer {created['key']}"},
        json={
            "model": NATLAS_MODEL_ID,
            "messages": [{"role": "user", "content": "Explain API."}],
            "temperature": 0,
            "max_tokens": 64,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["usage"]["prompt_tokens"] == 100
    assert body["usage"]["completion_tokens"] == 25
    assert body["usage"]["measurement"] == "provider_exact"
    assert body["usage"]["billing"]["cost_usd"] > 0

    after = client.get("/api/developer/me").json()["account"]["balance_microusd"]
    assert after < before


def test_new_non_demo_account_has_no_credit_and_cannot_infer(monkeypatch):
    email = f"developer-{uuid.uuid4().hex[:8]}@example.com"
    registered = client.post(
        "/api/developer/register",
        json={
            "email": email,
            "password": "a-secure-password",
            "display_name": "Test Developer",
        },
    )
    assert registered.status_code == 200

    key = client.post(
        "/api/developer/keys",
        json={"name": "empty-wallet", "scopes": ["inference.generate"]},
    ).json()["key"]

    response = client.post(
        "/v1/generate",
        headers={"Authorization": f"Bearer {key}"},
        json={
            "model": NATLAS_MODEL_ID,
            "messages": [{"role": "user", "content": "hello"}],
            "max_tokens": 64,
        },
    )
    assert response.status_code == 402
    assert response.json()["detail"]["error"] == "insufficient_credit"
