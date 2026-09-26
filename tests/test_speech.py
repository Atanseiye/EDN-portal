import json
import sys
import types

import pytest

from ednai.providers import (
    GradioSpaceProvider,
    NATLAS_ASR_MODELS,
    ProviderError,
)
from ednai.speech import asr_model_for, normalize_speech_language


def test_speech_language_aliases_resolve_to_official_ncair_models():
    assert normalize_speech_language("yo") == "yoruba"
    assert normalize_speech_language("HAU") == "hausa"
    assert normalize_speech_language("ibo") == "igbo"
    assert normalize_speech_language("en-NG") == "english"
    assert asr_model_for("yoruba") == "NCAIR1/Yoruba-ASR"
    assert asr_model_for("english") == "NCAIR1/NigerianAccentedEnglish"


def test_unsupported_speech_language_fails_closed():
    with pytest.raises(ValueError):
        asr_model_for("french")


def test_gradio_asr_requires_exact_model_provenance(monkeypatch, tmp_path):
    audio = tmp_path / "sample.wav"
    audio.write_bytes(b"RIFF-test")
    seen = {}

    class FakeClient:
        def __init__(self, *args, **kwargs):
            seen["client"] = (args, kwargs)

        def predict(self, *args, **kwargs):
            seen["predict"] = (args, kwargs)
            return json.dumps({
                "text": "Bawo ni",
                "model": NATLAS_ASR_MODELS["yoruba"],
                "language": "yoruba",
                "provider": "ednai_zerogpu_asr",
            })

    monkeypatch.setitem(
        sys.modules,
        "gradio_client",
        types.SimpleNamespace(
            Client=FakeClient,
            handle_file=lambda path: {"path": path},
        ),
    )

    provider = GradioSpaceProvider("owner/runtime")
    result = provider.transcribe(audio, "yoruba")

    assert result.text == "Bawo ni"
    assert result.model == "NCAIR1/Yoruba-ASR"
    assert result.language == "yoruba"
    assert seen["predict"][1]["api_name"] == "/transcribe"


def test_gradio_asr_rejects_substituted_model(monkeypatch, tmp_path):
    audio = tmp_path / "sample.wav"
    audio.write_bytes(b"RIFF-test")

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def predict(self, *args, **kwargs):
            return json.dumps({
                "text": "hello",
                "model": "someone/other-asr",
                "language": "english",
            })

    monkeypatch.setitem(
        sys.modules,
        "gradio_client",
        types.SimpleNamespace(
            Client=FakeClient,
            handle_file=lambda path: path,
        ),
    )

    with pytest.raises(ProviderError, match="provenance"):
        GradioSpaceProvider("owner/runtime").transcribe(audio, "english")
