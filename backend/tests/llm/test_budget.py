"""Tests for budget manager, monthly cap enforcement, and batch splitting."""

import logging
from pathlib import Path

import pytest

from csc.llm.budget import BudgetManager
from csc.llm.exceptions import BudgetExceededError


def test_budget_exceeded_before_call(tmp_path: Path) -> None:
    """Pre-flight check must raise BudgetExceededError if call exceeds monthly cap."""
    bm = BudgetManager(ledger_dir=tmp_path)

    # Initial spend: 8.50 USD on 9.00 USD cap
    bm.record_spend(8.50)
    assert bm.get_month_spend() == 8.50

    # Estimate of 0.60 USD -> Total 9.10 USD > 9.00 USD cap -> Rejected
    with pytest.raises(BudgetExceededError) as exc_info:
        bm.check_budget(estimated_cost=0.60)

    assert "monthly budget ceiling of $9.00 USD exceeded" in str(exc_info.value)


def test_budget_batch_splitting(tmp_path: Path) -> None:
    """A batch must be split into admitted and deferred items to fit remaining budget."""
    bm = BudgetManager(ledger_dir=tmp_path)

    # Spend 7.00 USD on 9.00 USD cap -> 2.00 USD remaining
    bm.record_spend(7.00)

    items = [f"item_{i}" for i in range(10)]
    item_cost = 0.50  # 4 items fit in 2.00 USD remaining

    admitted, deferred = bm.split_batch_to_fit(items=items, item_cost=item_cost)
    assert len(admitted) == 4
    assert len(deferred) == 6
    assert admitted == ["item_0", "item_1", "item_2", "item_3"]
    assert deferred == ["item_4", "item_5", "item_6", "item_7", "item_8", "item_9"]


def test_budget_elevation_logging(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Elevation of LLM_MONTHLY_CAP_USD above default 9.00 USD must be logged."""
    monkeypatch.setenv("LLM_MONTHLY_CAP_USD", "15.0")
    bm = BudgetManager()
    with caplog.at_level(logging.INFO):
        cap = bm.get_monthly_cap()

    assert cap == 15.0
    assert "elevated to 15.00 USD" in caplog.text


def test_budget_reconciliation_warning(caplog: pytest.LogCaptureFixture) -> None:
    """Deviation between estimated and actual cost exceeding 20% triggers a warning."""
    bm = BudgetManager()
    with caplog.at_level(logging.WARNING):
        # 30% gap
        bm.reconcile(estimated_cost=0.10, actual_cost=0.13)

    assert "Cost reconciliation alert" in caplog.text
    assert "deviated by 30.0%" in caplog.text
