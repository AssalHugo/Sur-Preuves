"""Tests unitaires pour la CLI Typer csc."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from csc.cli import app


def test_cli_help(runner: CliRunner) -> None:
    """Vérifie que la commande csc --help affiche tous les groupes requis."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    expected_groups = [
        "db",
        "llm",
        "openalex",
        "hal",
        "s2",
        "parlement",
        "ingest",
        "embed",
        "extract",
        "evidence",
        "synth",
        "verify",
        "legislature",
        "review",
        "publish",
        "backup",
    ]
    for group in expected_groups:
        assert group in result.stdout


def test_poc_placeholders(runner: CliRunner) -> None:
    """Vérifie le comportement des étapes POC non encore implémentées."""
    commands = [
        (["ingest"], "[POC] ingest : étape non implémentée (Lot L08)"),
        (["extract"], "[POC] extract : étape non implémentée (Lot L09)"),
        (["evidence"], "[POC] evidence : étape non implémentée (Lot L10)"),
        (["synth"], "[POC] synth : étape non implémentée (Lot L11)"),
        (["verify"], "[POC] verify : étape non implémentée (Lot L12)"),
        (
            ["publish", "bundle", "--include-drafts", "--poc"],
            "[POC] publish bundle : étape non implémentée (Lot L14)",
        ),
        (["review", "serve"], "[POC] Service de relecture non implémenté (Lot L14)"),
    ]
    for args, expected_output in commands:
        res = runner.invoke(app, args)
        assert res.exit_code == 0
        assert expected_output in res.stdout


def test_db_status_success(runner: CliRunner) -> None:
    """Vérifie db status en cas de succès avec extension active."""
    with patch("csc.cli.check_db_status", return_value=(True, "Connexion réussie", "0.8.0")):
        result = runner.invoke(app, ["db", "status"])
        assert result.exit_code == 0
        assert "Connecté avec succès" in result.stdout
        assert "v0.8.0" in result.stdout


def test_db_status_without_extension(runner: CliRunner) -> None:
    """Vérifie db status quand pgvector est absent."""
    with patch("csc.cli.check_db_status", return_value=(True, "Connexion réussie", None)):
        result = runner.invoke(app, ["db", "status"])
        assert result.exit_code == 0
        assert "Extension pgvector absente" in result.stdout


def test_db_status_failure(runner: CliRunner) -> None:
    """Vérifie db status en cas d'échec de connexion."""
    with patch("csc.cli.check_db_status", return_value=(False, "Connection refused", None)):
        result = runner.invoke(app, ["db", "status"])
        assert result.exit_code == 1
        assert "Échec de connexion" in result.stdout


def test_db_init_success(runner: CliRunner) -> None:
    """Vérifie db init en cas de succès."""
    with patch("csc.cli.init_vector_extension", return_value=True):
        result = runner.invoke(app, ["db", "init"])
        assert result.exit_code == 0
        assert "Extension pgvector activée" in result.stdout


def test_db_init_failure(runner: CliRunner) -> None:
    """Vérifie db init en cas d'erreur."""
    with patch("csc.cli.init_vector_extension", return_value=False):
        result = runner.invoke(app, ["db", "init"])
        assert result.exit_code == 1
        assert "Impossible d'activer l'extension pgvector" in result.stdout


def test_backup_create_mock(runner: CliRunner, tmp_path: Path) -> None:
    """Vérifie que la commande backup create appelle le bon mécanisme."""

    def fake_run(
        cmd: list[str],
        stdout: object = None,
        stderr: object = None,
        check: bool = False,
    ) -> MagicMock:
        if hasattr(stdout, "write"):
            stdout.write(b"fake dump data")
        return MagicMock(returncode=0, stderr=b"")

    with (
        patch("csc.cli.settings.backup_dir", tmp_path),
        patch(
            "shutil.which", side_effect=lambda cmd: "/usr/bin/docker" if cmd == "docker" else None
        ),
        patch("subprocess.run", side_effect=fake_run),
    ):
        result = runner.invoke(app, ["backup", "create"])
        assert result.exit_code == 0
        assert "Sauvegarde réussie via Docker" in result.stdout
