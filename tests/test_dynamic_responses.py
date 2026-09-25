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


def test_language_capability_question_is_answered_directly():
    result = ask("Can you speak Igbo?", state="Anambra", disco="EEDC")

    assert result["issue_type"] == "other"
    assert "Igbo" in result["summary"]
    assert "not active" in result["summary"]
    assert result["rights"] == []


def test_escalation_question_names_state_regulator():
    result = ask(
        "Who should I escalate my unresolved electricity complaint to in Anambra?",
        state="Anambra",
        disco="EEDC",
    )
    assert "Anambra State Electricity Regulatory Commission" in result["summary"]
    assert "EEDC" in result["summary"]


def test_complaint_timeline_question_states_15_working_days():
    result = ask("How long does the DisCo have to resolve my written electricity complaint?")
    assert "15 working days" in result["summary"]


def test_meter_replacement_responsibility_is_answered():
    result = ask("Who is responsible for replacing my faulty prepaid meter?")
    assert "responsible" in result["summary"].lower()
    assert "Ikeja Electric" in result["summary"]


def test_estimated_billing_after_meter_removal_is_answered():
    result = ask(
        "Can they give me estimated bills after removing my faulty meter and not replacing it?"
    )
    assert "should not" in result["summary"].lower()
    assert "three months" in result["summary"].lower()


def test_compound_question_answers_multiple_parts():
    result = ask(
        "My faulty meter was removed and I am now on estimated billing. "
        "What are my rights, what should I do, and who do I escalate to if Ikeja Electric does not resolve it?"
    )
    summary = result["summary"].lower()
    assert "estimated" in summary
    assert "first step" in summary
    assert "lagos state electricity regulatory commission" in summary


def test_tariff_band_response_is_specific():
    result = ask("I am being charged Band A but we do not get the promised hours of supply.")
    assert result["issue_type"] == "tariff_band"
    assert "challenge" in result["summary"].lower()
    assert "service band" in result["summary"].lower()


def test_yoruba_text_overrides_stale_english_selector_and_returns_yoruba():
    message = (
        "Láti ìgbà náà ni wọ́n ti ń fún mi ní owó ina àfọwọ́kọ tí ó ga ju ohun tí mo máa ń san lọ. "
        "Mo ti fi ẹ̀sùn náà ránṣẹ́ sí wọn ṣùgbọ́n wọn kò ṣe ohunkóhun. "
        "Ṣé wọ́n lè máa ṣe billing àfọwọ́kọ fún mi báyìí? "
        "Kí ni ẹ̀tọ́ mi, kí ni mo yẹ kí n ṣe báyìí, àti ta ni mo yẹ kí n fi ẹ̀sùn náà lé lọ́wọ́ tí wọn kò bá yanju rẹ̀?"
    )
    result = ask(message, state="Anambra", disco="EEDC")

    assert result["language"] == "yoruba"
    assert "Ìgbésẹ̀" in result["summary"] or "ẹ̀sùn" in result["summary"]
    assert any("oníbàárà" in right.lower() or "ẹ̀sùn" in right.lower() for right in result["rights"])
    assert any("kí o" in step.lower() or "ẹ̀sùn" in step.lower() for step in result["next_steps"])
    assert "ẹ̀sùn" in result["escalation"]["note"].lower()


def test_yoruba_natural_metering_without_english_keywords_is_classified():
    result = ask(
        "Mita mi bàjẹ́, wọ́n yọ ọ́ kúrò, wọn kò sì rọ́pò rẹ̀. Kí ni mo yẹ kí n ṣe?",
        state="Anambra",
        disco="EEDC",
    )
    assert result["language"] == "yoruba"
    assert result["issue_type"] == "metering"
    assert "Ìgbésẹ̀" in result["summary"] or "mita" in result["summary"].lower()


def test_hausa_text_language_is_preserved():
    result = ask(
        "Mita na ya lalace kuma kamfanin wuta ya cire shi. Me zan yi kuma menene hakkina?",
        state="Kaduna",
        disco="Kaduna Electric",
    )
    assert result["language"] == "hausa"
    assert any(word in result["summary"].lower() for word in ("mataki", "mita", "korafi", "hakki"))


def test_igbo_text_language_is_preserved():
    result = ask(
        "Mita m mebiri ma ha wepụrụ mita ahụ. Gịnị ka m mee, kedụ ikike m?",
        state="Anambra",
        disco="EEDC",
    )
    assert result["language"] == "igbo"
    assert any(word in result["summary"].lower() for word in ("nzọụkwụ", "mita", "mkpesa", "ikike"))
