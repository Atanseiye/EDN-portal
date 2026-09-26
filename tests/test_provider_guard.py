import pytest

from ednai.providers import NATLAS_MODEL_ID, ProviderError, assert_natlas_model


def test_official_model_is_allowed():
    assert assert_natlas_model(NATLAS_MODEL_ID) == NATLAS_MODEL_ID


@pytest.mark.parametrize("model", ["gpt-4", "meta-llama/Llama-3-8B", "other/model", ""])
def test_general_purpose_substitution_is_rejected(model):
    with pytest.raises(ProviderError):
        assert_natlas_model(model)
