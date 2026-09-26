import pytest

from ednai.providers import NATLAS_MODEL_ID, ProviderError, assert_natlas_model


def test_official_model_is_allowed():
    assert assert_natlas_model(NATLAS_MODEL_ID) == NATLAS_MODEL_ID


@pytest.mark.parametrize("model", ["gpt-4", "meta-llama/Llama-3-8B", "other/model", ""])
def test_general_purpose_substitution_is_rejected(model):
    with pytest.raises(ProviderError):
        assert_natlas_model(model)


def test_gradio_public_space_client_does_not_forward_hf_token(monkeypatch):
    import json
    import sys
    import types

    from ednai.models import Message
    from ednai.providers import GradioSpaceProvider

    seen = {}

    class FakeClient:
        def __init__(self, *args, **kwargs):
            seen["args"] = args
            seen["kwargs"] = kwargs

        def predict(self, *args, **kwargs):
            seen["predict_args"] = args
            seen["predict_kwargs"] = kwargs
            return json.dumps({
                "text": "EDNAI_OK",
                "model": NATLAS_MODEL_ID,
                "provider": "ednai_zerogpu",
            })

    monkeypatch.setitem(
        sys.modules,
        "gradio_client",
        types.SimpleNamespace(Client=FakeClient),
    )

    provider = GradioSpaceProvider(
        "KoladeOdunope/ednai-natlas-runtime",
        hf_token="must-not-be-forwarded",
    )
    result = provider.generate(
        [Message(role="user", content="Reply EDNAI_OK")],
        temperature=0,
        max_tokens=16,
    )

    assert seen["args"] == ("KoladeOdunope/ednai-natlas-runtime",)
    assert seen["kwargs"] == {}
    assert seen["predict_kwargs"]["api_name"] == "/generate"
    assert result.model == NATLAS_MODEL_ID


def test_gradio_quota_error_is_structured(monkeypatch):
    import sys
    import types

    from ednai.models import Message
    from ednai.providers import GradioSpaceProvider, ProviderQuotaError

    class QuotaClient:
        def __init__(self, *args, **kwargs):
            pass

        def predict(self, *args, **kwargs):
            raise RuntimeError(
                "You have exceeded your ZeroGPU quota "
                "(180s requested vs. 175s left). Try again in 23:55:13."
            )

    monkeypatch.setitem(
        sys.modules,
        "gradio_client",
        types.SimpleNamespace(Client=QuotaClient),
    )

    provider = GradioSpaceProvider("KoladeOdunope/ednai-natlas-runtime")

    with pytest.raises(ProviderQuotaError) as caught:
        provider.generate(
            [Message(role="user", content="hello")],
            temperature=0,
            max_tokens=16,
        )

    assert caught.value.retry_after_seconds == 86113
    assert "temporarily exhausted" in str(caught.value)
