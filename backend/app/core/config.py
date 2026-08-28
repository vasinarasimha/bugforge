from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "BugForge API"
    environment: str = "development"
    database_url: str
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    cors_origins: str = Field(default="http://localhost:5173,http://127.0.0.1:5173")
    groq_api_key: str = ""

    # Semantic similarity thresholds (cosine similarity, 0-1)
    similarity_threshold: float = 0.60
    duplicate_threshold: float = 0.85
    similar_defects_limit: int = 10

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
