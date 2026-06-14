import asyncio

from agent import tools
from core.session import Goal, STATE, reset


def _run(coro):
    return asyncio.run(coro)


def test_mf_central_requires_explicit_consent():
    """MF Central cannot be pulled before explicit user consent."""
    reset()
    result = _run(tools.pull_mf_central({}))

    assert result["error"] == "missing: MF Central consent"
    assert "ask permission" in result["instruction"]


def test_account_aggregator_requires_mf_central_first():
    """Finvu Account Aggregator is blocked until MF Central has been pulled."""
    reset()
    result = _run(tools.pull_account_aggregator({
        "user_confirmed_consent": True,
        "consent_context": "User agreed.",
    }))

    assert result["error"] == "missing: the MF Central pull"
    assert "Call pull_mf_central first" in result["instruction"]


def test_account_aggregator_correction_reuses_existing_consent(monkeypatch):
    """A correction to AA data after the first pull must not request a second OTP."""
    requested = []

    async def fake_request_otp(provider):
        requested.append(provider)
        return "1234"

    reset()
    monkeypatch.setattr(tools.consent, "request_otp", fake_request_otp)
    STATE.portfolio = {"total_monthly_sip": 12_000}

    first = _run(tools.pull_account_aggregator({
        "user_confirmed_consent": True,
        "consent_context": "User agreed to trigger Finvu OTP.",
    }))
    correction = _run(tools.pull_account_aggregator({
        "user_confirmed_consent": False,
        "consent_context": "Correction after prior consent.",
        "monthly_income": 175_000,
    }))

    assert requested == ["Finvu Account Aggregator"]
    assert first["monthly_income"] == 150_000
    assert correction["monthly_income"] == 175_000


def test_financial_snapshot_confirmation_requires_manual_assets_answer():
    """Goals remain blocked until the user answers the additional-assets question."""
    reset()
    STATE.aa_assets = {"epf": 450_000, "nps": 50_000, "stocks": 500_000}
    STATE.ratios = {"idle_surplus": 43_000}

    result = _run(tools.confirm_financial_snapshot({
        "user_confirmed_financial_data": True,
        "user_answered_additional_assets": False,
        "confirmation_context": "User confirmed AA but has not answered manual assets.",
    }))

    assert result["error"] == "missing: the additional-investments answer"
    assert "PPF, FDs, gold" in result["instruction"]


def test_cashflow_confirmation_is_separate_from_investment_confirmation():
    """Cash flow can be confirmed first, but goals stay blocked until investments are confirmed."""
    reset()
    STATE.aa_assets = {"epf": 450_000, "nps": 50_000, "stocks": 500_000}
    STATE.ratios = {"idle_surplus": 43_000, "savings_rate": 0.29, "debt_to_income": 0.17}

    result = _run(tools.confirm_financial_snapshot({
        "user_confirmed_cashflow": True,
        "user_confirmed_investments": False,
        "user_answered_additional_assets": False,
        "confirmation_context": "User confirmed income and expenses only.",
    }))

    assert STATE.cashflow_confirmed is True
    assert STATE.investments_confirmed is False
    assert STATE.financial_snapshot_confirmed is False
    assert result["error"] == "missing: explicit confirmation of investments"
    assert "savings rate" in result["instruction"]


def test_account_aggregator_correction_invalidates_stale_goal_plan(monkeypatch):
    """Changing income/expense after planning clears stale goals and asks for fresh confirmation."""
    requested = []

    async def fake_request_otp(provider):
        requested.append(provider)
        return "1234"

    reset()
    monkeypatch.setattr(tools.consent, "request_otp", fake_request_otp)
    STATE.portfolio = {
        "total_monthly_sip": 12_000,
        "total_value": 1_800_000,
        "equity_value": 1_360_000,
        "debt_value": 440_000,
    }
    _run(tools.pull_account_aggregator({
        "user_confirmed_consent": True,
        "consent_context": "User agreed to trigger Finvu OTP.",
    }))
    STATE.cashflow_confirmed = True
    STATE.investments_confirmed = True
    STATE.financial_snapshot_confirmed = True
    STATE.goals = [Goal("Emergency fund", 570_000, 1, 1, inflated_target=570_000, required_sip=0)]
    STATE.proposed_portfolios = {"Retirement": {"goal": "Retirement"}}

    result = _run(tools.pull_account_aggregator({
        "user_confirmed_consent": False,
        "consent_context": "Correction after prior consent.",
        "monthly_expenses": 80_000,
    }))

    assert requested == ["Finvu Account Aggregator"]
    assert result["monthly_expenses"] == 80_000
    assert STATE.cashflow_confirmed is False
    assert STATE.investments_confirmed is True
    assert STATE.financial_snapshot_confirmed is False
    assert STATE.goals == []
    assert STATE.proposed_portfolios == {}
