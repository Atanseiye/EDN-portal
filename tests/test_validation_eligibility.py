import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import Settings
from app.services.validation import ValidationStore


def make_store(tmp_path, **overrides):
    values = {
        "app_env": "test",
        "database_path": str(tmp_path / "validation.db"),
        "natlas_provider": "grounded_rules",
        "asr_provider": "disabled",
    }
    values.update(overrides)
    settings = Settings(**values)
    return ValidationStore(settings)


def test_grounded_rules_never_count_as_challenge_voice(tmp_path):
    store = make_store(tmp_path)
    store.add_interaction(
        session_id="user-1",
        language="yoruba",
        issue_type="metering",
        state="Lagos",
        disco="Ikeja Electric",
        channel="voice",
        asr_provider="disabled",
        validation_consent=True,
    )
    stats = store.stats()
    assert stats["competition_eligible_voice_interactions"] == 0
    assert stats["remaining_to_target"] == 50


def test_real_model_configuration_requires_consent(tmp_path):
    store = make_store(
        tmp_path,
        natlas_provider="gradio_space",
        natlas_space_id="user/natlas",
        asr_provider="gradio_space",
        asr_space_id="user/asr",
    )
    store.add_interaction(
        session_id="user-1",
        language="english",
        issue_type="billing",
        state="Lagos",
        disco="Ikeja Electric",
        channel="voice",
        asr_provider="gradio_space",
        validation_consent=False,
    )
    assert store.stats()["competition_eligible_voice_interactions"] == 0


def test_real_consent_voice_path_counts_exactly_once(tmp_path):
    store = make_store(
        tmp_path,
        natlas_provider="gradio_space",
        natlas_space_id="user/natlas",
        asr_provider="gradio_space",
        asr_space_id="user/asr",
    )
    store.add_interaction(
        session_id="external-user-1",
        language="igbo",
        issue_type="billing",
        state="Anambra",
        disco="EEDC",
        channel="voice",
        asr_provider="gradio_space",
        validation_consent=True,
    )
    stats = store.stats()
    assert stats["competition_eligible_voice_interactions"] == 1
    assert stats["unique_validation_sessions"] == 1
    assert stats["language_counts"]["igbo"] == 1
    assert stats["remaining_to_target"] == 49
