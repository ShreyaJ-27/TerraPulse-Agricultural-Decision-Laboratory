import os
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    database_url: str = "postgresql+psycopg://terrapulse:terrapulse@localhost:5433/terrapulse"

    @property
    def sqlalchemy_database_url(self) -> str:
        for prefix in ("postgres://", "postgresql://"):
            if self.database_url.startswith(prefix):
                return "postgresql+psycopg://" + self.database_url[len(prefix):]
        return self.database_url
    open_meteo_forecast_url: str = "https://api.open-meteo.com/v1/forecast"
    open_meteo_ensemble_url: str = "https://ensemble-api.open-meteo.com/v1/ensemble"
    open_meteo_timeout_seconds: float = 10.0
    soilgrids_api_url: str = "https://rest.isric.org/soilgrids/v2.0/properties/query"
    soilgrids_wcs_url: str = "https://maps.isric.org/mapserv"
    soilgrids_timeout_seconds: float = 10.0
    gemini_api_key: str | None = None
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    @property
    def require_workspace_key(self) -> bool:
        return self.app_env == "production" or os.environ.get("VERCEL_ENV") in {"preview", "production"}

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)


@lru_cache
def get_settings() -> Settings:
    return Settings()
