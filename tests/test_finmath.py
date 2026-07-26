import math

import pytest

from core import finmath as fm


def test_round_to_500():
    assert fm.round_to_500(12320) == 12500
    assert fm.round_to_500(12200) == 12000
    assert fm.round_to_500(0) == 0


def test_inflation_for_goal():
    assert fm.inflation_for_goal("Daughter's education") == 0.10
    assert fm.inflation_for_goal("Buy a house in Pune") == 0.07
    assert fm.inflation_for_goal("New car") == 0.06


def test_inflate():
    # 1 crore house, 12 years at 7%: 1e7 * 1.07^12
    assert fm.inflate(1e7, 12, 0.07) == pytest.approx(22_521_916, rel=1e-4)
    # 5 lakh at 6% for 1 year
    assert fm.inflate(500_000, 1, 0.06) == pytest.approx(530_000)


def test_financial_ratios():
    r = fm.financial_ratios(100_000, 60_000, 10_000, existing_monthly_sip=12_000)
    assert r["surplus"] == 30_000
    assert r["savings_rate"] == pytest.approx(0.30)
    assert r["savings_band"] == "good"
    assert r["debt_to_income"] == pytest.approx(0.10)
    assert r["dti_band"] == "average"
    assert r["idle_surplus"] == 18_000


def test_financial_ratios_bands():
    assert fm.financial_ratios(100_000, 98_000)["savings_band"] == "bad"
    assert fm.financial_ratios(100_000, 90_000)["savings_band"] == "average"
    assert fm.financial_ratios(100_000, 80_000)["savings_band"] == "good"
    assert fm.financial_ratios(100_000, 50_000, 30_000)["dti_band"] == "bad"
    assert fm.financial_ratios(100_000, 50_000, 10_000)["dti_band"] == "average"
    assert fm.financial_ratios(100_000, 50_000, 3_000)["dti_band"] == "good"


def test_lumpsum_fv():
    assert fm.lumpsum_fv(100_000, 0.11, 5) == pytest.approx(168_505.8, rel=1e-4)
    assert fm.lumpsum_fv(100_000, 0.07, 0) == pytest.approx(100_000)


def test_sip_fv():
    # 10k/month at 12% for 10 years (annuity-due): ≈ ₹23.23L
    assert fm.sip_fv(10_000, 0.12, 10) == pytest.approx(2_323_391, rel=1e-4)
    assert fm.sip_fv(0, 0.12, 10) == 0.0


def test_required_sip_inverts_sip_fv():
    target = fm.sip_fv(10_000, 0.12, 10)
    assert fm.required_sip(target, 0.12, 10) == pytest.approx(10_000, rel=1e-6)
    assert fm.required_sip(0, 0.12, 10) == 0.0


def test_years_to_target_inverts_sip_fv():
    target = fm.sip_fv(10_000, 0.12, 10)
    assert fm.years_to_target(10_000, target, 0.12) == pytest.approx(10.0, abs=0.05)
    assert fm.years_to_target(0, 100_000, 0.12) == math.inf


def test_blended_growth():
    assert fm.blended_growth(50, 50) == pytest.approx(0.09)
    assert fm.blended_growth(100, 0) == pytest.approx(0.11)
    assert fm.blended_growth(0, 0) == pytest.approx(0.07)


def test_affordability():
    assert fm.affordability(10_000, 20_000) == "comfortable"
    assert fm.affordability(18_000, 20_000) == "tight"
    assert fm.affordability(25_000, 20_000) == "unaffordable"
    assert fm.affordability(5_000, 0) == "unaffordable"


def test_risk_scoring():
    assert fm.score_risk_answer("I would top up and buy more") == 1
    assert fm.score_risk_answer("I'd panic and sell everything") == -1
    assert fm.score_risk_answer("I would just hold and wait") == 0
    # conservative keywords win within an answer
    assert fm.score_risk_answer("I'd buy more but honestly I'd be scared") == -1


def test_risk_profile_mapping():
    agg = fm.risk_profile_from_answers(["top up more", "buy the dip", "hold"])
    assert agg["risk_profile"] == "aggressive"
    assert agg["equity_band"] == 0.75
    assert agg["expected_return"] == 0.13

    cons = fm.risk_profile_from_answers(["exit everything", "move to FD"])
    assert cons["risk_profile"] == "conservative"
    assert cons["equity_band"] == 0.30

    # Mixed signals (one aggressive + one conservative) cancel → balanced.
    bal = fm.risk_profile_from_answers(["top up", "protect capital"])
    assert bal["risk_profile"] == "balanced"
    assert bal["expected_return"] == 0.11

    # Single tilt is enough under the 2-question threshold (±1).
    tilt = fm.risk_profile_from_answers(["hold steady", "maximize returns"])
    assert tilt["risk_profile"] == "aggressive"


def test_horizon_bucket():
    assert fm.horizon_bucket(1) == "short"
    assert fm.horizon_bucket(3) == "short"
    assert fm.horizon_bucket(4) == "medium"
    assert fm.horizon_bucket(7) == "medium"
    assert fm.horizon_bucket(8) == "long"
    assert fm.horizon_bucket(25) == "long"


def test_build_phases_short():
    phases = fm.build_phases("short", 3, 10_000)
    assert len(phases) == 1
    assert phases[0]["duration_years"] == 3
    assert phases[0]["allocation"]["debt"] == 0.95
    # Equity allocation is 0 → no equity funds in this phase
    assert all(f["bucket"] != "equity" for f in phases[0]["funds"])


def test_build_phases_medium_durations_sum_to_horizon():
    for years in (4, 5, 6, 7):
        phases = fm.build_phases("medium", years, 20_000)
        assert len(phases) == 2
        assert sum(p["duration_years"] for p in phases) == years


def test_build_phases_long_glides_equity_down():
    phases = fm.build_phases("long", 25, 30_000)
    assert len(phases) == 3
    assert sum(p["duration_years"] for p in phases) == 25
    # Equity share should decrease monotonically across phases (glide-down)
    eq = [p["allocation"]["equity"] for p in phases]
    assert eq[0] > eq[1] > eq[2]
    # All phases have at least one fund
    assert all(p["funds"] for p in phases)


def test_career_break_simulation_reserve_and_build_rate():
    result = fm.simulate_career_break(
        monthly_income=150_000,
        essential_outflow=75_000,
        idle_surplus=40_000,
        debt_fund_cushion=440_000,
        duration_months=12,
        starts_in_months=24,
        income_reduction_percent=100,
    )

    assert result["reserve_required"] == 900_000
    assert result["additional_reserve"] == 460_000
    assert result["monthly_reserve_build"] == 19_000
    assert result["goal_surplus_after_build"] == 20_833


def test_home_timing_simulation_compares_two_horizons():
    result = fm.simulate_home_timing(
        amount_today=10_000_000,
        current_horizon_years=5,
        proposed_horizon_years=8,
        portfolio_value=1_800_000,
        portfolio_monthly_sip=15_000,
        equity_value=1_360_000,
        debt_value=440_000,
        expected_return=0.11,
        idle_surplus=40_000,
    )

    assert result["current"]["horizon_years"] == 5
    assert result["proposed"]["horizon_years"] == 8
    assert result["current"]["required_sip"] > result["proposed"]["required_sip"]
    assert result["sip_delta"] < 0


def test_starting_family_simulation_combines_cost_and_education():
    result = fm.simulate_starting_family(
        child_arrival_years=2,
        added_monthly_cost=15_000,
        education_cost_today=3_000_000,
        expected_return=0.11,
        idle_surplus=40_000,
    )

    assert result["education_horizon_years"] == 20
    assert result["education_target"] > 3_000_000
    assert result["education_sip"] > 0
    assert result["remaining_surplus"] < 40_000


def test_runway_extension_uses_weak_funds_then_low_volatility_holdings():
    holdings = [
        {
            "fund": "Strong Core Equity",
            "category": "large cap",
            "type": "equity",
            "current_value": 520_000,
            "rating": 4,
            "flag": None,
        },
        {
            "fund": "Weak Mid Cap",
            "category": "mid cap",
            "type": "equity",
            "current_value": 280_000,
            "rating": 2,
            "flag": "underperformer",
        },
        {
            "fund": "Thematic Infra",
            "category": "thematic",
            "type": "equity",
            "current_value": 150_000,
            "rating": 1,
            "flag": "underperformer",
        },
        {
            "fund": "Liquid Fund",
            "category": "liquid",
            "type": "debt",
            "current_value": 150_000,
            "rating": 3,
            "flag": None,
        },
        {
            "fund": "Short Term Debt",
            "category": "short duration debt",
            "type": "debt",
            "current_value": 290_000,
            "rating": 4,
            "flag": None,
        },
    ]

    result = fm.plan_runway_extensions(
        liquid_cash=570_000,
        monthly_draw=75_000,
        holdings=holdings,
    )

    twelve, eighteen = result["options"]
    assert result["current_runway_months"] == 7.6
    assert twelve["additional_required"] == 330_000
    assert [(item["fund"], item["amount"]) for item in twelve["withdrawals"]] == [
        ("Thematic Infra", 150_000),
        ("Weak Mid Cap", 180_000),
    ]
    assert eighteen["additional_required"] == 780_000
    assert [(item["fund"], item["amount"]) for item in eighteen["withdrawals"]] == [
        ("Thematic Infra", 150_000),
        ("Weak Mid Cap", 280_000),
        ("Liquid Fund", 150_000),
        ("Short Term Debt", 200_000),
    ]
    assert all(
        item["fund"] != "Strong Core Equity"
        for option in result["options"]
        for item in option["withdrawals"]
    )
