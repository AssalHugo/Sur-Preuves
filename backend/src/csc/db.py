"""Gestion de la base de données PostgreSQL et de l'extension pgvector."""

from sqlalchemy import Engine, create_engine, text

from csc.config import settings


def get_engine(url: str | None = None) -> Engine:
    """Retourne une instance Engine SQLAlchemy."""
    target_url = url or settings.database_url
    return create_engine(target_url, pool_pre_ping=True)


def check_db_status(engine: Engine | None = None) -> tuple[bool, str, str | None]:
    """Vérifie l'état de la connexion à la base et la présence de pgvector.

    Retourne:
        tuple (connecté, message, version_vector)
    """
    eng = engine or get_engine()
    try:
        with eng.connect() as conn:
            # 1. Vérification de connectivité de base
            conn.execute(text("SELECT 1"))

            # 2. Vérification de l'extension vector
            result = conn.execute(
                text("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
            ).scalar()

            vector_version = str(result) if result is not None else None
            return True, "Connexion réussie", vector_version
    except Exception as exc:
        return False, f"Échec de connexion : {exc}", None


def init_vector_extension(engine: Engine | None = None) -> bool:
    """Active l'extension pgvector si elle n'est pas déjà présente."""
    eng = engine or get_engine()
    try:
        with eng.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        return True
    except Exception:
        return False
