"""Budget monitoring, hard spending cap enforcement, and batch splitting."""

import json
import logging
import os
from calendar import monthrange
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, TypeVar

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from csc.config import settings
from csc.db.models import LlmCallModel
from csc.llm.exceptions import BudgetExceededError

logger = logging.getLogger(__name__)

T = TypeVar("T")


class BudgetManager:
    """Enforces strict monthly budget ceiling, tracks spend, and reconciles costs."""

    def __init__(self, ledger_dir: Path | None = None) -> None:
        self.ledger_dir = ledger_dir or settings.llm_cache_dir
        self._logged_caps: set[float] = set()

    def _resolve_ledger_path(self) -> Path:
        target = self.ledger_dir
        if not target.is_absolute():
            root = Path(__file__).resolve().parents[4]
            target = root / target
        target.mkdir(parents=True, exist_ok=True)
        return target / "budget_ledger.json"

    def get_monthly_cap(self) -> float:
        """Retrieve current active monthly cap, logging any elevation above baseline (9.0)."""
        env_val = os.getenv("LLM_MONTHLY_CAP_USD")
        if env_val is not None:
            try:
                cap = float(env_val)
            except ValueError:
                cap = settings.llm_monthly_cap_usd
        else:
            cap = settings.llm_monthly_cap_usd

        if cap > 9.0 and cap not in self._logged_caps:
            logger.info("LLM monthly spend cap has been elevated to %.2f USD.", cap)
            self._logged_caps.add(cap)

        return cap

    def _get_month_bounds(
        self, target_date: date | datetime | None = None
    ) -> tuple[datetime, datetime]:
        ref: datetime
        if target_date is None:
            ref = datetime.now(UTC)
        elif isinstance(target_date, datetime):
            ref = (
                target_date.astimezone(UTC)
                if target_date.tzinfo
                else target_date.replace(tzinfo=UTC)
            )
        else:
            ref = datetime(target_date.year, target_date.month, target_date.day, tzinfo=UTC)

        start = datetime(ref.year, ref.month, 1, 0, 0, 0, tzinfo=UTC)
        _, last_day = monthrange(ref.year, ref.month)
        end = datetime(ref.year, ref.month, last_day, 23, 59, 59, 999999, tzinfo=UTC)
        return start, end

    def get_month_spend(
        self,
        session: Session | None = None,
        target_date: date | datetime | None = None,
    ) -> float:
        """Calculate total spend in USD for the target calendar month."""
        start, end = self._get_month_bounds(target_date)

        if session is not None:
            try:
                stmt = select(func.coalesce(func.sum(LlmCallModel.cost_usd), 0.0)).where(
                    LlmCallModel.created_at >= start,
                    LlmCallModel.created_at <= end,
                )
                db_spend = float(session.scalar(stmt) or 0.0)
                return round(db_spend, 6)
            except Exception as e:
                logger.debug("Could not read spend from database, using file ledger: %s", e)

        # Fallback to local file ledger
        ledger_path = self._resolve_ledger_path()
        if not ledger_path.exists():
            return 0.0

        try:
            records = json.loads(ledger_path.read_text(encoding="utf-8"))
            total = 0.0
            start_iso = start.isoformat()
            end_iso = end.isoformat()
            for r in records:
                ts = r.get("created_at", "")
                if start_iso <= ts <= end_iso:
                    total += float(r.get("cost_usd", 0.0))
            return round(total, 6)
        except Exception:
            return 0.0

    def record_spend(
        self,
        cost_usd: float,
        target_date: datetime | None = None,
        role: str = "unknown",
        model: str = "unknown",
    ) -> None:
        """Record spend into local ledger for offline persistence."""
        if cost_usd <= 0.0:
            return
        ledger_path = self._resolve_ledger_path()
        records: list[dict[str, Any]] = []
        if ledger_path.exists():
            try:
                records = json.loads(ledger_path.read_text(encoding="utf-8"))
            except Exception:
                records = []

        now = target_date or datetime.now(UTC)
        records.append(
            {
                "created_at": now.isoformat(),
                "cost_usd": cost_usd,
                "role": role,
                "model": model,
            }
        )
        try:
            ledger_path.write_text(json.dumps(records, indent=2), encoding="utf-8")
        except Exception:
            pass

    def check_budget(
        self,
        estimated_cost: float,
        session: Session | None = None,
        target_date: date | datetime | None = None,
    ) -> None:
        """Ensure that the proposed expenditure does not exceed the monthly ceiling."""
        cap = self.get_monthly_cap()
        spent = self.get_month_spend(session=session, target_date=target_date)
        if spent + estimated_cost > cap:
            raise BudgetExceededError(
                f"Operation rejected: monthly budget ceiling of ${cap:.2f} USD exceeded. "
                f"Current spend: ${spent:.4f} USD, estimated job cost: ${estimated_cost:.4f} USD."
            )

    def split_batch_to_fit(
        self,
        items: list[T],
        item_cost: float,
        session: Session | None = None,
        target_date: date | datetime | None = None,
    ) -> tuple[list[T], list[T]]:
        """Split a batch into admitted items and deferred items to fit remaining monthly budget."""
        if item_cost <= 0.0:
            return items, []

        cap = self.get_monthly_cap()
        spent = self.get_month_spend(session=session, target_date=target_date)
        remaining = max(0.0, cap - spent)

        max_admitted = int(remaining // item_cost)
        admitted = items[:max_admitted]
        deferred = items[max_admitted:]
        return admitted, deferred

    def reconcile(self, estimated_cost: float, actual_cost: float) -> None:
        """Compare estimated and actual costs, logging warning if gap exceeds 20%."""
        if estimated_cost <= 0.0:
            return
        gap = abs(actual_cost - estimated_cost) / estimated_cost
        if gap > 0.20:
            logger.warning(
                "Cost reconciliation alert: actual cost ($%.6f USD) deviated by %.1f%% "
                "from initial estimate ($%.6f USD).",
                actual_cost,
                gap * 100,
                estimated_cost,
            )

    def get_summary(
        self,
        session: Session | None = None,
        target_date: date | datetime | None = None,
    ) -> dict[str, Any]:
        """Produce full budget overview including role/model breakdowns and projection."""
        now = datetime.now(UTC)
        ref = target_date or now
        spent = self.get_month_spend(session=session, target_date=ref)
        cap = self.get_monthly_cap()
        remaining = max(0.0, cap - spent)

        day_of_month = now.day
        _, days_in_month = monthrange(now.year, now.month)
        projected = (spent / day_of_month) * days_in_month if day_of_month > 0 else spent

        by_role: dict[str, float] = {}
        by_model: dict[str, float] = {}

        if session is not None:
            try:
                start, end = self._get_month_bounds(ref)
                role_stmt = (
                    select(LlmCallModel.prompt_id, func.sum(LlmCallModel.cost_usd))
                    .where(LlmCallModel.created_at >= start, LlmCallModel.created_at <= end)
                    .group_by(LlmCallModel.prompt_id)
                )
                for r_name, r_cost in session.execute(role_stmt):
                    by_role[str(r_name)] = round(float(r_cost or 0.0), 4)

                model_stmt = (
                    select(LlmCallModel.model, func.sum(LlmCallModel.cost_usd))
                    .where(LlmCallModel.created_at >= start, LlmCallModel.created_at <= end)
                    .group_by(LlmCallModel.model)
                )
                for m_name, m_cost in session.execute(model_stmt):
                    by_model[str(m_name)] = round(float(m_cost or 0.0), 4)
            except Exception:
                pass

        # If DB query returned nothing or session wasn't provided, read file ledger
        if not by_role and not by_model:
            ledger_path = self._resolve_ledger_path()
            if ledger_path.exists():
                try:
                    records = json.loads(ledger_path.read_text(encoding="utf-8"))
                    start, end = self._get_month_bounds(ref)
                    start_iso = start.isoformat()
                    end_iso = end.isoformat()
                    for r in records:
                        ts = r.get("created_at", "")
                        if start_iso <= ts <= end_iso:
                            c = float(r.get("cost_usd", 0.0))
                            r_id = str(r.get("role", "unknown"))
                            m_id = str(r.get("model", "unknown"))
                            by_role[r_id] = round(by_role.get(r_id, 0.0) + c, 4)
                            by_model[m_id] = round(by_model.get(m_id, 0.0) + c, 4)
                except Exception:
                    pass

        return {
            "spent": round(spent, 4),
            "cap": round(cap, 2),
            "remaining": round(remaining, 4),
            "projected": round(projected, 4),
            "by_role": by_role,
            "by_model": by_model,
        }


budget_manager = BudgetManager()
