import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ["NATLAS_PROVIDER"] = "grounded_rules"
os.environ["ASR_PROVIDER"] = "disabled"
os.environ["DATABASE_PATH"] = "/tmp/powerrights-dynamic-test.db"
Path(os.environ["DATABASE_PATH"]).unlink(missing_ok=True)

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def ask(message: str, state: str = "Lagos", disco: str = "Ikeja Electric"):
    response = client.post(
        "/api/v1/advice",
        json={
            "message": message,
            "language": "english",
            "state": state,
            "disco": disco,
        },
    )
    assert response.status_code == 200
    return response.json()


def test_billing_and_metering_are_not_static_duplicates():
    billing = ask("My estimated bill is much higher than normal even though I use less electricity.")
    metering = ask("My prepaid meter is faulty and the DisCo removed it without replacing it.")

    assert billing["issue_type"] == "billing"
    assert metering["issue_type"] == "metering"
    assert billing["summary"] != metering["summary"]
    assert billing["next_steps"] != metering["next_steps"]
    assert billing["model"] == "verified-grounded-fallback"
    assert metering["model"] == "verified-grounded-fallback"


def test_non_electricity_prompt_is_not_given_fake_rights():
    result = ask("Can you speak Igbo?", state="Anambra", disco="EEDC")

    assert result["issue_type"] == "other"
    assert "does not look like an electricity complaint" in result["summary"]
    assert result["rights"] == []
    assert any("Describe the electricity problem" in step for step in result["next_steps"])


def test_tariff_band_response_is_specific():
    result = ask("I am being charged Band A but we do not get the promised hours of supply.")
    assert result["issue_type"] == "tariff_band"
    assert "tariff/service-band complaint" in result["summary"]
    assert any("service band" in step.lower() for step in result["next_steps"])
