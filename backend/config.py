from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    environment: str = "development"
    mongodb_uri: str = "mongodb://localhost:27017/?replicaSet=rs0"
    database: str = "kileger"
    session_cookie: str = "kileger_session"
    session_days: int = 7
    cookie_secure: bool = False
    allowed_origins: str = "http://localhost:8000,http://127.0.0.1:8000"
    allowed_hosts: str = "localhost,127.0.0.1"
    rate_limit: int = 10
    rate_window_seconds: int = 60

    model_config = SettingsConfigDict(env_prefix="KILEDGER_", env_file=".env", extra="ignore")

    @property
    def origins(self) -> list[str]:
        return [item.strip() for item in self.allowed_origins.split(",") if item.strip()]

    @property
    def hosts(self) -> list[str]:
        return [item.strip() for item in self.allowed_hosts.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
