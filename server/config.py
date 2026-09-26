from functools import lru_cache
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
    cors_origins: str = "http://localhost:8000"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [x.strip() for x in self.cors_origins.split(",") if x.strip()]

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
