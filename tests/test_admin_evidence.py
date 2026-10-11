import io
from fastapi.testclient import TestClient
from pypdf import PdfReader
import server.main as main
from server.store import BetaStore


def test_admin_evidence_round_trip(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "store", BetaStore(str(tmp_path / "evidence.sqlite")))
    monkeypatch.setattr(main.settings, "ednai_admin_token", "a-secure-test-token-" + "x" * 32)
    details = dict(test_date="2026-10-11", deployment="https://example.test @ abc123",
                   environment="Python 3.11 / Windows", use_case="Integrating a developer chatbot",
                   steps="Installed the SDK and called generate", expected_result="A generated answer",
                   actual_result="A valid generated answer", outcome="success", integration_minutes=12,
                   redacted_sample="POST /v1/generate -> HTTP 200", authenticity_confirmed=True)
    payload = dict(tester_identity="outside@example.com", features=["python_sdk"], rating=4,
                   useful=True, external_tester=True, consent=True, test_details=details)
    with TestClient(main.app) as client:
        assert client.get("/feedback").status_code == 200
        assert client.get("/challenge/admin").status_code == 200
        for endpoint in ("/api/admin/evidence", "/api/admin/evidence/report.pdf", "/api/admin/evidence/report.json"):
            assert client.get(endpoint).status_code == 401
        assert client.post("/api/admin/session", json={"token":"wrong"}).status_code == 401
        response = client.post("/api/admin/session", json={"token":main.settings.ednai_admin_token})
        assert response.status_code == 200
        assert "HttpOnly" in response.headers["set-cookie"] and "SameSite=strict" in response.headers["set-cookie"]
        first = client.post("/api/beta/feedback", json=payload).json()["evidence_id"]
        payload["tester_identity"] = "second@example.com"
        second = client.post("/api/beta/feedback", json=payload).json()["evidence_id"]
        data = client.get("/api/admin/evidence").json()
        assert data["validation"]["beta_target_met"] is False
        assert len(data["records"]) == 2
        assert data["records"][0]["test_details"] == details | {"request_ids":"", "evidence_links":"", "documentation_feedback":""}
        assert "outside@example.com" not in str(data)
        assert client.post(f"/api/admin/evidence/{first}/verify", headers={"Origin":"https://evil.test"}).status_code == 403
        for evidence_id in (first,second):
            assert client.post(f"/api/admin/evidence/{evidence_id}/verify").status_code == 200
        assert client.get("/api/admin/evidence").json()["validation"]["beta_target_met"] is True
        pdf = client.get("/api/admin/evidence/report.pdf")
        assert pdf.status_code == 200 and pdf.headers["content-type"] == "application/pdf"
        reader = PdfReader(io.BytesIO(pdf.content))
        text = "\n".join(p.extract_text() for p in reader.pages)
        assert "2 unique verified external testers" in text
        assert "Installed the SDK" in text and "outside@example.com" not in text
        assert "UNVERIFIED / INTERNAL" in text
        assert client.delete("/api/admin/session").status_code == 204
        assert client.get("/api/admin/evidence").status_code == 401
    reopened = BetaStore(str(tmp_path / "evidence.sqlite"))
    assert reopened.report_records()[0]["test_details"]["outcome"] == "success"


def test_pdf_paginates_long_feedback():
    from server.evidence_pdf import validation_pdf
    record = dict(id="ref", tester_hash="hash", created_at="2026-10-11", verified_at=None,
                  affiliation="Lab", role="Developer", features=["python_sdk"], rating=4, useful=True,
                  external_tester=True, verified_external=False, test_details={"actual_result":"Long feedback "*1000},
                  blocker=None, notes="End of feedback")
    data=dict(generated_at="2026-10-11", records=[record],validation=dict(unique_verified_external_beta_testers=0,
              consented_feedback_records=1,unique_external_beta_submissions=1,pending_external_submissions=1))
    reader=PdfReader(io.BytesIO(validation_pdf(data)))
    assert len(reader.pages)>4
    assert "End of feedback" in reader.pages[-1].extract_text()
