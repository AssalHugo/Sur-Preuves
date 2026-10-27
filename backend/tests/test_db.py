"""Tests unitaires pour les fonctions de base de données."""

from unittest.mock import MagicMock

from sqlalchemy import Engine
from sqlalchemy.exc import OperationalError

from csc.db import check_db_status, init_vector_extension


def test_check_db_status_success() -> None:
    """Vérifie check_db_status avec un moteur mocké renvoyant la version vector."""
    mock_engine = MagicMock(spec=Engine)
    mock_conn = MagicMock()
    mock_engine.connect.return_value.__enter__.return_value = mock_conn

    # Premier execute: SELECT 1
    # Second execute: SELECT extversion FROM pg_extension WHERE extname = 'vector'
    mock_result = MagicMock()
    mock_result.scalar.return_value = "0.8.0"
    mock_conn.execute.side_effect = [MagicMock(), mock_result]

    connected, msg, version = check_db_status(mock_engine)
    assert connected is True
    assert "réussie" in msg
    assert version == "0.8.0"


def test_check_db_status_without_vector() -> None:
    """Vérifie check_db_status quand l'extension n'est pas installée."""
    mock_engine = MagicMock(spec=Engine)
    mock_conn = MagicMock()
    mock_engine.connect.return_value.__enter__.return_value = mock_conn

    mock_result = MagicMock()
    mock_result.scalar.return_value = None
    mock_conn.execute.side_effect = [MagicMock(), mock_result]

    connected, msg, version = check_db_status(mock_engine)
    assert connected is True
    assert version is None


def test_check_db_status_error() -> None:
    """Vérifie le traitement d'erreur de connexion."""
    mock_engine = MagicMock(spec=Engine)
    mock_engine.connect.side_effect = OperationalError(
        "connection refused", params=None, orig=Exception()
    )

    connected, msg, version = check_db_status(mock_engine)
    assert connected is False
    assert "Échec de connexion" in msg
    assert version is None


def test_init_vector_extension_success() -> None:
    """Vérifie init_vector_extension avec succès."""
    mock_engine = MagicMock(spec=Engine)
    mock_conn = MagicMock()
    mock_engine.begin.return_value.__enter__.return_value = mock_conn

    assert init_vector_extension(mock_engine) is True
    mock_conn.execute.assert_called_once()


def test_init_vector_extension_error() -> None:
    """Vérifie init_vector_extension en cas d'erreur SQL."""
    mock_engine = MagicMock(spec=Engine)
    mock_engine.begin.side_effect = Exception("permission denied")

    assert init_vector_extension(mock_engine) is False
