"""Configuration application pour csc."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_ROOT_ENV_FILE = _PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    """Paramètres globaux de l'application chargés depuis l'environnement ou .env."""

    model_config = SettingsConfigDict(
        env_file=(_ROOT_ENV_FILE, ".env"),
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
    models_config_path: Path = Field(default=Path("config/models.yaml"))
    pricing_config_path: Path = Field(default=Path("config/pricing.yaml"))
    prompts_dir: Path = Field(default=Path("prompts"))
    llm_cache_dir: Path = Field(default=Path("var/cache/llm"))
    models_cache_dir: Path = Field(default=Path("var/models"))
    llm_debug: bool = False

    # Connecteurs
    openalex_api_key: str | None = None
    openalex_base_url: str = "https://api.openalex.org"
    openalex_email: str | None = None
    openalex_cache_dir: Path = Field(default=Path("var/cache/openalex"))
    openalex_daily_budget_credits: float = 100000.0
    openalex_budget_threshold_pct: float = 0.90
    hal_base_url: str = "https://api.archives-ouvertes.fr/search"
    hal_cache_dir: Path = Field(default=Path("var/cache/hal"))
    nosparlementaires_api_key: str | None = None

    # Sauvegardes
    backup_dir: Path = Field(default=Path("./var/backups"))

    # Back-office de relecture
    review_port: int = 8000
    review_auth: str = "local"


settings = Settings()
