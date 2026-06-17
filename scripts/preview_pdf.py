"""Generate a sample financial plan PDF from a baked SessionState.

Mirrors web/src/demoSnapshot.ts so the PDF can be regenerated without
running a live voice session. Useful for design iteration and for
attaching a representative artefact to demo material.

Usage:  python scripts/preview_pdf.py
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core.plan_pdf import generate_pdf
from core.session import Goal, SessionState


def build_state() -> SessionState:
    s = SessionState()
    s.name = "Rakshit"
    s.age = 28
    s.monthly_income = 150000
    s.monthly_expenses = 70000
    s.monthly_emi = 25000
    s.expense_breakdown = {
        "investments": 20000,
        "household_expenses": 30000,
        "utilities": 8000,
        "entertainment": 12000,
        "emis": 25000,
    }
    s.ratios = {
        "surplus": 55000,
        "savings_rate": 0.3667,
        "savings_band": "good",
        "debt_to_income": 0.1667,
        "dti_band": "average",
    }
    s.risk_profile = "balanced"
    s.portfolio = {
        "holdings": [
            {"fund": "ICICI Prudential Bluechip Fund", "type": "equity",
             "current_value": 520000, "monthly_sip": 5000, "rating": 4, "flag": None},
            {"fund": "Parag Parikh Flexi Cap Fund", "type": "equity",
             "current_value": 410000, "monthly_sip": 4000, "rating": 4, "flag": None},
            {"fund": "Quant Mid Cap Fund", "type": "equity",
             "current_value": 280000, "monthly_sip": 3000, "rating": 2, "flag": "underperformer"},
            {"fund": "ICICI Prudential Infrastructure Fund", "type": "equity",
             "current_value": 150000, "monthly_sip": 0, "rating": 1, "flag": "underperformer"},
            {"fund": "HDFC Short Term Debt Fund", "type": "debt",
             "current_value": 290000, "monthly_sip": 3000, "rating": 4, "flag": None},
            {"fund": "HDFC Liquid Fund", "type": "debt",
             "current_value": 150000, "monthly_sip": 0, "rating": 3, "flag": None},
        ],
        "total_value": 1800000,
        "total_monthly_sip": 15000,
        "underperformers": ["Quant Mid Cap Fund", "ICICI Prudential Infrastructure Fund"],
        "review_methodology": (
            "We judge each fund on two things: whether its category suits the user's "
            "risk profile, and a fund score based on consistency versus category "
            "average plus downside protection."
        ),
        "fund_reviews": [
            {"fund": "Quant Mid Cap Fund", "status": "weak",
             "reason": "the mid cap category fits a balanced risk profile; the fund "
                       "score is weak on consistency versus category average or "
                       "downside protection"},
            {"fund": "ICICI Prudential Infrastructure Fund", "status": "weak",
             "reason": "thematic funds are too concentrated for this risk-profile-led "
                       "plan; the fund score is weak on consistency versus category "
                       "average or downside protection"},
        ],
    }
    s.goals = [
        Goal(name="Emergency fund", target_amount_today=570000, horizon_years=1,
             priority=1, inflated_target=570000, projected_from_existing=570000,
             required_sip=0, funded=True),
        Goal(name="Buy a house in Pune", target_amount_today=10000000, horizon_years=10,
             priority=2, inflated_target=19671514, projected_from_existing=7160004,
             required_sip=50500, funded=True),
        Goal(name="Daughter's education", target_amount_today=3000000, horizon_years=12,
             priority=3, inflated_target=9415285, projected_from_existing=0,
             required_sip=9500, funded=True),
        Goal(name="Sabbatical year", target_amount_today=2000000, horizon_years=8,
             priority=4, inflated_target=3500000, projected_from_existing=0,
             required_sip=0, funded=False),
    ]
    s.proposed_portfolios = {
        "Buy a house in Pune": {
            "goal": "Buy a house in Pune",
            "horizon_bucket": "long",
            "horizon_years": 10,
            "monthly_sip": 50500,
            "selection_basis": ("Funds selected for the user's risk profile and goal "
                                "horizon using return profile, downside protection, "
                                "volatility and role in the phase."),
            "phases": [
                {"phase": 1, "duration_years": 5,
                 "allocation": {"equity": 0.8, "debt": 0.15, "gold": 0.05}, "funds": []},
                {"phase": 2, "duration_years": 3,
                 "allocation": {"equity": 0.5, "debt": 0.4, "gold": 0.1}, "funds": []},
                {"phase": 3, "duration_years": 2,
                 "allocation": {"equity": 0.2, "debt": 0.7, "gold": 0.1}, "funds": []},
            ],
            "current_phase": {
                "phase": 1, "duration_years": 5,
                "allocation": {"equity": 0.8, "debt": 0.15, "gold": 0.05},
                "funds": [
                    {"fund": "UTI Nifty 50 Index Fund", "category": "equity", "monthly_sip": 24000},
                    {"fund": "Parag Parikh Flexi Cap Fund", "category": "equity", "monthly_sip": 16000},
                    {"fund": "HDFC Short Duration Debt Fund", "category": "debt", "monthly_sip": 5500},
                    {"fund": "Nippon India Gold Savings Fund", "category": "gold", "monthly_sip": 2500},
                    {"fund": "HDFC Liquid Fund", "category": "debt", "monthly_sip": 2500},
                ],
            },
        },
        "Daughter's education": {
            "goal": "Daughter's education",
            "horizon_bucket": "long",
            "horizon_years": 12,
            "monthly_sip": 9500,
            "selection_basis": "Long-horizon child goal; index-led equity core with small gold hedge.",
            "phases": [
                {"phase": 1, "duration_years": 6,
                 "allocation": {"equity": 0.85, "debt": 0.10, "gold": 0.05}, "funds": []},
                {"phase": 2, "duration_years": 4,
                 "allocation": {"equity": 0.55, "debt": 0.35, "gold": 0.10}, "funds": []},
                {"phase": 3, "duration_years": 2,
                 "allocation": {"equity": 0.25, "debt": 0.65, "gold": 0.10}, "funds": []},
            ],
            "current_phase": {
                "phase": 1, "duration_years": 6,
                "allocation": {"equity": 0.85, "debt": 0.10, "gold": 0.05},
                "funds": [
                    {"fund": "UTI Nifty 50 Index Fund", "category": "equity", "monthly_sip": 4500},
                    {"fund": "Parag Parikh Flexi Cap Fund", "category": "equity", "monthly_sip": 3500},
                    {"fund": "HDFC Short Duration Debt Fund", "category": "debt", "monthly_sip": 1000},
                    {"fund": "Nippon India Gold Savings Fund", "category": "gold", "monthly_sip": 500},
                ],
            },
        },
    }
    return s


if __name__ == "__main__":
    path = generate_pdf(build_state())
    print(path)
