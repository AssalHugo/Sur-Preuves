"""Gestion des moteurs SQLAlchemy, des sessions et de l'extension pgvector."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from csc.config import settings


def get_engine(url: str | None = None) -> Engine:
    """Retourne une instance Engine SQLAlchemy configurée."""
    target_url = url or settings.database_url
    return create_engine(target_url, pool_pre_ping=True)


def create_session_factory(engine: Engine | None = None) -> sessionmaker[Session]:
    """Crée une fabrique de sessions liée au moteur spécifié."""
    eng = engine or get_engine()
    return sessionmaker(bind=eng, autoflush=False, autocommit=False)


@contextmanager
def get_session(engine: Engine | None = None) -> Generator[Session, None, None]:
    """Gestionnaire de contexte fournissant une session transactionnelle SQLAlchemy."""
    factory = create_session_factory(engine)
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


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
