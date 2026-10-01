import pytest

from server.config import Settings
from server.security import validate_production_settings


def test_production_rejects_unsafe_defaults():
    settings = Settings(
        app_env="production",
        ednai_provider="gradio_space",
        ednai_gradio_space_id="owner/runtime",
        hf_token="",
        ednai_database_url="",
        ednai_admin_token="change-me",
        trusted_hosts="*",
        cors_origins="*",
        ednai_demo_account_enabled=True,
        ednai_allow_public_demo_account=False,
        ednai_pricing_mode="demo",
        ednai_require_exact_usage=False,
    )
    with pytest.raises(RuntimeError) as exc:
        validate_production_settings(settings)
    message = str(exc.value)
    assert "EDNAI_DATABASE_URL" in message
    assert "EDNAI_ADMIN_TOKEN" in message
    assert "HF_TOKEN" in message
    assert "Wildcard CORS" in message
    assert "Public demo account" in message
    assert "EDNAI_PRICING_MODE" in message
    assert "EDNAI_REQUIRE_EXACT_USAGE" in message


def test_production_accepts_explicit_safe_contract():
    settings = Settings(
        app_env="production",
        ednai_provider="gradio_space",
        ednai_model="NCAIR1/N-ATLaS",
        ednai_gradio_space_id="owner/runtime",
        hf_token="hf_example",
        ednai_database_url="postgresql://user:pass@db/ednai",
        ednai_admin_token="x" * 48,
        trusted_hosts="ednai.example.com",
        cors_origins="https://ednai.example.com",
        ednai_demo_account_enabled=False,
        ednai_pricing_mode="production",
        ednai_require_exact_usage=True,
    )
    validate_production_settings(settings)
