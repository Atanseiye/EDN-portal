from fastapi.testclient import TestClient

import server.main as main
from server.store import BetaStore


def test_feedback_response_updates_count_before_review_and_on_reload(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "store", BetaStore(str(tmp_path / "feedback.sqlite3")))
    with TestClient(main.app) as client:
        feedback = {
            "tester_identity": "external@example.com", "features": ["playground"],
            "rating": 4, "useful": True, "external_tester": True, "consent": True,
        }
        response = client.post("/api/beta/feedback", json=feedback)
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "pending_review"
        assert body["validation"]["unique_external_beta_submissions"] == 1
        assert body["validation"]["unique_verified_external_beta_testers"] == 0
        assert body["validation"]["beta_target_met"] is False

        feedback["tester_identity"] = "  EXTERNAL@example.com "
        duplicate = client.post("/api/beta/feedback", json=feedback).json()
        assert duplicate["validation"]["unique_external_beta_submissions"] == 1

        feedback["tester_identity"] = "second@example.com"
        second = client.post("/api/beta/feedback", json=feedback).json()
        assert second["validation"]["unique_external_beta_submissions"] == 2
        reload = client.get("/api/challenge/readiness").json()
        assert reload["validation"]["unique_external_beta_submissions"] == 2
        assert reload["checks"]["minimum_two_external_beta_testers"] is False


def test_no_consent_or_internal_feedback_cannot_increase_external_count(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "store", BetaStore(str(tmp_path / "feedback.sqlite3")))
    with TestClient(main.app) as client:
        feedback = {
            "tester_identity": "team@example.com", "features": ["playground"],
            "rating": 4, "useful": True, "external_tester": False, "consent": True,
        }
        internal = client.post("/api/beta/feedback", json=feedback).json()
        assert internal["validation"]["unique_external_beta_submissions"] == 0
        feedback.update(external_tester=True, consent=False)
        assert client.post("/api/beta/feedback", json=feedback).status_code == 400
        assert main.store.stats()["unique_external_beta_submissions"] == 0
