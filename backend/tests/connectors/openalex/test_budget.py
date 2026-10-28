"""Tests unitaires pour le suivi du budget OpenAlex et le seuil d'arrêt à 90 %."""

import pytest

from csc.connectors.openalex.budget import OpenAlexBudgetManager
from csc.connectors.openalex.exceptions import OpenAlexBudgetExceededError


def test_budget_initial_state(tmp_budget_manager: OpenAlexBudgetManager) -> None:
    status = tmp_budget_manager.get_status()
    assert float(status["credits_used"] or 0.0) == 0.0
    assert float(status["daily_limit"] or 0.0) == 1000.0
    # Aucune exception avant d'atteindre le seuil
    tmp_budget_manager.check_budget_before_call()


def test_budget_record_usage(tmp_budget_manager: OpenAlexBudgetManager) -> None:
    tmp_budget_manager.record_usage(credits_used=150.0, remaining_reported=850.0)
    status = tmp_budget_manager.get_status()
    assert float(status["credits_used"] or 0.0) == 150.0
    assert float(status["remaining_reported"] or 0.0) == 850.0

    # Nouvel appel incrémente
    tmp_budget_manager.record_usage(credits_used=200.0, remaining_reported=650.0)
    status2 = tmp_budget_manager.get_status()
    assert float(status2["credits_used"] or 0.0) == 350.0
    assert float(status2["remaining_reported"] or 0.0) == 650.0


def test_budget_exceeded_threshold_90_pct(tmp_budget_manager: OpenAlexBudgetManager) -> None:
    # Seuil à 90 % de 1000 = 900 crédits
    tmp_budget_manager.record_usage(credits_used=899.0)
    tmp_budget_manager.check_budget_before_call()  # OK

    tmp_budget_manager.record_usage(credits_used=2.0)  # Total 901.0 >= 900.0
    with pytest.raises(OpenAlexBudgetExceededError) as exc_info:
        tmp_budget_manager.check_budget_before_call()

    assert "90 %" in str(exc_info.value)
    assert "901.0" in str(exc_info.value)


def test_budget_exceeded_by_remaining_reported(tmp_budget_manager: OpenAlexBudgetManager) -> None:
    # Si l'en-tête officiel indique qu'il reste <= 10 % du budget
    tmp_budget_manager.record_usage(credits_used=50.0, remaining_reported=90.0)
    with pytest.raises(OpenAlexBudgetExceededError) as exc_info:
        tmp_budget_manager.check_budget_before_call()

    assert "inférieur à 10 %" in str(exc_info.value)


def test_budget_reset_on_new_day(tmp_budget_manager: OpenAlexBudgetManager) -> None:
    tmp_budget_manager.record_usage(credits_used=950.0)

    # Modifier artificiellement la date du registre vers hier
    ledger_path = tmp_budget_manager._resolve_ledger_path()
    content = ledger_path.read_text(encoding="utf-8")
    modified = content.replace(tmp_budget_manager._current_day(), "2020-01-01")
    ledger_path.write_text(modified, encoding="utf-8")

    # Lecture pour le jour courant doit réinitialiser
    status = tmp_budget_manager.get_status()
    assert float(status["credits_used"] or 0.0) == 0.0
    tmp_budget_manager.check_budget_before_call()  # Ne lève plus d'exception
