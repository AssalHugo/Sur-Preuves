"""Point d'entrée de la CLI csc (Typer)."""

import shutil
import subprocess
from datetime import datetime

import typer
from rich.console import Console

from csc.config import settings
from csc.db import check_db_status, init_vector_extension

app = typer.Typer(
    name="csc",
    help="Comparateur Programmes politiques 2027 x État de la science (CLI principale).",
    no_args_is_help=True,
)
console = Console()

# ------------------------------------------------------------------------------
# Groupe 1 : DB
# ------------------------------------------------------------------------------
db_app = typer.Typer(help="Gestion de la base de données PostgreSQL et pgvector.")
app.add_typer(db_app, name="db")


@db_app.command(name="status")
def db_status_cmd() -> None:
    """Vérifie l'état de la connexion et de l'extension pgvector."""
    console.print(f"[bold blue]Vérification de la base :[/bold blue] {settings.database_url}")
    connected, msg, vector_version = check_db_status()

    if not connected:
        console.print(f"[bold red]✗ Échec de connexion :[/bold red] {msg}")
        raise typer.Exit(code=1)

    console.print(f"[bold green]✓ Connecté avec succès :[/bold green] {msg}")
    if vector_version:
        console.print(f"[bold green]✓ Extension pgvector active :[/bold green] v{vector_version}")
    else:
        console.print(
            "[yellow]! Extension pgvector absente.[/yellow] "
            "Exécutez `csc db init` ou `make db-migrate` pour l'activer."
        )


@db_app.command(name="init")
def db_init_cmd() -> None:
    """Initialise l'extension pgvector dans la base de données."""
    console.print(
        f"[bold blue]Initialisation de pgvector sur :[/bold blue] {settings.database_url}"
    )
    ok = init_vector_extension()
    if ok:
        console.print("[bold green]✓ Extension pgvector activée ou déjà présente.[/bold green]")
    else:
        console.print("[bold red]✗ Impossible d'activer l'extension pgvector.[/bold red]")
        raise typer.Exit(code=1)


@db_app.command(name="migrate")
def db_migrate_cmd() -> None:
    """Applique les migrations de base de données."""
    db_init_cmd()


# ------------------------------------------------------------------------------
# Groupes réservés pour les lots suivants (avec messages d'étape POC non implémentée)
# ------------------------------------------------------------------------------


def _register_placeholder(
    name: str,
    help_text: str,
    lot: str,
) -> typer.Typer:
    sub_app = typer.Typer(help=help_text, invoke_without_command=True)

    @sub_app.callback(invoke_without_command=True)
    def _default(ctx: typer.Context) -> None:
        if ctx.invoked_subcommand is None:
            console.print(f"[yellow][POC] {name} : étape non implémentée ({lot})[/yellow]")

    app.add_typer(sub_app, name=name)
    return sub_app


# L03 Couche LLM
_register_placeholder("llm", "Couche d'abstraction LLM Gemini (L03)", "Lot L03")

# L04 Connecteur OpenAlex
_register_placeholder("openalex", "Connecteur API OpenAlex (L04)", "Lot L04")

# L05 Connecteur HAL
_register_placeholder("hal", "Connecteur API HAL Solr (L05)", "Lot L05")

# L06 Connecteur Semantic Scholar
_register_placeholder("s2", "Connecteur Semantic Scholar (L06)", "Lot L06")

# L07 Connecteur Parlementaire
_register_placeholder("parlement", "Connecteur NosParlementaires & Open Data AN (L07)", "Lot L07")

# L08 Ingestion & Embeddings
_register_placeholder("ingest", "Ingestion documentaire PDF / Docling (L08)", "Lot L08")
_register_placeholder("embed", "Génération des embeddings fastembed (L08)", "Lot L08")

# L09 Extraction
_register_placeholder(
    "extract", "Extraction des affirmations factuelles et causales (L09)", "Lot L09"
)

# L10 Recherche de preuves
_register_placeholder(
    "evidence", "Recherche et qualification de preuves scientifiques (L10)", "Lot L10"
)

# L11 Synthèse
_register_placeholder("synth", "Synthèse de fiches par LLM (L11)", "Lot L11")

# L12 Vérification croisée
_register_placeholder("verify", "Vérification croisée et contrôles déterministes (L12)", "Lot L12")

# L13 Bilan de législature
_register_placeholder("legislature", "Bilan de législature (L13)", "Lot L13")

# L14 Back-office de relecture
review_app = typer.Typer(help="Back-office de relecture (L14)", invoke_without_command=True)


@review_app.callback(invoke_without_command=True)
def review_default(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        console.print("[yellow][POC] review : étape non implémentée (Lot L14)[/yellow]")


@review_app.command(name="serve")
def review_serve(
    host: str = typer.Option("127.0.0.1", "--host", help="Hôte d'écoute"),
    port: int = typer.Option(8000, "--port", help="Port d'écoute"),
) -> None:
    """Lance le serveur de relecture."""
    console.print(
        f"[bold blue]Lancement du back-office de relecture sur http://{host}:{port}[/bold blue]"
    )
    console.print("[yellow][POC] Service de relecture non implémenté (Lot L14)[/yellow]")


app.add_typer(review_app, name="review")

# L14 / L02 Publication & Bundle
publish_app = typer.Typer(
    help="Publication et génération du bundle JSON (L14 / L02)", invoke_without_command=True
)


@publish_app.callback(invoke_without_command=True)
def publish_default(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        console.print("[yellow][POC] publish : étape non implémentée (Lot L14)[/yellow]")


@publish_app.command(name="bundle")
def publish_bundle(
    include_drafts: bool = typer.Option(False, "--include-drafts", help="Inclure les brouillons"),
    poc: bool = typer.Option(False, "--poc", help="Mode démonstration POC"),
) -> None:
    """Exporte le bundle de publication pour le site statique."""
    console.print(
        f"[yellow][POC] publish bundle : étape non implémentée (Lot L14) "
        f"[include_drafts={include_drafts}, poc={poc}][/yellow]"
    )


app.add_typer(publish_app, name="publish")

# L16 Sauvegardes
backup_app = typer.Typer(
    help="Gestion des sauvegardes de la base PostgreSQL (L16)", invoke_without_command=True
)


@backup_app.callback(invoke_without_command=True)
def backup_default(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        backup_create()


@backup_app.command(name="create")
def backup_create() -> None:
    """Effectue un dump pg_dump -Fc vers BACKUP_DIR."""
    backup_dir = settings.backup_dir
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = backup_dir / f"backup_{timestamp}.dump"

    console.print(f"[bold blue]Création de la sauvegarde vers :[/bold blue] {backup_file}")

    # Vérifie si pg_dump est présent sur l'hôte
    pg_dump_path = shutil.which("pg_dump")
    if pg_dump_path:
        db_url = settings.database_url.replace("postgresql+psycopg://", "postgresql://")
        cmd = [
            pg_dump_path,
            "-Fc",
            "-d",
            db_url,
            "-f",
            str(backup_file),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if res.returncode == 0 and backup_file.exists() and backup_file.stat().st_size > 0:
            console.print(f"[bold green]✓ Sauvegarde réussie :[/bold green] {backup_file}")
            return
        if backup_file.exists() and backup_file.stat().st_size == 0:
            backup_file.unlink(missing_ok=True)
        err_msg = res.stderr.strip()
        console.print(
            f"[yellow]! Échec avec pg_dump local ({err_msg}), essai via Docker...[/yellow]"
        )

    # Repli via conteneur Docker csc-db
    docker_path = shutil.which("docker")
    if docker_path:
        cmd_docker = [
            docker_path,
            "compose",
            "exec",
            "-T",
            "db",
            "pg_dump",
            "-U",
            settings.postgres_user,
            "-Fc",
            settings.postgres_db,
        ]
        try:
            with open(backup_file, "wb") as f_out:
                res_docker = subprocess.run(
                    cmd_docker, stdout=f_out, stderr=subprocess.PIPE, check=False
                )
            if res_docker.returncode == 0 and backup_file.stat().st_size > 0:
                console.print(
                    f"[bold green]✓ Sauvegarde réussie via Docker :[/bold green] {backup_file}"
                )
                return
            docker_err = res_docker.stderr.decode().strip()
            console.print(f"[bold red]✗ Échec du dump via Docker : {docker_err}[/bold red]")
        except Exception as e:
            console.print(f"[bold red]✗ Erreur lors de l'exécution Docker : {e}[/bold red]")
        finally:
            if backup_file.exists() and backup_file.stat().st_size == 0:
                backup_file.unlink(missing_ok=True)

    # Si ni l'un ni l'autre n'a fonctionné
    console.print("[bold red]✗ Impossible de réaliser la sauvegarde.[/bold red]")
    raise typer.Exit(code=1)


app.add_typer(backup_app, name="backup")


if __name__ == "__main__":
    app()
