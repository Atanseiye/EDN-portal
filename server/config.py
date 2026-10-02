from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from ednai.providers import NATLAS_MODEL_ID


class Settings(BaseSettings):
    app_env: str = "development"
    ednai_provider: str = "disabled"
    ednai_model: str = NATLAS_MODEL_ID
    ednai_upstream_base_url: str = ""
    ednai_upstream_api_key: str = ""
    ednai_gradio_space_id: str = ""
    hf_token: str = ""
    ednai_admin_token: str = "change-me"
    ednai_database_path: str = "/tmp/ednai.sqlite3"
    ednai_database_url: str = ""
    ednai_beta_recovery_json: str = Field(default="", repr=False)
    ednai_auth_enabled: bool = True
    ednai_demo_account_enabled: bool = True
    ednai_allow_public_demo_account: bool = False
    ednai_demo_email: str = "demo@edn.com"
    ednai_demo_password: str = "12345"
    ednai_demo_credit_usd: float = 10.0
    ednai_input_usd_per_1m_tokens: float = 0.50
    ednai_output_usd_per_1m_tokens: float = 1.50
    ednai_pricing_mode: str = "demo"
    ednai_require_exact_usage: bool = True
    ednai_session_hours: int = 24
    ednai_max_api_keys_per_account: int = 10
    ednai_login_rate_limit_per_minute: int = 10
    ednai_api_rate_limit_per_minute: int = 60
    ednai_demo_request_rate_limit_per_hour: int = 5
    ednai_smtp_host: str = ""
    ednai_smtp_port: int = 587
    ednai_smtp_username: str = ""
    ednai_smtp_password: str = ""
    ednai_smtp_from: str = ""
    trusted_hosts: str = "*"
    cors_origins: str = "http://localhost:8000"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [x.strip() for x in self.cors_origins.split(",") if x.strip()]

    @property
    def trusted_host_list(self) -> list[str]:
        return [x.strip() for x in self.trusted_hosts.split(",") if x.strip()]

    @property
    def allowed_origin_set(self) -> set[str]:
        return set(self.cors_origin_list)

    @property
    def qualifying_provider(self) -> bool:
        p = self.ednai_provider.lower()
        if self.ednai_model != NATLAS_MODEL_ID:
            return False
        if p == "local":
            return True
        if p == "openai_compatible":
            return bool(self.ednai_upstream_base_url)
        if p == "gradio_space":
            return bool(self.ednai_gradio_space_id)
        return False


@lru_cache
def get_settings() -> Settings:
    return Settings()
