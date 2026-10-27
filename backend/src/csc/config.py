"""Configuration application pour csc."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Paramètres globaux de l'application chargés depuis l'environnement ou .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Base de données
    postgres_user: str = "csc"
    postgres_password: str = "csc"
    postgres_db: str = "csc"
    postgres_port: int = 5432
    database_url: str = Field(
        default="postgresql+psycopg://csc:csc@127.0.0.1:5432/csc",
        description="URL de connexion SQLAlchemy à PostgreSQL",
    )

    # LLM
    gemini_api_key: str | None = None
    gemini_free_api_key: str | None = None
    llm_monthly_cap_usd: float = 9.0

    # Connecteurs
    openalex_api_key: str | None = None
    nosparlementaires_api_key: str | None = None

    # Sauvegardes
    backup_dir: Path = Field(default=Path("./var/backups"))

    # Back-office de relecture
    review_port: int = 8000
    review_auth: str = "local"


settings = Settings()
