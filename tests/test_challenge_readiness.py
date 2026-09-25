import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ["NATLAS_PROVIDER"] = "grounded_rules"
os.environ["ASR_PROVIDER"] = "disabled"
os.environ["APP_ENV"] = "test"
os.environ["DATABASE_PATH"] = "/tmp/powerrights-readiness-test.db"
Path(os.environ["DATABASE_PATH"]).unlink(missing_ok=True)

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_challenge_page_exists():
    r = client.get("/challenge")
    assert r.status_code == 200
    assert "Challenge" in r.text


def test_fallback_build_never_reports_challenge_ready():
    r = client.get("/api/v1/challenge/readiness")
    assert r.status_code == 200
    body = r.json()
    assert body["ready"] is False
    assert body["checks"]["working_technical_artifact"] is True
    assert body["checks"]["official_natlas_llm_configured"] is False
    assert body["checks"]["official_natlas_asr_configured"] is False
    assert body["checks"]["minimum_50_documented_real_voice_interactions"] is False
    assert body["validation"]["competition_eligible_voice_interactions"] == 0
    assert body["validation"]["validation_target"] == 50


def test_health_exposes_real_validation_gate():
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["challenge_ready"] is False
    assert body["validation_target"] == 50
