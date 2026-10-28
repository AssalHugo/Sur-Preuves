"""Tests d'intégration des migrations Alembic sur la base de données."""

from pathlib import Path

from alembic.config import Config as AlembicConfig
from sqlalchemy import inspect

from alembic import command as alembic_command
from csc.db.session import get_engine


def _get_alembic_config() -> AlembicConfig:
    candidates = [
        Path("backend/alembic.ini"),
        Path("alembic.ini"),
    ]
    ini_file = next(p for p in candidates if p.exists())
    return AlembicConfig(str(ini_file))


def test_alembic_migration_head_and_table_inspection() -> None:
    """Vérifie que les migrations Alembic s'appliquent et créent toutes les tables."""
    cfg = _get_alembic_config()
    engine = get_engine()

    # 1. Application des migrations
    alembic_command.upgrade(cfg, "head")

    # 2. Inspection des tables créées
    inspector = inspect(engine)
    db_tables = set(inspector.get_table_names())

    expected_tables = {
        "candidates",
        "parties",
        "parliamentary_groups",
        "source_documents",
        "document_chunks",
        "proposals",
        "claims",
        "scholarly_works",
        "evidence_queries",
        "evidence_items",
        "assessments",
        "reviewers",
        "reviews",
        "verification_reports",
        "changelog_entries",
        "scrutins",
        "votes",
        "amendments",
        "llm_calls",
        "rectification_requests",
    }
    assert expected_tables.issubset(db_tables), f"Tables manquantes : {expected_tables - db_tables}"


def test_alembic_downgrade_and_reupgrade_cycle() -> None:
    """Vérifie le cycle complet upgrade -> downgrade base -> upgrade head."""
    cfg = _get_alembic_config()

    # Downgrade vers la base
    alembic_command.downgrade(cfg, "base")

    engine = get_engine()
    inspector = inspect(engine)
    db_tables_after_downgrade = set(inspector.get_table_names())
    assert "assessments" not in db_tables_after_downgrade
    assert "candidates" not in db_tables_after_downgrade

    # Re-upgrade vers head
    alembic_command.upgrade(cfg, "head")
    inspector_re = inspect(engine)
    db_tables_after_reupgrade = set(inspector_re.get_table_names())
    assert "assessments" in db_tables_after_reupgrade
    assert "candidates" in db_tables_after_reupgrade
