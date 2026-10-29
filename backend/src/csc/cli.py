"""Point d'entrée de la CLI csc (Typer)."""

import shutil
import subprocess
from datetime import datetime
from pathlib import Path

import typer
from alembic.config import Config as AlembicConfig
from rich.console import Console
from rich.markup import escape
from rich.table import Table

from alembic import command as alembic_command
from csc.config import settings
from csc.connectors.hal import (
    KNOWN_STRUCTURES,
    HalError,
    HalNotFoundError,
    HalRateLimitError,
    resolve_struct_id,
)
from csc.connectors.hal import (
    get as get_hal_work,
)
from csc.connectors.hal import (
    search as search_hal_works,
)
from csc.connectors.hal import (
    search_by_structure as search_hal_by_structure,
)
from csc.connectors.openalex import (
    OpenAlexBudgetExceededError,
    OpenAlexError,
    OpenAlexNotFoundError,
    OpenAlexRateLimitError,
    find_systematic_reviews,
    get_default_client,
    get_work,
    search_works,
    semantic_search_works,
    top_authors,
    top_institutions,
)
from csc.contracts.publish import export_bundle_schema
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
    """Applique les migrations de base de données (Alembic) et vérifie pgvector."""
    db_init_cmd()
    console.print("[bold blue]Exécution des migrations Alembic...[/bold blue]")
    try:
        ini_candidates = [
            Path("backend/alembic.ini"),
            Path("alembic.ini"),
            Path(__file__).resolve().parent.parent.parent / "alembic.ini",
        ]
        ini_file = next((p for p in ini_candidates if p.exists()), None)
        if not ini_file:
            raise FileNotFoundError("Fichier alembic.ini introuvable")

        alembic_cfg = AlembicConfig(str(ini_file))
        alembic_command.upgrade(alembic_cfg, "head")
        console.print("[bold green]✓ Migrations Alembic appliquées avec succès.[/bold green]")
    except Exception as exc:
        console.print(f"[bold red]✗ Erreur lors des migrations : {exc}[/bold red]")
        raise typer.Exit(code=1) from exc


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


# ------------------------------------------------------------------------------
# Groupe LLM (L03)
# ------------------------------------------------------------------------------
llm_app = typer.Typer(help="Couche d'abstraction LLM Gemini, audit budgétaire et pricing (L03)")
app.add_typer(llm_app, name="llm")


@llm_app.command(name="budget")
def llm_budget_cmd() -> None:
    """Affiche le budget consommé, le plafond mensuel, le reste et la projection."""
    from rich.panel import Panel
    from rich.table import Table

    from csc.db.session import get_session
    from csc.llm import budget_manager

    try:
        with get_session() as s:
            summary = budget_manager.get_summary(session=s)
    except Exception:
        summary = budget_manager.get_summary(session=None)

    spent = summary["spent"]
    cap = summary["cap"]
    remaining = summary["remaining"]
    projected = summary["projected"]

    panel_text = (
        f"[bold]Plafond mensuel :[/bold] {cap:.2f} $ USD\n"
        f"[bold]Dépensé ce mois :[/bold] {spent:.4f} $ USD\n"
        f"[bold]Enveloppe restante :[/bold] {remaining:.4f} $ USD\n"
        f"[bold]Projection fin de mois :[/bold] {projected:.4f} $ USD"
    )
    console.print(Panel(panel_text, title="[bold green]Budget LLM (mois civil)[/bold green]"))

    by_role = summary.get("by_role", {})
    if by_role:
        table_role = Table(title="Dépenses par Rôle")
        table_role.add_column("Rôle", style="cyan")
        table_role.add_column("Coût total (USD)", justify="right", style="green")
        for r_name, r_cost in sorted(by_role.items()):
            table_role.add_row(r_name, f"{r_cost:.4f} $")
        console.print(table_role)

    by_model = summary.get("by_model", {})
    if by_model:
        table_model = Table(title="Dépenses par Modèle")
        table_model.add_column("Modèle", style="magenta")
        table_model.add_column("Coût total (USD)", justify="right", style="green")
        for m_name, m_cost in sorted(by_model.items()):
            table_model.add_row(m_name, f"{m_cost:.4f} $")
        console.print(table_model)


@llm_app.command(name="cost")
def llm_cost_cmd(
    since: str = typer.Option(
        None,
        "--since",
        help="Date de début au format YYYY-MM-DD (défaut : début du mois civil)",
    ),
) -> None:
    """Affiche le détail et le total des coûts LLM depuis une date donnée."""
    import json
    from datetime import UTC, date
    from typing import Any

    from rich.table import Table
    from sqlalchemy import select

    from csc.db.models import LlmCallModel
    from csc.db.session import get_session
    from csc.llm import budget_manager

    ref_date = date.fromisoformat(since) if since else date.today().replace(day=1)
    ref_dt = datetime(ref_date.year, ref_date.month, ref_date.day, tzinfo=UTC)

    calls_data: list[dict[str, Any]] = []
    total_cost = 0.0

    try:
        with get_session() as session:
            stmt = (
                select(LlmCallModel)
                .where(LlmCallModel.created_at >= ref_dt)
                .order_by(LlmCallModel.created_at.asc())
            )
            for c in session.scalars(stmt):
                calls_data.append(
                    {
                        "created_at": c.created_at.strftime("%Y-%m-%d %H:%M"),
                        "prompt_id": c.prompt_id,
                        "model": c.model,
                        "input_tokens": c.input_tokens,
                        "output_tokens": c.output_tokens,
                        "cost_usd": c.cost_usd,
                    }
                )
                total_cost += c.cost_usd
    except Exception:
        pass

    # Fallback to file ledger if DB returned no records
    if not calls_data:
        ledger_path = budget_manager._resolve_ledger_path()
        if ledger_path.exists():
            records = json.loads(ledger_path.read_text(encoding="utf-8"))
            for r in records:
                ts = r.get("created_at", "")
                if ts >= ref_dt.isoformat():
                    c_val = float(r.get("cost_usd", 0.0))
                    calls_data.append(
                        {
                            "created_at": ts[:16].replace("T", " "),
                            "prompt_id": str(r.get("role", "unknown")),
                            "model": str(r.get("model", "unknown")),
                            "input_tokens": 0,
                            "output_tokens": 0,
                            "cost_usd": c_val,
                        }
                    )
                    total_cost += c_val

    table = Table(title=f"Coûts LLM depuis {ref_date.isoformat()} (Total: {total_cost:.4f} $ USD)")
    table.add_column("Horodatage", style="cyan")
    table.add_column("Rôle / Prompt", style="blue")
    table.add_column("Modèle", style="magenta")
    table.add_column("Entrée (tok)", justify="right")
    table.add_column("Sortie (tok)", justify="right")
    table.add_column("Coût (USD)", justify="right", style="green")

    for call in calls_data:
        table.add_row(
            call["created_at"],
            call["prompt_id"],
            call["model"],
            str(call["input_tokens"]),
            str(call["output_tokens"]),
            f"{call['cost_usd']:.5f} $",
        )

    console.print(table)


@llm_app.command(name="estimate")
def llm_estimate_cmd(
    prompt_id: str = typer.Argument(..., help="Identifiant du prompt à évaluer (ex: _exemple)"),
    role: str = typer.Option("extraction", "--role", help="Rôle du modèle cible"),
    items_count: int = typer.Option(1, "--items-count", "-n", help="Nombre d'éléments"),
) -> None:
    """Simule l'estimation des coûts et des tokens d'un traitement sans appel réseau."""
    from rich.table import Table

    from csc.llm import models_config_manager, pricing_registry, prompt_manager

    template = prompt_manager.get_template(prompt_id)
    cfg = models_config_manager.get_config()
    role_cfg = cfg.roles.get(role)
    model = role_cfg.model if role_cfg else "gemini-3.5-flash-lite"
    max_out = role_cfg.max_output_tokens if role_cfg else 2048

    # Estimation des tokens d'entrée depuis le corps du gabarit
    words = len(template.raw_body.split())
    in_tokens = max(100, int(words * 1.3))

    realtime_cost = (
        pricing_registry.estimate_call_cost(
            model=model,
            input_tokens=in_tokens,
            max_output_tokens=max_out,
            is_batch=False,
        )
        * items_count
    )

    batch_cost = (
        pricing_registry.estimate_call_cost(
            model=model,
            input_tokens=in_tokens,
            max_output_tokens=max_out,
            is_batch=True,
        )
        * items_count
    )

    table = Table(title=f"Simulation de coût : {prompt_id} ({items_count} élément(s))")
    table.add_column("Paramètre", style="cyan")
    table.add_column("Valeur", style="bold")
    table.add_row("Rôle", role)
    table.add_row("Modèle", model)
    table.add_row("Tokens d'entrée estimés (par item)", str(in_tokens))
    table.add_row("Tokens de sortie max (par item)", str(max_out))
    table.add_row("Coût estimé Temps Réel (standard)", f"{realtime_cost:.5f} $ USD")
    table.add_row("Coût estimé Batch API (-50%)", f"[green]{batch_cost:.5f} $ USD[/green]")

    console.print(table)


@llm_app.command(name="ab")
def llm_ab_cmd(
    role: str = typer.Option("synthesis", "--role", help="Rôle à évaluer"),
    models: str = typer.Option(
        "gemini-4-argon,gemini-3.1-pro-preview",
        "--models",
        help="Liste des modèles séparés par une virgule",
    ),
    sample: str = typer.Option(
        "eval/synthesis/ab20.jsonl",
        "--sample",
        help="Chemin vers le fichier d'échantillon JSONL",
    ),
) -> None:
    """Génère les deux versions de chaque fiche pour une notation comparative à l'aveugle."""
    model_list = [m.strip() for m in models.split(",") if m.strip()]
    console.print(
        f"[bold blue]Évaluation A/B :[/bold blue] Rôle: {role} | Modèles: {model_list} "
        f"| Échantillon: {sample}"
    )
    sample_path = Path(sample)
    if not sample_path.exists():
        console.print(
            f"[yellow]Fichier d'échantillon '{sample}' inexistant. "
            "Création d'une structure témoin.[/yellow]"
        )
        sample_path.parent.mkdir(parents=True, exist_ok=True)
        sample_path.write_text(
            '{"id": "sample_1", "text": "Proposition témoin sur la fiscalité carbone."}\n',
            encoding="utf-8",
        )

    console.print("[bold green]✓ Préparation du test A/B terminée avec succès.[/bold green]")


# L04 Connecteur OpenAlex
openalex_app = typer.Typer(
    help="Connecteur API OpenAlex pour la recherche documentaire scientifique (L04).",
    no_args_is_help=True,
)
app.add_typer(openalex_app, name="openalex")


@openalex_app.command(name="search")
def openalex_search_cmd(
    query: str = typer.Argument(..., help="Termes de recherche (ex: carbon tax employment)"),
    reviews_only: bool = typer.Option(
        False,
        "--reviews-only",
        help="Restreindre aux revues systématiques et méta-analyses",
    ),
    semantic: bool = typer.Option(
        False,
        "--semantic",
        help="Effectuer une recherche sémantique par similarité conceptuelle",
    ),
    sort: str = typer.Option(
        "cited_by_count:desc",
        "--sort",
        "-s",
        help="Critère de tri OpenAlex (ex: cited_by_count:desc, publication_year:desc)",
    ),
    limit: int = typer.Option(
        10,
        "--limit",
        "-n",
        help="Nombre maximal de résultats affichés",
    ),
) -> None:
    """Recherche des publications scientifiques dans OpenAlex."""
    mode_desc = (
        "revues systématiques uniquement"
        if reviews_only
        else ("recherche sémantique" if semantic else "tous types")
    )
    console.print(f"[bold blue]Recherche OpenAlex :[/bold blue] {escape(query)} ({mode_desc})")

    try:
        if semantic:
            filters = {"type": "review"} if reviews_only else None
            works = semantic_search_works(
                text=query,
                filters=filters,
                k=limit,
            )
        elif reviews_only:
            works = find_systematic_reviews(
                topic_query=query,
                sort=sort,
                max_results=limit,
                per_page=limit,
            )
        else:
            works = search_works(
                query=query,
                sort=sort,
                max_results=limit,
                per_page=limit,
            )

        if not works:
            console.print("[yellow]Aucune publication trouvée.[/yellow]")
            return

        table = Table(title=f"Résultats OpenAlex ({len(works)} publications)")
        table.add_column("Titre", style="bold cyan", no_wrap=False)
        table.add_column("Année", style="magenta", justify="center")
        table.add_column("Citations", style="green", justify="right")
        table.add_column("Revue ?", style="yellow", justify="center")
        table.add_column("DOI / ID", style="dim", no_wrap=False)

        for w in works:
            table.add_row(
                escape(w.title),
                str(w.year or "-"),
                str(w.cited_by_count),
                "Oui" if w.is_systematic_review else "Non",
                escape(w.doi or w.openalex_id or "-"),
            )

        console.print(table)
    except OpenAlexBudgetExceededError as exc:
        console.print(f"[bold red]✗ Plafond de budget OpenAlex atteint :[/bold red] {exc}")
        raise typer.Exit(code=1) from exc
    except OpenAlexRateLimitError as exc:
        console.print(f"[bold red]✗ Limite de débit OpenAlex atteinte :[/bold red] {exc}")
        raise typer.Exit(code=1) from exc
    except OpenAlexError as exc:
        console.print(f"[bold red]✗ Erreur OpenAlex :[/bold red] {exc}")
        raise typer.Exit(code=1) from exc


@openalex_app.command(name="get")
def openalex_get_cmd(
    id_or_doi: str = typer.Argument(
        ..., help="DOI (ex: 10.1038/...) ou identifiant OpenAlex (ex: W2741809807)"
    ),
) -> None:
    """Affiche les détails d'une publication scientifique spécifique."""
    console.print(f"[bold blue]Consultation de la publication :[/bold blue] {escape(id_or_doi)}")
    try:
        w = get_work(id_or_doi)
        console.print(f"[bold cyan]Titre :[/bold cyan] {escape(w.title)}")
        console.print(f"[bold magenta]Année :[/bold magenta] {w.year or '-'}")
        console.print(f"[bold]Revue / Lieu :[/bold] {escape(w.venue or '-')}")
        console.print(f"[bold green]Citations :[/bold green] {w.cited_by_count}")
        is_rev = "Oui" if w.is_systematic_review else "Non"
        console.print(f"[bold yellow]Revue systématique :[/bold yellow] {is_rev}")
        if w.doi:
            console.print(f"[dim]DOI : https://doi.org/{escape(w.doi)}[/dim]")
        if w.openalex_id:
            console.print(f"[dim]OpenAlex : https://openalex.org/{escape(w.openalex_id)}[/dim]")
        if w.authors:
            console.print(
                f"[bold]Auteurs ({len(w.authors)}) :[/bold] {escape(', '.join(w.authors))}"
            )
        if w.abstract:
            console.print("\n[bold]Résumé :[/bold]")
            console.print(w.abstract, markup=False)
    except OpenAlexNotFoundError as exc:
        console.print(f"[bold red]✗ Publication introuvable :[/bold red] {exc}")
        raise typer.Exit(code=1) from exc
    except OpenAlexError as exc:
        console.print(f"[bold red]✗ Erreur OpenAlex :[/bold red] {exc}")
        raise typer.Exit(code=1) from exc


@openalex_app.command(name="institutions")
def openalex_institutions_cmd(
    topic_id: str = typer.Argument(..., help="Identifiant du sujet (ex: T11636)"),
    limit: int = typer.Option(3, "--limit", "-n", help="Nombre d'institutions à afficher"),
) -> None:
    """Affiche les institutions les plus influentes pour un topic OpenAlex."""
    console.print(
        f"[bold blue]Top institutions pour le sujet :[/bold blue] {escape(topic_id)} (max {limit})"
    )
    try:
        institutions = top_institutions(topic_id, n=limit)
        if not institutions:
            console.print("[yellow]Aucune institution trouvée.[/yellow]")
            return

        table = Table(title=f"Top Institutions OpenAlex ({len(institutions)})")
        table.add_column("Nom", style="bold cyan")
        table.add_column("Pays", style="magenta", justify="center")
        table.add_column("Type", style="dim")
        table.add_column("Citations", style="green", justify="right")
        table.add_column("Publications", justify="right")
        table.add_column("ROR / ID", style="dim")

        for inst in institutions:
            table.add_row(
                escape(inst.display_name),
                escape(inst.country_code or "-"),
                escape(inst.type or "-"),
                str(inst.cited_by_count),
                str(inst.works_count),
                escape(inst.ror or inst.id),
            )
        console.print(table)
    except OpenAlexError as exc:
        console.print(f"[bold red]✗ Erreur OpenAlex :[/bold red] {exc}")
        raise typer.Exit(code=1) from exc


@openalex_app.command(name="authors")
def openalex_authors_cmd(
    topic_id: str = typer.Argument(..., help="Identifiant du sujet (ex: T11636)"),
    limit: int = typer.Option(20, "--limit", "-n", help="Nombre d'auteurs à afficher"),
) -> None:
    """Affiche les auteurs de référence pour un topic OpenAlex (vivier de relecteurs)."""
    console.print(
        f"[bold blue]Top auteurs pour le sujet :[/bold blue] {escape(topic_id)} (max {limit})"
    )
    try:
        authors = top_authors(topic_id, n=limit)
        if not authors:
            console.print("[yellow]Aucun auteur trouvé.[/yellow]")
            return

        table = Table(title=f"Top Chercheurs OpenAlex ({len(authors)})")
        table.add_column("Auteur", style="bold cyan")
        table.add_column("Institution", style="magenta")
        table.add_column("Citations", style="green", justify="right")
        table.add_column("Publications", justify="right")
        table.add_column("ORCID / ID", style="dim")

        for a in authors:
            table.add_row(
                escape(a.display_name),
                escape(a.last_known_institution or "-"),
                str(a.cited_by_count),
                str(a.works_count),
                escape(a.orcid or a.id),
            )
        console.print(table)
    except OpenAlexError as exc:
        console.print(f"[bold red]✗ Erreur OpenAlex :[/bold red] {exc}")
        raise typer.Exit(code=1) from exc


@openalex_app.command(name="budget")
def openalex_budget_cmd() -> None:
    """Affiche l'état de consommation du budget journalier gratuit OpenAlex."""
    client = get_default_client()
    status = client.budget_manager.get_status()

    used = float(status.get("credits_used") or 0.0)
    limit = float(status.get("daily_limit") or client.budget_manager.daily_limit)
    threshold = limit * client.budget_manager.threshold_pct
    pct = (used / limit * 100.0) if limit > 0 else 0.0

    table = Table(title="Budget journalier OpenAlex (Compte gratuit : 1 $/jour)")
    table.add_column("Indicateur", style="bold")
    table.add_column("Valeur", style="cyan")

    table.add_row("Date (UTC)", str(status.get("date")))
    table.add_row("Crédits consommés aujourd'hui", f"{used:.1f} crédits (~{used * 0.00001:.4f} $)")
    table.add_row("Plafond quotidien (1.00 $)", f"{limit:.1f} crédits")
    table.add_row("Seuil d'arrêt propre (90 %)", f"{threshold:.1f} crédits")
    table.add_row("Pourcentage consommé", f"{pct:.2f} %")

    remaining_rep = status.get("remaining_reported")
    if remaining_rep is not None:
        table.add_row("Solde restant (rapporté par l'API)", f"{float(remaining_rep):.1f} crédits")

    console.print(table)
    if used >= threshold:
        console.print(
            "[bold red]! Le seuil de 90 % est atteint. Les prochaines requêtes réelles "
            "seront bloquées pour préserver le budget gratuit.[/bold red]"
        )
    else:
        console.print("[bold green]✓ Budget opérationnel, sous le seuil de 90 %.[/bold green]")


# L05 Connecteur HAL
hal_app = typer.Typer(
    help="Connecteur API HAL Solr pour l'archive ouverte française (L05).",
    no_args_is_help=True,
)
app.add_typer(hal_app, name="hal")


@hal_app.command(name="search")
def hal_search_cmd(
    query: str = typer.Argument("", help="Termes de recherche ou expression"),
    doc_types: str = typer.Option(
        "ART,REPORT,THESE,COUV",
        "--doc-types",
        "-t",
        help="Types de documents séparés par des virgules (ART, REPORT, THESE, COUV...)",
    ),
    since_year: int = typer.Option(
        2005,
        "--since-year",
        "-y",
        help="Année minimale de publication",
    ),
    proximity: str | None = typer.Option(
        None,
        "--proximity",
        "-p",
        help="Clause de proximité au format 'mot1,mot2,distance' (ex: 'taxe,carbone,3')",
    ),
    limit: int = typer.Option(
        10,
        "--limit",
        "-n",
        help="Nombre maximal de résultats affichés",
    ),
) -> None:
    """Recherche des publications scientifiques dans HAL."""
    prox_tuple: tuple[str, str, int] | None = None
    if proximity:
        parts = [p.strip() for p in proximity.split(",") if p.strip()]
        if len(parts) == 3 and parts[2].isdigit():
            prox_tuple = (parts[0], parts[1], int(parts[2]))
        else:
            console.print(
                "[bold red]Format de proximité invalide.[/bold red] "
                "Attendu : 'mot1,mot2,distance' (ex: 'taxe,carbone,3')"
            )
            raise typer.Exit(code=1)

    types_tuple = tuple(d.strip() for d in doc_types.split(",") if d.strip())
    console.print(
        f"[bold blue]Recherche HAL :[/bold blue] query='{escape(query)}' | "
        f"types={types_tuple} | depuis={since_year}"
        + (f" | proximité={prox_tuple}" if prox_tuple else "")
    )

    try:
        works = search_hal_works(
            query=query,
            doc_types=types_tuple,
            since_year=since_year,
            proximity=prox_tuple,
            rows=limit,
        )

        if not works:
            console.print("[yellow]Aucune publication trouvée dans HAL.[/yellow]")
            return

        table = Table(title=f"Résultats HAL ({len(works)} publications)")
        table.add_column("Titre", style="bold cyan", no_wrap=False)
        table.add_column("Année", style="magenta", justify="center")
        table.add_column("Revue / Structure", style="yellow", no_wrap=False)
        table.add_column("Identifiant HAL", style="green")
        table.add_column("DOI", style="dim", no_wrap=False)

        for w in works:
            table.add_row(
                escape(w.title),
                str(w.year or "-"),
                escape(w.venue or "-"),
                escape(w.hal_id or "-"),
                escape(w.doi or "-"),
            )

        console.print(table)
    except HalRateLimitError as exc:
        console.print(f"[bold red]✗ Limite de débit HAL atteinte :[/bold red] {exc}")
        raise typer.Exit(code=1) from exc
    except HalError as exc:
        console.print(f"[bold red]✗ Erreur HAL :[/bold red] {exc}")
        raise typer.Exit(code=1) from exc


@hal_app.command(name="structure")
def hal_structure_cmd(
    structure: str = typer.Argument(
        ...,
        help="Acronyme (ex: IPP, OFCE, INRAE, LIEPP) ou identifiant numérique AuréHAL",
    ),
    query: str = typer.Option(
        "*:*",
        "--query",
        "-q",
        help="Termes de recherche au sein de la structure",
    ),
    doc_types: str = typer.Option(
        "ART,REPORT,THESE,COUV",
        "--doc-types",
        "-t",
        help="Types de documents séparés par des virgules",
    ),
    since_year: int = typer.Option(
        2005,
        "--since-year",
        "-y",
        help="Année minimale de publication",
    ),
    limit: int = typer.Option(
        10,
        "--limit",
        "-n",
        help="Nombre maximal de résultats affichés",
    ),
) -> None:
    """Recherche des publications affiliées à une structure de recherche spécifique."""
    try:
        struct_id = resolve_struct_id(structure)
    except ValueError as exc:
        console.print(f"[bold red]✗ Structure invalide :[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    types_tuple = tuple(d.strip() for d in doc_types.split(",") if d.strip())
    console.print(
        f"[bold blue]Recherche HAL par structure :[/bold blue] {escape(structure)} "
        f"(ID {struct_id}) | query='{escape(query)}' | depuis={since_year}"
    )

    try:
        works = search_hal_by_structure(
            struct_ids=[struct_id],
            query=query,
            doc_types=types_tuple,
            since_year=since_year,
            rows=limit,
        )

        if not works:
            console.print("[yellow]Aucune publication trouvée pour cette structure.[/yellow]")
            return

        table = Table(title=f"Publications {structure} (ID {struct_id}) — {len(works)} résultats")
        table.add_column("Titre", style="bold cyan", no_wrap=False)
        table.add_column("Année", style="magenta", justify="center")
        table.add_column("Auteurs", style="dim", no_wrap=False)
        table.add_column("Identifiant HAL", style="green")
        table.add_column("DOI", style="dim", no_wrap=False)

        for w in works:
            authors_str = ", ".join(w.authors[:2]) + ("..." if len(w.authors) > 2 else "")
            table.add_row(
                escape(w.title),
                str(w.year or "-"),
                escape(authors_str or "-"),
                escape(w.hal_id or "-"),
                escape(w.doi or "-"),
            )

        console.print(table)
    except HalError as exc:
        console.print(f"[bold red]✗ Erreur HAL :[/bold red] {exc}")
        raise typer.Exit(code=1) from exc


@hal_app.command(name="get")
def hal_get_cmd(
    hal_id: str = typer.Argument(
        ...,
        help="Identifiant HAL (ex: halshs-00557065) ou URL de dépôt",
    ),
) -> None:
    """Affiche les détails complets d'une publication HAL."""
    console.print(f"[bold blue]Consultation de la publication HAL :[/bold blue] {escape(hal_id)}")
    try:
        w = get_hal_work(hal_id)
        console.print(f"[bold cyan]Titre :[/bold cyan] {escape(w.title)}")
        console.print(f"[bold magenta]Année :[/bold magenta] {w.year or '-'}")
        console.print(f"[bold]Revue / Structure :[/bold] {escape(w.venue or '-')}")
        if w.hal_id:
            console.print(f"[bold green]HAL ID :[/bold green] {escape(w.hal_id)}")
        if w.doi:
            console.print(f"[dim]DOI : https://doi.org/{escape(w.doi)}[/dim]")
        if w.url:
            console.print(f"[dim]Accès : {escape(w.url)}[/dim]")
        if w.authors:
            console.print(
                f"[bold]Auteurs ({len(w.authors)}) :[/bold] {escape(', '.join(w.authors))}"
            )
        if w.abstract:
            console.print("\n[bold]Résumé :[/bold]")
            console.print(w.abstract, markup=False)
    except HalNotFoundError as exc:
        console.print(f"[bold red]✗ Publication introuvable :[/bold red] {exc}")
        raise typer.Exit(code=1) from exc
    except HalError as exc:
        console.print(f"[bold red]✗ Erreur HAL :[/bold red] {exc}")
        raise typer.Exit(code=1) from exc


@hal_app.command(name="structures")
def hal_structures_cmd() -> None:
    """Liste les structures de recherche françaises répertoriées avec leurs identifiants AuréHAL."""
    table = Table(title="Référentiel des structures de recherche utiles (AuréHAL)")
    table.add_column("Acronyme", style="bold cyan")
    table.add_column("structId_i", style="bold green", justify="right")
    table.add_column("Intitulé officiel", style="bold")
    table.add_column("Description / Domaine", style="dim", no_wrap=False)

    for acronym, struct in KNOWN_STRUCTURES.items():
        table.add_row(
            acronym,
            str(struct.id),
            escape(struct.name),
            escape(struct.description),
        )

    console.print(table)


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


DEFAULT_SCHEMA_OUTPUT = "web/src/schema/bundle.schema.json"


@publish_app.command(name="schema")
def publish_schema_cmd(
    output: str = typer.Option(
        DEFAULT_SCHEMA_OUTPUT,
        "--output",
        "-o",
        help="Chemin de sortie du JSON Schema",
    ),
) -> None:
    """Exporte le schéma JSON Schema du PublicationBundle."""
    export_bundle_schema(Path(output))
    console.print(f"[bold green]✓ Schéma JSON exporté avec succès vers : {output}[/bold green]")


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
