from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    app_base_url: str = "http://localhost:8000"
    admin_token: str = "change-me"
    database_path: str = "/tmp/powerrights.db"
    database_url: str = ""

    natlas_provider: str = "mock"
    natlas_model: str = "NCAIR1/N-ATLaS"
    natlas_base_url: str = "http://localhost:8001/v1"
    natlas_api_key: str = ""
    natlas_timeout_seconds: int = 90

    asr_provider: str = "mock"
    hf_token: str = ""
    max_audio_mb: int = 12

    cors_origins: str = "http://localhost:8000"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [x.strip() for x in self.cors_origins.split(",") if x.strip()]

    @property
    def challenge_model_ready(self) -> bool:
        return self.natlas_provider.lower() not in {"mock", "disabled", ""}

    @property
    def challenge_asr_ready(self) -> bool:
        return self.asr_provider.lower() not in {"mock", "disabled", ""}

    @property
    def persistent_validation_ready(self) -> bool:
        return bool(self.database_url)


@lru_cache
def get_settings() -> Settings:
    return Settings()
