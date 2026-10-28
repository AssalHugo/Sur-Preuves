"""Suivi du budget journalier gratuit OpenAlex et arrêt propre à 90 %."""

import json
import logging
import threading
from datetime import UTC, datetime
from pathlib import Path

from csc.config import settings
from csc.connectors.openalex.exceptions import OpenAlexBudgetExceededError

logger = logging.getLogger(__name__)

DEFAULT_DAILY_CREDITS_LIMIT = 100_000.0  # 1.00 $ = 100 000 crédits
DEFAULT_THRESHOLD_PCT = 0.90  # 90 %


class OpenAlexBudgetManager:
    """Gestionnaire du budget quotidien de crédits OpenAlex."""

    def __init__(
        self,
        ledger_dir: Path | None = None,
        daily_limit: float = DEFAULT_DAILY_CREDITS_LIMIT,
        threshold_pct: float = DEFAULT_THRESHOLD_PCT,
    ) -> None:
        self.ledger_dir = ledger_dir or settings.openalex_cache_dir
        self.daily_limit = daily_limit
        self.threshold_pct = threshold_pct
        self._lock = threading.Lock()

    def _resolve_ledger_path(self) -> Path:
        target = self.ledger_dir
        if not target.is_absolute():
            # Racine du dépôt (civic-tech/)
            from csc.config import _PROJECT_ROOT

            target = _PROJECT_ROOT / target
        target.mkdir(parents=True, exist_ok=True)
        return target / "daily_credits.json"

    def _current_day(self) -> str:
        return datetime.now(UTC).strftime("%Y-%m-%d")

    def _read_ledger(self) -> dict[str, float | str | None]:
        path = self._resolve_ledger_path()
        today = self._current_day()
        if not path.exists():
            return {
                "date": today,
                "credits_used": 0.0,
                "daily_limit": self.daily_limit,
                "remaining_reported": None,
                "last_updated": datetime.now(UTC).isoformat(),
            }

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if data.get("date") != today:
                # Nouveau jour UTC, réinitialisation du compteur journalier
                return {
                    "date": today,
                    "credits_used": 0.0,
                    "daily_limit": self.daily_limit,
                    "remaining_reported": None,
                    "last_updated": datetime.now(UTC).isoformat(),
                }
            return data  # type: ignore[no-any-return]
        except Exception as exc:
            logger.debug("Impossible de lire le registre des crédits OpenAlex : %s", exc)
            return {
                "date": today,
                "credits_used": 0.0,
                "daily_limit": self.daily_limit,
                "remaining_reported": None,
                "last_updated": datetime.now(UTC).isoformat(),
            }

    def _write_ledger(self, data: dict[str, float | str | None]) -> None:
        path = self._resolve_ledger_path()
        tmp_path = path.with_suffix(".tmp")
        try:
            tmp_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
            tmp_path.replace(path)
        except Exception as exc:
            logger.warning("Échec d'écriture du registre de crédits OpenAlex : %s", exc)
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except OSError:
                    pass

    def get_status(self) -> dict[str, float | str | None]:
        """Retourne l'état courant de consommation des crédits journaliers."""
        with self._lock:
            return self._read_ledger()

    def check_budget_before_call(self) -> None:
        """Vérifie si le seuil de 90% du budget journalier n'est pas encore dépassé."""
        with self._lock:
            ledger = self._read_ledger()
            credits_used = float(ledger.get("credits_used") or 0.0)
            daily_limit = float(ledger.get("daily_limit") or self.daily_limit)
            max_allowed = daily_limit * self.threshold_pct

            # Vérification basée sur les crédits consommés comptabilisés
            if credits_used >= max_allowed:
                raise OpenAlexBudgetExceededError(
                    "Arrêt propre : seuil de 90 % du budget journalier OpenAlex atteint "
                    f"({credits_used:.1f}/{daily_limit:.1f} crédits, seuil : {max_allowed:.1f})."
                )

            # Vérification basée sur l'en-tête officiel restant si rapporté
            remaining = ledger.get("remaining_reported")
            if remaining is not None:
                rem_val = float(remaining)
                min_remaining = daily_limit * (1.0 - self.threshold_pct)
                if rem_val <= min_remaining:
                    raise OpenAlexBudgetExceededError(
                        f"Arrêt propre : solde restant de crédits OpenAlex inférieur à 10 % "
                        f"({rem_val:.1f} restants sur {daily_limit:.1f})."
                    )

    def record_usage(
        self,
        credits_used: float,
        remaining_reported: float | None = None,
        limit_reported: float | None = None,
    ) -> None:
        """Enregistre la consommation d'une requête et met à jour les limites."""
        with self._lock:
            ledger = self._read_ledger()
            prev_used = float(ledger.get("credits_used") or 0.0)
            new_used = prev_used + max(0.0, credits_used)

            ledger["credits_used"] = new_used
            if limit_reported is not None and limit_reported > 0:
                ledger["daily_limit"] = limit_reported
                self.daily_limit = limit_reported
            if remaining_reported is not None:
                ledger["remaining_reported"] = remaining_reported
            ledger["last_updated"] = datetime.now(UTC).isoformat()

            self._write_ledger(ledger)

    def reset(self) -> None:
        """Réinitialise le registre pour les tests."""
        with self._lock:
            today = self._current_day()
            self._write_ledger(
                {
                    "date": today,
                    "credits_used": 0.0,
                    "daily_limit": self.daily_limit,
                    "remaining_reported": None,
                    "last_updated": datetime.now(UTC).isoformat(),
                }
            )
