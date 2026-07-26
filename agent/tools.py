"""Tool schemas + handlers. Tools own ALL math; the LLM only converses.

Every handler returns through session.tool_response() so the LLM is re-anchored
with narration_hint / progress / next_step on every call. Guard rails return an
{"error", "instruction"} payload instead of raising.
"""

import datetime as _dt
import json
import math

from loguru import logger

from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.adapters.schemas.tools_schema import ToolsSchema
from pipecat.services.llm_service import FunctionCallParams

from core import finmath as fm
from core import consent, plan_pdf, portfolio_data, ui_bus
from core.run_transcript import record_tool_call, record_tool_result
from core.session import STATE, Goal, get_goal, missing, snapshot, tool_response


GOAL_TYPES = [
    {"key": "emergency", "label": "Emergency fund", "section": "Safety net",
     "blurb": "Six months of outflow — your runway if life slips."},
    {"key": "retirement", "label": "Retirement", "section": "Long-term independence",
     "blurb": "Anchor a corpus to age 60 so work stays a choice."},
    {"key": "home", "label": "Home", "section": "Aspirations",
     "blurb": "Down payment in today's rupees, then we inflate it forward."},
    {"key": "education", "label": "Children's education", "section": "Aspirations",
     "blurb": "Higher-ed cost compounds fastest — usually 18 − age years out."},
    {"key": "car", "label": "Car or vehicle", "section": "Aspirations",
     "blurb": "Short-horizon goal; usually three to five years."},
    {"key": "other", "label": "Anything else", "section": "Aspirations",
     "blurb": "Wedding, sabbatical, travel — speak it and Maya plans it."},
]


def _pct(x: float) -> str:
    return f"{x * 100:.0f} percent"


def _invalidate_plan_after_financial_edit(*, cashflow_changed: bool, investments_changed: bool) -> None:
    if cashflow_changed:
        STATE.cashflow_confirmed = False
    if investments_changed:
        STATE.investments_confirmed = False
    STATE.financial_snapshot_confirmed = False
    STATE.goals.clear()
    STATE.gap_result = None
    STATE.proposed_portfolios.clear()
    STATE.plan_pdf_path = None
    STATE.corpus_fraction_remaining = 1.0


def _has_any(args: dict, keys: tuple[str, ...]) -> bool:
    return any(args.get(key) is not None for key in keys)


def _mark_provider_observed() -> None:
    STATE.financial_snapshot_observed_at = _dt.datetime.now(_dt.UTC).isoformat()
    STATE.restored_financial_data = False


async def _maybe_emit_sip_cascade() -> None:
    """If the total SIP just changed from what we last showed the user,
    fire a cascade_diff message — the frontend renders it as a transient
    toast ('SIP updated · ₹50,000 → ₹52,000') so the user sees the knock-on
    of their revise immediately."""
    new_total = sum(g.required_sip or 0 for g in STATE.goals if g.funded)
    prev_total = STATE.last_published_total_sip
    STATE.last_published_total_sip = new_total
    if prev_total > 0 and new_total > 0 and abs(new_total - prev_total) >= 500:
        await ui_bus.emit({
            "type": "cascade_diff",
            "label": "Monthly SIP",
            "before": prev_total,
            "after": new_total,
        })


def _fund_review(holding: dict, risk_profile: str | None) -> dict:
    category = holding.get("category") or holding["type"]
    rating = int(holding.get("rating") or 0)
    category_suitable = category != "thematic"
    score_good = rating >= 3

    reasons = []
    if category_suitable:
        reasons.append(f"the {category} category fits a {risk_profile or 'balanced'} risk profile")
    else:
        reasons.append("thematic funds are too concentrated for this risk-profile-led plan")
    if score_good:
        reasons.append("the fund score is acceptable on consistency versus category average and downside protection")
    else:
        reasons.append("the fund score is weak on consistency versus category average or downside protection")

    return {
        "fund": holding["fund"],
        "category": category,
        "rating": rating,
        "category_suitable": category_suitable,
        "score_good": score_good,
        "status": "good" if category_suitable and score_good else "review",
        "reason": "; ".join(reasons),
    }


# ---------------------------------------------------------------- handlers

async def pull_mf_central(args: dict) -> dict:
    """Stage 3a: fetch the caller's mutual fund portfolio from MF Central (mocked)."""
    if not args.get("user_confirmed_consent"):
        return missing("MF Central consent",
                       "Explain why MF Central is needed, ask permission to trigger the OTP, and only call this after the user agrees.")
    await ui_bus.emit_artifact("mfc_consent", {
        "provider": "MF Central",
        "consent_context": args.get("consent_context"),
        "otp_provider": "MF Central",
    })
    otp = await consent.request_otp("MF Central")
    if str(otp).replace(" ", "") != "1234":
        return missing("the MF Central OTP",
                       "Tell the user the OTP did not match, then call pull_mf_central again so they can retry.")
    STATE.portfolio = portfolio_data.lookup(STATE.name or "client")
    _mark_provider_observed()
    p = STATE.portfolio
    for edit in args.get("holding_edits") or []:
        fund = (edit.get("fund") or "").strip().lower()
        holding = next((h for h in p["holdings"] if h["fund"].strip().lower() == fund), None)
        if not holding:
            continue
        if edit.get("current_value") is not None:
            holding["current_value"] = float(edit["current_value"])
        if edit.get("monthly_sip") is not None:
            holding["monthly_sip"] = float(edit["monthly_sip"])
    if args.get("holding_edits"):
        p["total_value"] = sum(h["current_value"] for h in p["holdings"])
        p["total_monthly_sip"] = sum(h["monthly_sip"] for h in p["holdings"])
        p["equity_value"] = sum(h["current_value"] for h in p["holdings"] if h["type"] == "equity")
        p["debt_value"] = sum(h["current_value"] for h in p["holdings"] if h["type"] == "debt")
    reviews = [_fund_review(h, STATE.risk_profile) for h in p["holdings"]]
    p["fund_reviews"] = reviews
    p["good_funds"] = [r["fund"] for r in reviews if r["status"] == "good"]
    p["underperformers"] = [r["fund"] for r in reviews if r["status"] != "good"]
    p["review_methodology"] = (
        "We judge each fund on two things: whether its category suits the user's "
        "risk profile, and a fund score based on consistency versus category average "
        "plus downside protection."
    )
    under = p["underperformers"]

    # MFC diagnosis insights — toned bullets surface in the card. Good: pick
    # the best-rated suitable fund. Bad: one bullet per underperformer with
    # explicit "Unsuitable category" / "Weak ranking" tags + LTCG-aware action.
    insights: list[dict] = []
    good_reviews = [r for r in reviews if r["status"] == "good"]
    if good_reviews:
        top_good = max(good_reviews, key=lambda r: r["rating"])
        insights.append({"tone": "good",
                         "text": f"Keep {top_good['fund']} — {top_good['category']} fits a "
                                 f"{STATE.risk_profile or 'balanced'} profile."})
    bad_with_sip = [
        h for h in p["holdings"]
        if h["fund"] in under and (h.get("monthly_sip") or 0) > 0
    ]
    for review in (r for r in reviews if r["status"] != "good"):
        holding = next(h for h in p["holdings"] if h["fund"] == review["fund"])
        tags = []
        if not review["category_suitable"]:
            tags.append("Unsuitable category")
        if not review["score_good"]:
            tags.append("Weak ranking")
        tag_text = " · ".join(tags) or "Needs review"
        sip = int(holding.get("monthly_sip") or 0)
        if sip > 0:
            action = f"Stop the ₹{sip:,}/mo SIP and exit gradually as units cross 1-year LTCG."
        else:
            action = "Exit gradually as units cross 1-year LTCG."
        insights.append({
            "tone": "bad",
            "text": f"{review['fund']} — {tag_text}. {action}",
        })

    await ui_bus.emit_artifact("mfc_review", {
        "total_funds": len(p["holdings"]),
        "total_value": p["total_value"],
        "total_monthly_sip": p["total_monthly_sip"],
        "underperformer_count": len(under),
        "good_count": len(p["good_funds"]),
        "insights": insights,
    })
    hint = (f"MF Central is back. Portfolio of {fm.round_to_500(p['total_value']) / 1e5:.0f} "
            f"lakhs across {len(p['holdings'])} funds with {p['total_monthly_sip']} rupees of "
            f"monthly SIPs. Explain that fund review uses category suitability for the "
            f"user's {STATE.risk_profile or 'risk'} profile plus a score based on consistency "
            f"versus category average and downside protection. ")
    if under:
        reasons = "; ".join(f"{r['fund']}: {r['reason']}" for r in reviews if r["status"] != "good")
        hint += (f"{len(under)} of {len(p['holdings'])} funds need review: "
                 f"{', '.join(under)}. Use these reasons briefly: {reasons}. ")
        if bad_with_sip:
            sip_actions = "; ".join(
                f"stop the {int(h['monthly_sip'])} rupee SIP into {h['fund']}"
                for h in bad_with_sip
            )
            hint += (f"For underperformers with a live SIP: {sip_actions}. Then tell the user "
                     f"to exit the existing units gradually as they cross one-year long-term "
                     f"capital gains, to avoid the short-term tax hit. ")
    else:
        hint += "No red flags — a clean portfolio."
    return tool_response(p, hint)


async def pull_account_aggregator(args: dict) -> dict:
    """Stage 3b: AA (Finvu) pull — income/expense/EMI plus other-asset snapshot."""
    if not STATE.portfolio:
        return missing("the MF Central pull",
                       "Call pull_mf_central first so existing SIPs feed into idle surplus.")
    correction_keys = (
        "monthly_income", "monthly_expenses", "monthly_emi", "investments",
        "household_expenses", "utilities", "entertainment", "epf", "nps", "stocks",
    )
    is_correction = bool(STATE.aa_assets) and _has_any(args, correction_keys)
    needs_fresh_consent = not STATE.aa_assets or (STATE.restored_financial_data and not is_correction)
    if needs_fresh_consent:
        if not args.get("user_confirmed_consent"):
            return missing("Account Aggregator consent",
                           "Explain what Account Aggregator is, what data it pulls and why it helps the plan. Ask permission to trigger the OTP, and only call this after the user agrees.")
        await ui_bus.emit_artifact("aa_consent", {
            "provider": "Finvu Account Aggregator",
            "consent_context": args.get("consent_context"),
            "otp_provider": "Finvu Account Aggregator",
        })
        otp = await consent.request_otp("Finvu Account Aggregator")
        if str(otp).replace(" ", "") != "1234":
            return missing("the Account Aggregator OTP",
                           "Tell the user the OTP did not match, then call pull_account_aggregator again so they can retry.")

    previous_assets = STATE.aa_assets or {}
    cashflow_changed = _has_any(args, (
        "monthly_income", "monthly_expenses", "monthly_emi", "investments",
        "household_expenses", "utilities", "entertainment",
    ))
    investments_changed = _has_any(args, ("epf", "nps", "stocks"))
    if is_correction:
        _invalidate_plan_after_financial_edit(
            cashflow_changed=cashflow_changed,
            investments_changed=investments_changed,
        )

    previous_breakdown = STATE.expense_breakdown or {}
    breakdown = {
        "investments": float(args.get("investments") if args.get("investments") is not None
                             else previous_breakdown.get("investments", 20_000)),
        "household_expenses": float(args.get("household_expenses") if args.get("household_expenses") is not None
                                    else previous_breakdown.get("household_expenses", 30_000)),
        "utilities": float(args.get("utilities") if args.get("utilities") is not None
                           else previous_breakdown.get("utilities", 8_000)),
        "entertainment": float(args.get("entertainment") if args.get("entertainment") is not None
                               else previous_breakdown.get("entertainment", 12_000)),
    }
    STATE.monthly_income = float(args.get("monthly_income") if args.get("monthly_income") is not None
                                 else STATE.monthly_income or 150_000)
    STATE.monthly_emi = float(args.get("monthly_emi") if args.get("monthly_emi") is not None
                              else STATE.monthly_emi or 25_000)
    non_emi_total = sum(breakdown.values())
    STATE.monthly_expenses = float(args.get("monthly_expenses") if args.get("monthly_expenses") is not None
                                   else non_emi_total)
    STATE.expense_breakdown = {**breakdown, "emis": STATE.monthly_emi}
    STATE.aa_assets = {
        "epf": float(args.get("epf") if args.get("epf") is not None
                     else previous_assets.get("epf", 450_000)),
        "nps": float(args.get("nps") if args.get("nps") is not None
                     else previous_assets.get("nps", 50_000)),
        "stocks": float(args.get("stocks") if args.get("stocks") is not None
                        else previous_assets.get("stocks", 500_000)),
    }
    existing_sip = STATE.portfolio["total_monthly_sip"]
    STATE.ratios = fm.financial_ratios(
        STATE.monthly_income, STATE.monthly_expenses, STATE.monthly_emi, existing_sip)
    _mark_provider_observed()
    r = STATE.ratios
    aa = STATE.aa_assets
    total_outflow = STATE.monthly_expenses + STATE.monthly_emi
    # Investments first: extend the existing-portfolio story with EPF, NPS,
    # stocks (+ any manual extras). Cashflow comes after, as a clean second
    # block — "complete one flow before the other."
    await ui_bus.emit_artifact("investments_review", {
        "mf_total": (STATE.portfolio or {}).get("total_value"),
        "mf_funds_count": len((STATE.portfolio or {}).get("holdings") or []),
        "aa_assets": aa,
        "additional_assets": list(STATE.additional_assets or []),
    })
    # Income snapshot also carries the live ratios so the card can render
    # savings-rate and DTI bars in-place — no separate ratios artifact needed.
    await ui_bus.emit_artifact("income_snapshot", {
        "monthly_income": STATE.monthly_income,
        "monthly_expenses": STATE.monthly_expenses,
        "monthly_emi": STATE.monthly_emi,
        "total_outflow": total_outflow,
        "expense_breakdown": STATE.expense_breakdown,
        "aa_assets": aa,
        "ratios": r,
    })
    if is_correction:
        changed = []
        if investments_changed:
            changed.append("investments")
        if cashflow_changed:
            changed.append("income and expenses")
        changed_text = " and ".join(changed) or "the snapshot"
        prefix = f"Updated {changed_text}. "
    else:
        prefix = "Finvu is back. "
    hint = (f"{prefix}Say you looked at the last three months of bank data. "
            f"Start with investments: alongside the MF Central portfolio, AA pulled "
            f"EPF {aa['epf']}, NPS {aa['nps']}, and stocks {aa['stocks']} rupees. "
            f"Ask the user to confirm these investments and whether to add anything else "
            f"like PPF, fixed deposits, gold, real estate or US/international stocks. If they correct "
            f"EPF, NPS or stocks, call pull_account_aggregator again with that correction; "
            f"do not ask for OTP again. Only after investments are confirmed, move to "
            f"income and expenses: average monthly income {STATE.monthly_income} rupees, "
            f"total outflow {total_outflow} rupees broken into investments "
            f"{breakdown['investments']}, monthly loan repayments {STATE.monthly_emi}, household "
            f"{breakdown['household_expenses']}, utilities {breakdown['utilities']}, "
            f"entertainment {breakdown['entertainment']}. Mention savings rate "
            f"{_pct(r['savings_rate'])} ({r['savings_band']}) and monthly loan repayments as a share of income "
            f"{_pct(r['debt_to_income'])} ({r['dti_band']}). Ask to confirm cash flow.")
    return tool_response({"ratios": r, "aa_assets": aa,
                          "monthly_income": STATE.monthly_income,
                          "monthly_expenses": STATE.monthly_expenses,
                          "monthly_emi": STATE.monthly_emi,
                          "expense_breakdown": STATE.expense_breakdown}, hint)


async def add_family(args: dict) -> dict:
    """Stage 2: capture spouse age, children (with ages), and other dependents."""
    spouse_age = args.get("spouse_age")
    children = args.get("children") or []  # list of {"age": int}
    dependents_count = int(args.get("dependents_count") or 0)
    STATE.family = {
        "spouse_age": int(spouse_age) if spouse_age is not None else None,
        "children": [{"age": int(c["age"])} for c in children if "age" in c],
        "dependents_count": dependents_count,
    }
    parts = []
    if STATE.family["spouse_age"] is not None:
        parts.append(f"spouse aged {STATE.family['spouse_age']}")
    if STATE.family["children"]:
        ages = ", ".join(str(c["age"]) for c in STATE.family["children"])
        parts.append(f"{len(STATE.family['children'])} child(ren) aged {ages}")
    if dependents_count:
        parts.append(f"{dependents_count} other dependent(s)")
    summary = "; ".join(parts) or "no immediate dependents"
    await ui_bus.emit_artifact("family_recap", {
        "family": STATE.family,
        "summary": summary,
    })
    hint = (f"Family captured — {summary}. Keep this in mind when goals come up: a young child "
            f"suggests an education goal in 18-minus-age years; the caller's own age plus "
            f"retirement age suggests a retirement goal.")
    return tool_response(STATE.family, hint)


async def add_manual_asset(args: dict) -> dict:
    """Stage 3c (optional): voice-added extras like PPF, FDs, gold, real estate."""
    STATE.investments_confirmed = False
    STATE.financial_snapshot_confirmed = False
    STATE.goals.clear()
    STATE.gap_result = None
    STATE.proposed_portfolios.clear()
    STATE.plan_pdf_path = None
    STATE.corpus_fraction_remaining = 1.0
    entry = {
        "name": args["name"],
        "asset_type": args.get("asset_type") or "other",
        "value": float(args["value"]),
    }
    STATE.additional_assets.append(entry)
    total = sum(a["value"] for a in STATE.additional_assets)
    # Re-emit investments_review so the on-screen card stays mounted and shows
    # the new manual asset live. The wrapper's post-tool state event will then
    # re-anchor the refreshed card instead of advancing to the queued cashflow.
    await ui_bus.emit_artifact("investments_review", {
        "mf_total": (STATE.portfolio or {}).get("total_value"),
        "mf_funds_count": len((STATE.portfolio or {}).get("holdings") or []),
        "aa_assets": STATE.aa_assets,
        "additional_assets": list(STATE.additional_assets),
    })
    hint = (f"Added {entry['name']} worth {entry['value']:.0f} rupees. "
            f"Total manual extras now {total:.0f} rupees across "
            f"{len(STATE.additional_assets)} item(s). Ask if there is anything else.")
    return tool_response({"added": entry, "additional_assets": STATE.additional_assets}, hint)


async def confirm_financial_snapshot(args: dict) -> dict:
    """Gate before goals: user accepted AA data and answered manual additions."""
    if not STATE.aa_assets or not STATE.ratios:
        return missing("the Account Aggregator pull",
                       "Call pull_account_aggregator first so there is a financial snapshot to confirm.")
    cashflow_ok = bool(args.get("user_confirmed_cashflow") or args.get("user_confirmed_financial_data"))
    investments_ok = bool(args.get("user_confirmed_investments") or args.get("user_confirmed_financial_data"))
    if cashflow_ok:
        STATE.cashflow_confirmed = True
    if investments_ok and args.get("user_answered_additional_assets"):
        STATE.investments_confirmed = True
    # Investments first — one full flow before the cashflow flow begins.
    if not args.get("user_answered_additional_assets") and investments_ok:
        return missing("the additional-investments answer",
                       "Ask whether they want to add PPF, fixed deposits, gold, real estate, US stocks or international stocks before cashflow.")
    if not STATE.investments_confirmed:
        return missing("explicit confirmation of investments",
                       "Show MF Central holdings plus Finvu EPF, NPS and stocks as a list. Ask for edits or additions, then confirm investments before moving to income and expenses.")
    if not STATE.cashflow_confirmed:
        return missing("explicit confirmation of income and expenses",
                       "Show the AA income and expense methodology with savings rate and monthly loan repayments as a share of income, ask for edits, and get the user's confirmation before goals.")

    STATE.financial_snapshot_confirmed = True
    # Surface the goal-types menu the moment goals are unlocked, so the user
    # has a visual anchor while Maya frames the goals stage.
    await ui_bus.emit_artifact("goal_types_picker", {
        "types": GOAL_TYPES,
        "recommended": ["emergency", "retirement"],
    })
    hint = ("Financial snapshot confirmed. The user accepted the investment holdings, "
            "answered the additional-investments check, and confirmed cash flow. The "
            "goal-types picker is now on screen — frame goals briefly (safety, "
            "long-term independence, aspirations) and start with the emergency fund.")
    return tool_response({
        "cashflow_confirmed": STATE.cashflow_confirmed,
        "investments_confirmed": STATE.investments_confirmed,
        "financial_snapshot_confirmed": True,
        "additional_assets": STATE.additional_assets,
    }, hint)


async def confirm_resume(args: dict) -> dict:
    """Release the returning-user gate after the user answers the resume question."""
    if not STATE.is_returning_session:
        return missing("a returning session", "Continue the normal first-call flow.")
    if not args.get("user_confirmed"):
        return missing("the user's resume choice",
                       "Ask whether they want to continue the saved plan or change anything.")
    STATE.resume_confirmed = True
    return tool_response(
        {"resume_confirmed": True},
        "Resume confirmed. Acknowledge their choice, then follow next_step from the restored state.",
    )


async def choose_experience(args: dict) -> dict:
    """Choose the preloaded simulator call's traditional or what-if path."""
    if not STATE.is_simulator_session:
        return missing("the simulator entry experience",
                       "Continue the normal planning flow.")
    raw_choice = str(args.get("choice") or "").strip().lower()
    if any(word in raw_choice for word in ("simulator", "simulate", "scenario", "decision")):
        choice = "simulator"
    elif any(word in raw_choice for word in ("traditional", "goal", "planning", "plan")):
        choice = "traditional"
    else:
        return missing("a clear simulator choice",
                       "Ask whether they want traditional goal planning or the financial decision simulator.")

    STATE.simulator_choice = choice
    STATE.last_simulation = None
    if choice == "traditional":
        await ui_bus.emit_artifact("goal_types_picker", {
            "types": GOAL_TYPES,
            "recommended": ["emergency", "retirement"],
        })
        hint = (
            "Traditional planning selected. The full financial profile is already confirmed "
            "and the goal-types card is on screen. Ask which goal they want to plan first."
        )
    else:
        await ui_bus.emit_artifact("simulator_menu", {
            "scenarios": [
                {
                    "key": "career_break",
                    "label": "Take a career break",
                    "description": "See the runway and reserve you would need.",
                },
                {
                    "key": "home_timing",
                    "label": "Move a home purchase",
                    "description": "Compare the monthly investment at two timelines.",
                },
                {
                    "key": "starting_family",
                    "label": "Start a family",
                    "description": "See how childcare and education reshape surplus.",
                },
            ],
        })
        hint = (
            "Decision simulator selected. Offer three choices: career break, moving a home "
            "purchase earlier or later, or starting a family. Ask which one they want to test."
        )
    return tool_response({"choice": choice}, hint)


def _simulator_baseline() -> dict:
    breakdown = STATE.expense_breakdown or {}
    essential_outflow = (
        float(breakdown.get("household_expenses") or 0)
        + float(breakdown.get("utilities") or 0)
        + float(breakdown.get("entertainment") or 0)
        + float(STATE.monthly_emi or 0)
    )
    return {
        "monthly_income": float(STATE.monthly_income or 0),
        "essential_outflow": essential_outflow,
        "idle_surplus": float((STATE.ratios or {}).get("idle_surplus") or 0),
    }


async def simulate_life_event(args: dict) -> dict:
    """Run one bounded, deterministic what-if against the preloaded profile."""
    if not STATE.is_simulator_session or STATE.simulator_choice != "simulator":
        return missing("the financial decision simulator",
                       "Use the /simulator entry and choose the decision simulator first.")
    if not STATE.financial_snapshot_confirmed or not STATE.portfolio or not STATE.ratios:
        return missing("a confirmed financial profile",
                       "Load the simulator profile before running a scenario.")

    event_type = str(args.get("event_type") or "").strip().lower()
    baseline = _simulator_baseline()
    expected_return = fm.EXPECTED_RETURN[STATE.risk_profile or "balanced"]
    comparisons: list[dict] = []

    if event_type == "career_break":
        if any(args.get(field) is None for field in (
            "duration_months",
            "starts_in_months",
            "income_reduction_percent",
        )):
            return missing("career-break timing",
                           "Ask how many months the break lasts, how many months from now it starts, and whether income stops fully or falls by a stated percentage.")
        duration = int(args["duration_months"])
        starts_in = int(args["starts_in_months"])
        reduction_pct = float(args["income_reduction_percent"])
        if duration < 1 or starts_in < 0 or not 0 <= reduction_pct <= 100:
            return missing("valid career-break inputs",
                           "Use a positive duration, a non-negative start time, and an income reduction from zero to one hundred percent.")

        debt_fund_cushion = float(STATE.portfolio.get("debt_value") or 0)
        scenario = fm.simulate_career_break(
            monthly_income=baseline["monthly_income"],
            essential_outflow=baseline["essential_outflow"],
            idle_surplus=baseline["idle_surplus"],
            debt_fund_cushion=debt_fund_cushion,
            duration_months=duration,
            starts_in_months=starts_in,
            income_reduction_percent=reduction_pct,
        )
        status = "viable" if scenario["goal_surplus_after_build"] >= 0 else "needs_adjustment"
        title = "Career break"
        headline = (
            "Your current cushion can absorb this break."
            if scenario["additional_reserve"] <= 0
            else "This break needs a larger cash runway first."
        )
        recommendation = (
            f"Build an additional reserve of {scenario['additional_reserve']} rupees before the "
            f"break. That requires about {scenario['monthly_reserve_build']} rupees a "
            f"month for {starts_in} months."
            if scenario["additional_reserve"] > 0
            else f"The debt-fund cushion covers the estimated {scenario['reserve_required']} rupee shortfall."
        )
        comparisons = [
            {
                "label": "Monthly income",
                "before": baseline["monthly_income"],
                "after": scenario["income_during"],
                "format": "inr",
            },
            {
                "label": "Monthly cash position",
                "before": scenario["cash_position_before"],
                "after": scenario["cash_position_during"],
                "format": "inr",
            },
            {
                "label": "Reserve required",
                "before": 0,
                "after": scenario["reserve_required"],
                "format": "inr",
            },
        ]
        scenario = {
            **scenario,
            "duration_months": duration,
            "starts_in_months": starts_in,
            "income_reduction_percent": reduction_pct,
        }
        narration = (
            f"For a {duration}-month break starting in {starts_in} months, income falls by "
            f"{reduction_pct:.0f} percent and the estimated reserve is "
            f"{scenario['reserve_required']} rupees. {recommendation}"
        )

    elif event_type == "home_timing":
        required = ("goal_amount_today", "current_horizon_years", "proposed_horizon_years")
        if any(args.get(field) is None for field in required):
            return missing("the home scenario amount and two timelines",
                           "Ask the home's cost today, the current purchase timeline, and the proposed timeline.")
        amount_today = float(args["goal_amount_today"])
        current_years = int(args["current_horizon_years"])
        proposed_years = int(args["proposed_horizon_years"])
        if amount_today <= 0 or current_years < 1 or proposed_years < 1:
            return missing("valid home scenario inputs",
                           "Use a positive home cost and timelines at least one year away.")

        scenario = fm.simulate_home_timing(
            amount_today=amount_today,
            current_horizon_years=current_years,
            proposed_horizon_years=proposed_years,
            portfolio_value=float(STATE.portfolio["total_value"]),
            portfolio_monthly_sip=float(STATE.portfolio["total_monthly_sip"]),
            equity_value=float(STATE.portfolio.get("equity_value") or 0),
            debt_value=float(STATE.portfolio.get("debt_value") or 0),
            expected_return=expected_return,
            idle_surplus=baseline["idle_surplus"],
        )
        current = scenario["current"]
        proposed = scenario["proposed"]
        sip_delta = scenario["sip_delta"]
        status = (
            "viable"
            if proposed["affordability"] == "comfortable"
            else "needs_adjustment"
        )
        title = "Home purchase timing"
        headline = (
            "The new timeline lowers the monthly pressure."
            if sip_delta < 0
            else "The new timeline increases the monthly commitment."
        )
        if sip_delta > 0:
            recommendation = (
                f"The proposed timeline needs {sip_delta} rupees more each month. "
                "Keep the later date, lower the home budget, or redirect another goal."
            )
        elif sip_delta < 0:
            recommendation = (
                f"The proposed timeline releases {abs(sip_delta)} rupees of monthly capacity."
            )
        else:
            recommendation = "Both timelines need roughly the same monthly investment."
        comparisons = [
            {
                "label": "Purchase timeline",
                "before": current_years,
                "after": proposed_years,
                "format": "years",
            },
            {
                "label": "Future home cost",
                "before": current["inflated_target"],
                "after": proposed["inflated_target"],
                "format": "inr",
            },
            {
                "label": "Required monthly SIP",
                "before": current["required_sip"],
                "after": proposed["required_sip"],
                "format": "inr",
            },
        ]
        narration = (
            f"At {current_years} years, the home needs about {current['required_sip']} rupees "
            f"a month. At {proposed_years} years, it needs about "
            f"{proposed['required_sip']} rupees. {recommendation}"
        )

    elif event_type == "starting_family":
        required = ("child_arrival_years", "added_monthly_cost", "education_cost_today")
        if any(args.get(field) is None for field in required):
            return missing("the family scenario assumptions",
                           "Ask when the child may arrive, the added monthly family cost, and today's education cost to plan for.")
        arrival_years = int(args["child_arrival_years"])
        added_monthly_cost = float(args["added_monthly_cost"])
        education_today = float(args["education_cost_today"])
        if arrival_years < 0 or added_monthly_cost < 0 or education_today <= 0:
            return missing("valid family scenario inputs",
                           "Use a non-negative arrival time and monthly cost, plus a positive education amount.")

        scenario = fm.simulate_starting_family(
            child_arrival_years=arrival_years,
            added_monthly_cost=added_monthly_cost,
            education_cost_today=education_today,
            expected_return=expected_return,
            idle_surplus=baseline["idle_surplus"],
        )
        status = "viable" if scenario["affordability"] == "comfortable" else "needs_adjustment"
        title = "Starting a family"
        headline = (
            "The family plan fits within the current surplus."
            if scenario["remaining_surplus"] >= 0
            else "The family plan needs a trade-off."
        )
        recommendation = (
            f"Set aside {scenario['added_monthly_cost']} rupees for added monthly costs "
            f"and {scenario['education_sip']} rupees for education. That leaves "
            f"{scenario['remaining_surplus']} rupees of monthly goal capacity."
        )
        comparisons = [
            {
                "label": "Monthly goal capacity",
                "before": round(baseline["idle_surplus"]),
                "after": scenario["remaining_surplus"],
                "format": "inr",
            },
            {
                "label": "Added family cost",
                "before": 0,
                "after": scenario["added_monthly_cost"],
                "format": "inr",
            },
            {
                "label": "Education SIP",
                "before": 0,
                "after": scenario["education_sip"],
                "format": "inr",
            },
        ]
        narration = (
            f"Starting a family adds {scenario['added_monthly_cost']} rupees a month. "
            f"An education target of {scenario['education_target']} rupees needs about "
            f"{scenario['education_sip']} rupees a month. {recommendation}"
        )

    else:
        return missing("a supported life event",
                       "Choose career_break, home_timing, or starting_family.")

    result = {
        "event_type": event_type,
        "title": title,
        "headline": headline,
        "status": status,
        "baseline": baseline,
        "scenario": scenario,
        "comparisons": comparisons,
        "recommendation": recommendation,
    }
    STATE.last_simulation = result
    await ui_bus.emit_artifact("scenario_comparison", result)
    return tool_response(result, narration)


def _emergency_goals() -> list[dict]:
    return [
        {
            "name": goal.name,
            "required_sip": goal.required_sip,
            "horizon_years": goal.horizon_years,
        }
        for goal in STATE.goals
    ]


def _protected_emergency_goals(raw_names: list | None) -> set[str]:
    known = {goal.name.lower(): goal.name for goal in STATE.goals}
    protected = set()
    for raw_name in raw_names or []:
        name = str(raw_name).strip().lower()
        if name in known:
            protected.add(name)
    return protected


def _emergency_emotional_context(description: str, emergency_type: str) -> dict:
    text = description.lower()
    if any(word in text for word in (
        "baby", "newborn", "child was born", "child is born", "had a kid",
        "had a child", "became a father", "became a mother",
    )):
        return {
            "tone": "celebratory",
            "supportive_opening": (
                "Congratulations, Rakshit. That is wonderful news. Let us make the money "
                "side feel calm and manageable, so you can focus on your family."
            ),
        }
    if any(word in text for word in (
        "lost my job", "laid off", "fired", "job loss", "unemployed",
        "income stopped",
    )):
        return {
            "tone": "job_loss",
            "supportive_opening": (
                "I am really sorry, Rakshit. You do not have to solve everything today. "
                "We will work through this together, one decision at a time."
            ),
        }
    if any(word in text for word in (
        "hospital", "medical", "surgery", "treatment", "diagnosis", "illness",
    )):
        return {
            "tone": "medical",
            "supportive_opening": (
                "I am sorry you are dealing with this, Rakshit. Let us make the money "
                "side one less thing to carry and protect the decisions that cannot wait."
            ),
        }
    if any(word in text for word in (
        "death", "passed away", "bereavement", "funeral",
    )):
        return {
            "tone": "bereavement",
            "supportive_opening": (
                "I am very sorry, Rakshit. We can move slowly and handle only the "
                "financial decisions that truly need attention right now."
            ),
        }
    return {
        "tone": "steady",
        "supportive_opening": (
            "I hear you, Rakshit. Let us slow this down and turn it into a few clear "
            "decisions, so the whole plan does not feel like it is moving at once."
        ),
    }


def _emergency_guidance(
    *,
    emergency_type: str,
    scenario: dict,
    emotional_tone: str,
) -> list[dict]:
    if emergency_type == "new_child" or emotional_tone == "celebratory":
        return [
            {
                "label": "Protect the family first",
                "detail": "Review health cover, life cover, and nominees before adding a new investment.",
            },
            {
                "label": "Reset the monthly rhythm",
                "detail": "Understand the new childcare cash flow while keeping the emergency buffer intact.",
            },
            {
                "label": "Then fund the future",
                "detail": "Shape the education goal after the near-term family costs feel stable.",
            },
        ]
    if emergency_type == "income_shock":
        return [
            {
                "label": "Protect what keeps life running",
                "detail": (
                    f"Ring-fence {scenario['essential_outflow']} rupees a month for household "
                    "needs, utilities, and monthly loan repayments."
                ),
            },
            {
                "label": "Make goals flexible, not abandoned",
                "detail": (
                    f"Temporarily release {scenario['monthly_freed']} rupees a month from "
                    "flexible goals while preserving any goal you mark non-negotiable."
                ),
            },
            {
                "label": "Use the reserve with checkpoints",
                "detail": (
                    f"The current plan has {scenario['runway_months']} months of runway at "
                    "this cash burn. Review the plan every thirty days, not every day."
                ),
            },
        ]
    return [
        {
            "label": "Handle the immediate need",
            "detail": (
                f"Use up to {scenario['reserve_used']} rupees from the emergency reserve "
                "without disturbing long-term holdings first."
            ),
        },
        {
            "label": "Choose what stays protected",
            "detail": (
                f"Temporarily release {scenario['monthly_freed']} rupees a month only from "
                "goals you are comfortable delaying."
            ),
        },
        {
            "label": "Rebuild before accelerating",
            "detail": (
                f"Restore about {scenario['monthly_rebuild_needed']} rupees a month to the "
                "reserve, then restart paused goals."
            ),
        },
    ]


async def analyze_financial_emergency(args: dict) -> dict:
    """Build a reversible whole-plan proposal for an explicit emergency."""
    if not STATE.is_emergency_session:
        return missing(
            "emergency mode",
            "Use the Emergency button on the simulator entry screen.",
        )
    if not STATE.goals or not STATE.financial_snapshot_confirmed:
        return missing(
            "the completed demo plan",
            "Reload emergency mode so the completed plan is available.",
        )

    emergency_type = str(args.get("emergency_type") or "").strip().lower()
    description = str(args.get("description") or "").strip()
    emotional_context = _emergency_emotional_context(description, emergency_type)
    protected = _protected_emergency_goals(args.get("protected_goal_names"))
    emergency_goal = get_goal("Emergency fund")
    liquid_reserve = float(
        (emergency_goal.projected_from_existing if emergency_goal else 0)
        or (emergency_goal.target_amount_today if emergency_goal else 0)
    )
    baseline = _simulator_baseline()
    goals = _emergency_goals()
    total_sip_before = round(sum(goal["required_sip"] or 0 for goal in goals))

    if emergency_type == "new_child":
        scenario = {
            "status": "orientation",
            "goal_changes": [],
        }
        result = {
            "emergency_type": emergency_type,
            "description": description,
            "title": "A new chapter",
            "headline": "First protect the family, then reshape the plan.",
            "status": "viable",
            "comparisons": [],
            "recommendation": (
                "Start with whichever feels most urgent: monthly cash flow, financial "
                "protection, or the child's longer-term goal."
            ),
            "goal_changes": [],
            "scenario": scenario,
            "protected_goal_names": [],
            "supportive_opening": emotional_context["supportive_opening"],
            "emotional_tone": emotional_context["tone"],
            "guidance_steps": _emergency_guidance(
                emergency_type=emergency_type,
                scenario=scenario,
                emotional_tone=emotional_context["tone"],
            ),
            "proposal_ready": False,
            "applied": False,
        }
        STATE.pending_emergency_plan = result
        STATE.emergency_plan_applied = False
        await ui_bus.emit_artifact("emergency_shockwave", result)
        return tool_response(
            result,
            f"{emotional_context['supportive_opening']} Explain protection, near-term cash "
            "flow, and the child's future as the three decisions. Then ask which one feels "
            "most urgent. Do not ask for an amount yet.",
        )

    if emergency_type == "income_shock":
        if args.get("monthly_income_after") is None or args.get("duration_months") is None:
            return missing(
                "the new monthly income and duration",
                "Ask one question at a time: what monthly income remains, then how many months it may last.",
            )
        monthly_income_after = float(args["monthly_income_after"])
        duration_months = int(args["duration_months"])
        if monthly_income_after < 0 or duration_months < 1:
            return missing(
                "valid income-shock inputs",
                "Use a non-negative monthly income and a duration of at least one month.",
            )
        scenario = fm.simulate_income_emergency(
            monthly_income_after=monthly_income_after,
            duration_months=duration_months,
            essential_outflow=baseline["essential_outflow"],
            liquid_reserve=liquid_reserve,
            goals=goals,
            protected_goal_names=protected,
        )
        runway_plan = fm.plan_runway_extensions(
            liquid_cash=liquid_reserve,
            monthly_draw=scenario["monthly_draw"],
            holdings=STATE.portfolio.get("holdings") or [],
        )
        scenario["runway_plan"] = runway_plan
        total_sip_after = round(sum(
            item["after_sip"] for item in scenario["goal_changes"]
        ))
        headline = (
            "Your safety net can carry this income interruption."
            if scenario["status"] == "viable"
            else "The current safety net does not cover the full interruption."
        )
        recommendation = (
            f"Pause {scenario['monthly_freed']} rupees of monthly goal investments for "
            f"{duration_months} months. The emergency fund covers "
            f"{scenario['runway_months']} months at the revised cash burn."
            if scenario["status"] == "viable"
            else f"Even after pausing goals, the plan is short by "
                 f"{scenario['reserve_gap']} rupees. Reduce spending, shorten the break, "
                 "or add temporary income before accepting."
        )
        comparisons = [
            {
                "label": "Monthly income",
                "before": round(STATE.monthly_income or 0),
                "after": scenario["monthly_income_after"],
                "format": "inr",
            },
            {
                "label": "Goal investments",
                "before": total_sip_before,
                "after": total_sip_after,
                "format": "inr",
            },
            {
                "label": "Emergency runway",
                "before": round(liquid_reserve / baseline["essential_outflow"], 1),
                "after": scenario["runway_months"] or 0,
                "format": "months",
            },
        ]
        title = "Income interruption"
        narration = (
            f"I have reworked the whole plan for {duration_months} months. "
            f"It frees {scenario['monthly_freed']} rupees a month and leaves "
            f"{scenario['reserve_gap']} rupees uncovered. {recommendation}"
        )
        runway_options = runway_plan["options"]
        if runway_options and runway_plan["current_runway_months"] is not None:
            option_summaries = []
            for option in runway_options:
                withdrawals = ", ".join(
                    f"{item['fund']} for {item['amount']} rupees"
                    for item in option["withdrawals"]
                )
                option_summaries.append(
                    f"{option['target_months']} months needs "
                    f"{option['additional_required']} rupees more"
                    + (f", from {withdrawals}" if withdrawals else "")
                )
            narration = (
                f"{narration} You currently have {runway_plan['current_liquid_cash']} "
                f"rupees liquid, covering {runway_plan['current_runway_months']} months. "
                f"{'. '.join(option_summaries)}. I would build twelve months first and "
                "review the position every thirty days."
            )
        elif runway_plan["current_runway_months"] is None:
            narration = (
                f"{narration} The revised income covers the monthly cash burn, so the "
                "liquid reserve does not need to fund this period."
            )

    elif emergency_type == "urgent_cost":
        if args.get("one_time_cost") is None or args.get("recovery_months") is None:
            return missing(
                "the urgent amount and recovery period",
                "Ask one question at a time: how much is needed now, then over how many months the reserve should be rebuilt.",
            )
        one_time_cost = float(args["one_time_cost"])
        recovery_months = int(args["recovery_months"])
        if one_time_cost <= 0 or recovery_months < 1:
            return missing(
                "valid urgent-cost inputs",
                "Use a positive one-time cost and a recovery period of at least one month.",
            )
        scenario = fm.simulate_urgent_cost(
            one_time_cost=one_time_cost,
            recovery_months=recovery_months,
            liquid_reserve=liquid_reserve,
            idle_surplus=baseline["idle_surplus"],
            goals=goals,
            protected_goal_names=protected,
        )
        total_sip_after = round(sum(
            item["after_sip"] for item in scenario["goal_changes"]
        ))
        headline = (
            "The urgent cost can be absorbed without breaking the plan."
            if scenario["status"] == "viable"
            else "This cost needs one more trade-off before it is safe."
        )
        recommendation = (
            f"Use {scenario['reserve_used']} rupees from the emergency fund, pause "
            f"{scenario['monthly_freed']} rupees of monthly goal investments, and rebuild "
            f"{scenario['monthly_rebuild_needed']} rupees a month for "
            f"{recovery_months} months."
            if scenario["status"] == "viable"
            else f"The immediate funding gap is {scenario['immediate_gap']} rupees. "
                 "Lower the cost, extend recovery, or identify another source before accepting."
        )
        comparisons = [
            {
                "label": "Emergency reserve",
                "before": liquid_reserve,
                "after": scenario["reserve_after"],
                "format": "inr",
            },
            {
                "label": "Goal investments",
                "before": total_sip_before,
                "after": total_sip_after,
                "format": "inr",
            },
            {
                "label": "Monthly reserve rebuild",
                "before": 0,
                "after": scenario["monthly_rebuild_needed"],
                "format": "inr",
            },
        ]
        title = "Urgent expense"
        narration = (
            f"I have reworked the whole plan around the {one_time_cost} rupee need. "
            f"It frees {scenario['monthly_freed']} rupees a month. {recommendation}"
        )
    else:
        return missing(
            "a supported emergency type",
            "Use income_shock for an income interruption, urgent_cost for money needed now, or new_child for a recent birth.",
        )

    guidance_steps = _emergency_guidance(
        emergency_type=emergency_type,
        scenario=scenario,
        emotional_tone=emotional_context["tone"],
    )
    result = {
        "emergency_type": emergency_type,
        "description": description,
        "title": title,
        "headline": headline,
        "status": scenario["status"],
        "comparisons": comparisons,
        "recommendation": recommendation,
        "goal_changes": scenario["goal_changes"],
        "scenario": scenario,
        "runway_plan": scenario.get("runway_plan"),
        "recommended_runway_months": (
            12
            if emergency_type == "income_shock"
            and (scenario.get("runway_plan") or {}).get("current_runway_months") is not None
            and (scenario.get("runway_plan") or {})["current_runway_months"] < 12
            else None
        ),
        "protected_goal_names": sorted(protected),
        "supportive_opening": emotional_context["supportive_opening"],
        "emotional_tone": emotional_context["tone"],
        "guidance_steps": guidance_steps,
        "proposal_ready": True,
        "applied": False,
    }
    STATE.pending_emergency_plan = result
    STATE.emergency_plan_applied = False
    await ui_bus.emit_artifact("emergency_shockwave", result)
    return tool_response(
        result,
        f"{emotional_context['supportive_opening']} Then explain the three guidance steps "
        f"conversationally. After that, summarize the plan impact: {narration}",
    )


async def commit_emergency_plan(args: dict) -> dict:
    """Apply or undo the most recent emergency proposal."""
    if not STATE.is_emergency_session:
        return missing(
            "emergency mode",
            "Use the Emergency button on the simulator entry screen.",
        )
    action = str(args.get("action") or "").strip().lower()
    if action == "undo":
        if not STATE.emergency_original_goals:
            return missing(
                "an applied emergency plan",
                "There is nothing to undo. Continue discussing the current proposal.",
            )
        originals = {item["name"]: item for item in STATE.emergency_original_goals}
        for goal in STATE.goals:
            original = originals.get(goal.name)
            if original:
                goal.__dict__.update(original)
        STATE.proposed_portfolios = json.loads(
            json.dumps(STATE.emergency_original_portfolios)
        )
        STATE.last_published_total_sip = sum(
            goal.required_sip or 0 for goal in STATE.goals if goal.funded
        )
        STATE.pending_emergency_plan = None
        STATE.emergency_original_goals = []
        STATE.emergency_original_portfolios = {}
        STATE.emergency_plan_applied = False
        restored = {
            "title": "Original plan restored",
            "headline": "The emergency changes have been undone.",
            "status": "viable",
            "comparisons": [],
            "goal_changes": [],
            "recommendation": "Your home and education investments are back to their original schedule.",
            "applied": False,
            "undone": True,
        }
        await ui_bus.emit_artifact("emergency_shockwave", restored)
        return tool_response(
            restored,
            "The original plan is restored. Confirm that the home and education investments are back on schedule.",
        )

    if action != "accept":
        return missing(
            "the user's explicit decision",
            "Ask whether they want to accept the proposal or keep adjusting it.",
        )
    proposal = STATE.pending_emergency_plan
    if not proposal:
        return missing(
            "an emergency proposal",
            "Call analyze_financial_emergency before asking the user to accept.",
        )
    if not proposal.get("proposal_ready", True):
        return missing(
            "a calculated emergency proposal",
            "This is still the orientation stage. Ask which area the user wants to work through before requesting acceptance.",
        )
    if proposal["status"] != "viable":
        return missing(
            "a viable emergency proposal",
            "The proposal still has a shortfall. Adjust the amount, duration, or protected goals first.",
        )

    if not STATE.emergency_original_goals:
        STATE.emergency_original_goals = [
            dict(goal.__dict__) for goal in STATE.goals
        ]
        STATE.emergency_original_portfolios = json.loads(
            json.dumps(STATE.proposed_portfolios)
        )

    changes = {item["name"]: item for item in proposal["goal_changes"]}
    for goal in STATE.goals:
        change = changes.get(goal.name)
        if not change:
            continue
        goal.required_sip = float(change["after_sip"])
        new_horizon = int(change["after_horizon_years"])
        if new_horizon != goal.horizon_years:
            goal.horizon_years = new_horizon
            goal.inflated_target = round(
                fm.inflate(
                    goal.target_amount_today,
                    goal.horizon_years,
                    fm.inflation_for_goal(goal.name),
                )
            )
        if (goal.required_sip or 0) <= 0:
            STATE.proposed_portfolios.pop(goal.name, None)
        else:
            bucket = fm.horizon_bucket(goal.horizon_years)
            STATE.proposed_portfolios[goal.name] = {
                "goal": goal.name,
                "horizon_bucket": bucket,
                "horizon_years": goal.horizon_years,
                "monthly_sip": goal.required_sip,
                "phases": fm.build_phases(
                    bucket,
                    goal.horizon_years,
                    goal.required_sip,
                ),
            }
    STATE.last_published_total_sip = sum(
        goal.required_sip or 0 for goal in STATE.goals if goal.funded
    )
    STATE.plan_pdf_path = None
    STATE.emergency_plan_applied = True
    applied = {**proposal, "applied": True}
    STATE.pending_emergency_plan = applied
    await ui_bus.emit_artifact("emergency_shockwave", applied)
    return tool_response(
        applied,
        "The emergency plan is active. Confirm the immediate reserve action, which goal investments are paused, and that the user can ask to undo it.",
    )


async def assess_risk_profile(args: dict) -> dict:
    answers = args["answers"]
    if not answers or len(answers) < 2:
        return missing("at least 2 risk scenario answers",
                       "Ask another behavioral scenario question first.")
    STATE.risk_answers = answers
    result = fm.risk_profile_from_answers(answers)
    STATE.risk_profile = result["risk_profile"]
    await ui_bus.emit_artifact("risk_reveal", result)
    hint = (f"The user comes out {result['risk_profile']}: roughly "
            f"{result['equity_band'] * 100:.0f} percent equity suits them, and we'll plan "
            f"with {result['expected_return'] * 100:.0f} percent expected returns.")
    return tool_response(result, hint)


async def add_goal(args: dict) -> dict:
    if len(STATE.goals) >= 4:
        return missing("room for another goal",
                       "Four goals are already captured — that's the maximum. Move on.")
    name = args["name"]
    horizon = int(args.get("horizon_years") or 1)
    if horizon < 1:
        return missing("a valid horizon", "Ask for a target year at least 1 year away.")
    if args.get("target_amount_today") is None:
        if "emergency" not in name.lower():
            return missing("a goal amount",
                           "Ask for today's cost for this goal, unless it is the emergency fund.")
        if STATE.monthly_expenses is None or STATE.monthly_emi is None:
            return missing("the monthly expense outflow",
                           "Call pull_account_aggregator first so the emergency fund can use six months of expenses.")
        amount = (STATE.monthly_expenses + STATE.monthly_emi) * 6
    else:
        amount = float(args["target_amount_today"])
    inflation = 0.0 if "emergency" in name.lower() else fm.inflation_for_goal(name)
    goal = Goal(
        name=name,
        target_amount_today=amount,
        horizon_years=horizon,
        priority=int(args["priority"]),
        inflated_target=round(fm.inflate(amount, horizon, inflation)),
    )
    STATE.goals.append(goal)
    # Emit the inflation curve immediately so the user has a visual while we
    # discuss the just-captured target. compute_gap_and_sip will re-emit the
    # same kind later with SIP info attached (same-kind replace in the queue).
    if "emergency" not in name.lower():
        target_year = _dt.datetime.now().year + horizon
        await ui_bus.emit_artifact("inflation_curve", {
            "goal": goal.name,
            "target_amount_today": goal.target_amount_today,
            "inflated_target": goal.inflated_target,
            "horizon_years": horizon,
            "inflation_used": inflation,
            "target_year": target_year,
        })
    if "emergency" in name.lower():
        hint = (f"Emergency fund captured at {amount:.0f} rupees — six months of the "
                f"user's confirmed monthly outflow. Explain it as the first safety goal "
                f"before long-term investing.")
    else:
        hint = (f"Captured. With {inflation * 100:.0f} percent inflation, today's "
                f"{amount / 1e5:.0f} lakh becomes about {goal.inflated_target / 1e5:.0f} lakhs "
                f"in {horizon} years — react to that jump.")
    return tool_response({
        "goal": name,
        "inflated_target": goal.inflated_target,
        "inflation_used": inflation,
        "goals_captured": len(STATE.goals),
    }, hint)


async def project_existing_corpus(args: dict) -> dict:
    if not STATE.portfolio:
        return missing("the existing portfolio",
                       "Call pull_mf_central first.")
    goal = get_goal(args["goal_name"])
    if not goal:
        return missing(f"a goal named '{args['goal_name']}'",
                       "Add the goal with add_goal first, or use the exact goal name.")
    p = STATE.portfolio
    g_rate = fm.blended_growth(p["equity_value"], p["debt_value"])
    n = goal.horizon_years
    fv_total = fm.lumpsum_fv(p["total_value"], g_rate, n) + fm.sip_fv(p["total_monthly_sip"], g_rate, n)
    # waterfall: only the un-earmarked fraction of the corpus is available to this goal
    available = fv_total * STATE.corpus_fraction_remaining
    earmarked = min(available, goal.inflated_target)
    if fv_total > 0:
        STATE.corpus_fraction_remaining = max(0.0, STATE.corpus_fraction_remaining - earmarked / fv_total)
    goal.projected_from_existing = round(earmarked)
    coverage = earmarked / goal.inflated_target if goal.inflated_target else 0
    hint = (f"Existing investments, grown at {g_rate * 100:.1f} percent blended, cover about "
            f"{coverage * 100:.0f} percent of the {goal.name} goal.")
    return tool_response({
        "goal": goal.name,
        "projected_from_existing": goal.projected_from_existing,
        "inflated_target": goal.inflated_target,
        "coverage_pct": round(coverage * 100, 1),
        "blended_growth_used": round(g_rate, 4),
    }, hint)


async def compute_gap_and_sip(args: dict) -> dict:
    if not STATE.risk_profile:
        return missing("the risk profile",
                       "Ask the behavioral risk questions and call assess_risk_profile first.")
    if not STATE.ratios:
        return missing("the Account Aggregator pull",
                       "Call pull_account_aggregator first — it sets income, expenses and monthly loan repayments.")
    goal = get_goal(args["goal_name"])
    if not goal:
        return missing(f"a goal named '{args['goal_name']}'", "Add the goal with add_goal first.")
    if goal.projected_from_existing is None:
        return missing(f"the projection for '{goal.name}'",
                       "Call project_existing_corpus for this goal first.")

    rate = float(args.get("expected_return") or fm.EXPECTED_RETURN[STATE.risk_profile])
    gap = max(0.0, goal.inflated_target - goal.projected_from_existing)
    goal.required_sip = fm.round_to_500(fm.required_sip(gap, rate, goal.horizon_years))
    idle = STATE.ratios["idle_surplus"]
    total_sip = sum(g.required_sip or 0 for g in STATE.goals if g.funded)
    afford = fm.affordability(total_sip, idle)

    STATE.gap_result = {
        "goal": goal.name,
        "gap": round(gap),
        "required_sip": goal.required_sip,
        "expected_return_used": rate,
        "total_required_sip_all_goals": total_sip,
        "idle_surplus": idle,
        "affordability": afford,
    }
    await ui_bus.emit_artifact("inflation_curve", {
        "goal": goal.name,
        "target_amount_today": goal.target_amount_today,
        "inflated_target": goal.inflated_target,
        "projected_from_existing": goal.projected_from_existing,
        "gap": round(gap),
        "horizon_years": goal.horizon_years,
        "required_sip": goal.required_sip,
        "expected_return_used": rate,
        "inflation_used": fm.inflation_for_goal(goal.name),
        "target_year": _dt.datetime.now().year + goal.horizon_years,
    })
    await _maybe_emit_sip_cascade()
    hint = (f"For {goal.name} the gap needs {goal.required_sip} rupees a month. Across all goals "
            f"so far that's {total_sip} rupees against an idle surplus of {idle} — {afford}.")
    return tool_response(STATE.gap_result, hint)


async def reprioritize(args: dict) -> dict:
    funded_goals = [g for g in sorted(STATE.goals, key=lambda g: g.priority) if g.required_sip is not None]
    if not funded_goals:
        return missing("computed SIPs for the goals",
                       "Run project_existing_corpus and compute_gap_and_sip for each goal first.")
    budget = float(args["max_affordable_sip"])
    rate = fm.EXPECTED_RETURN[STATE.risk_profile or "balanced"]
    remaining = budget
    table = []
    for g in funded_goals:
        need = g.required_sip or 0
        if need <= remaining:
            remaining -= need
            g.funded = True
            table.append({"goal": g.name, "priority": g.priority, "assigned_sip": need,
                          "status": "fully funded"})
        elif remaining >= 500:
            assigned = fm.round_to_500(remaining)
            assigned = min(assigned, int(remaining // 500) * 500) or 500
            gap = max(0.0, g.inflated_target - (g.projected_from_existing or 0))
            achieved = fm.sip_fv(assigned, rate, g.horizon_years)
            shortfall = max(0.0, gap - achieved)
            extended = fm.years_to_target(assigned, gap, rate)
            g.funded = True
            g.required_sip = assigned
            remaining = 0
            table.append({
                "goal": g.name, "priority": g.priority, "assigned_sip": assigned,
                "status": "partially funded",
                "shortfall_at_horizon": round(shortfall),
                "shortfall_pct": round(shortfall / g.inflated_target * 100, 1),
                "or_extend_horizon_to_years": None if math.isinf(extended) else extended,
                "original_horizon_years": g.horizon_years,
            })
        else:
            g.funded = False
            g.required_sip = 0
            table.append({"goal": g.name, "priority": g.priority, "assigned_sip": 0,
                          "status": "parked — no budget left"})
    partial = next((r for r in table if r["status"] == "partially funded"), None)
    if partial:
        hint = (f"At {budget:.0f} rupees a month, {partial['goal']} falls short by about "
                f"{partial['shortfall_pct']} percent — or it moves out to "
                f"{partial['or_extend_horizon_to_years']} years. Offer the trade-off and let them choose.")
    else:
        parked = [r["goal"] for r in table if r["assigned_sip"] == 0]
        hint = (f"At this budget, {', '.join(parked)} gets parked." if parked
                else "All goals fit within this budget.")
    await _maybe_emit_sip_cascade()
    return tool_response({"max_affordable_sip": budget, "goals": table}, hint)


async def build_goal_portfolio(args: dict) -> dict:
    if not STATE.risk_profile:
        return missing("the risk profile", "Call assess_risk_profile first.")
    goal = get_goal(args["goal_name"])
    if not goal:
        return missing(f"a goal named '{args['goal_name']}'",
                       "Use the exact goal name; add it with add_goal first if missing.")
    if not goal.funded or not goal.required_sip:
        return missing(f"a funded SIP for '{goal.name}'",
                       "Run compute_gap_and_sip (and reprioritize if needed) for this goal first.")

    bucket = fm.horizon_bucket(goal.horizon_years)
    phases = fm.build_phases(bucket, goal.horizon_years, goal.required_sip)

    STATE.proposed_portfolios[goal.name] = {
        "goal": goal.name,
        "horizon_bucket": bucket,
        "horizon_years": goal.horizon_years,
        "monthly_sip": goal.required_sip,
        "phases": phases,
        "current_phase": phases[0],
        "selection_basis": ("This goal-based portfolio is built from the user's risk profile and "
                            "goal horizon, using top category funds from each required category "
                            "to balance risk and return."),
    }
    await ui_bus.emit_artifact("sip_split", STATE.proposed_portfolios[goal.name])

    if bucket == "long":
        hint = (f"{goal.name} is {goal.horizon_years} years — long-term, three phases. "
                f"Present only current phase one now: {phases[0]['duration_years']} years, "
                f"eighty percent equity, fifteen percent debt, five percent gold. Explain that "
                f"this goal-based portfolio uses the user's risk profile and top category funds "
                f"for the right risk-return mix; mention future phases only as glide-down context.")
    elif bucket == "medium":
        hint = (f"{goal.name} is {goal.horizon_years} years — medium-term, two phases. "
                f"Present only current phase one now: {phases[0]['duration_years']} years, "
                f"fifty percent equity, forty percent debt, ten percent gold. Explain that the "
                f"portfolio uses top category funds chosen for the user's risk profile and "
                f"the right risk-return mix; mention "
                f"the later debt-heavy phase only as glide-down context.")
    else:
        hint = (f"{goal.name} is {goal.horizon_years} years — short-term, one phase. "
                f"Present the current phase: ninety-five percent debt and five percent gold, "
                f"using top category funds for the user's risk profile, with focus on downside "
                f"protection, liquidity and the right risk-return mix.")

    return tool_response(STATE.proposed_portfolios[goal.name], hint)


def _goals_recap_payload() -> dict:
    """Snapshot of all captured goals for the 'Where we're heading' card."""
    goals = [
        {
            "name": g.name,
            "priority": g.priority,
            "horizon_years": g.horizon_years,
            "target_year": _dt.datetime.now().year + g.horizon_years,
            "target_amount_today": g.target_amount_today,
            "inflated_target": g.inflated_target,
            "required_sip": g.required_sip,
            "funded": g.funded,
        }
        for g in sorted(STATE.goals, key=lambda x: x.priority)
    ]
    return {
        "goals": goals,
        "total_inflated": sum(g["inflated_target"] or 0 for g in goals),
        "total_sip": sum(g["required_sip"] or 0 for g in goals if g["funded"]),
    }


async def show_artifact(args: dict) -> dict:
    """Re-summon a previously shown artifact, or build a goals_recap from STATE.

    The frontend keeps a queue and dismisses cards on tool advance, so the user
    can ask "show me my investments again" and Maya can bring it back without
    re-running the original tool. For goals_recap, we always rebuild from STATE
    so the recap reflects edits or reprioritizations since it was last seen.
    """
    kind = (args.get("kind") or "").strip()
    if not kind:
        return missing("an artifact kind", "Pass the kind name like income_snapshot or mfc_review.")

    if kind == "goals_recap":
        if not STATE.goals:
            return missing("any captured goals",
                           "There are no goals yet. Walk the user through Stage 5 first.")
        payload = _goals_recap_payload()
        await ui_bus.emit_artifact("goals_recap", payload)
        return tool_response(payload,
                             "Goals recap is back on screen — narrate the running tally briefly.")

    cached = ui_bus.last_artifact(kind)
    if cached is None:
        return missing(f"a previously shown '{kind}' artifact",
                       "The user has not seen that card yet — walk them through it the normal way.")
    await ui_bus.emit_artifact(kind, cached)
    return tool_response({"kind": kind}, f"Re-summoned {kind}. Briefly remind the user what it shows.")


async def generate_plan_pdf(args: dict) -> dict:
    if not STATE.goals or not STATE.ratios:
        return missing("a complete plan",
                       "Finish goals, ratios and the portfolio before generating the PDF.")
    language = args.get("language", "en")
    path = plan_pdf.generate_pdf(STATE, language=language)
    STATE.plan_pdf_path = path
    filename = path.split("/")[-1]
    url = f"/output/{filename}"
    total_sip = sum(g.required_sip or 0 for g in STATE.goals if g.funded)
    await ui_bus.emit_artifact("plan_hero", {
        "url": url,
        "pdf_file": filename,
        "total_monthly_sip": total_sip,
        "goals_count": len([g for g in STATE.goals if g.funded]),
    })
    logger.opt(colors=True).info(f"<green>📄 PLAN PDF READY: {path}</green>")
    logger.opt(colors=True).info(f"<green>📄 Serving at: {url}</green>")
    return tool_response(
        {"pdf_file": filename, "url": url},
        "The plan PDF is ready — tell them it's done, give three action items, and close warmly.")


# ---------------------------------------------------------------- schemas

_NUM = {"type": "number"}

TOOL_SPECS = [
    (confirm_resume, "Release the returning-session gate after the user says whether to continue or change the saved plan. Never call this in a fresh session or before the user answers.",
     {"user_confirmed": {"type": "boolean", "description": "True after the user answers the resume question"},
      "choice": {"type": "string", "description": "Short verbatim summary such as continue or change home budget"}},
     ["user_confirmed"]),
    (choose_experience, "Choose a path for the preloaded /simulator call after the user answers Maya's opening question.",
     {"choice": {"type": "string", "description": "traditional for goal planning, or simulator for a financial decision simulation"}},
     ["choice"]),
    (simulate_life_event, "Compare one life decision against the preloaded financial profile. Ask only for the fields needed by the selected event, then call this tool. Supported event_type values: career_break, home_timing, starting_family.",
     {
         "event_type": {"type": "string", "description": "career_break, home_timing, or starting_family"},
         "duration_months": {"type": "integer", "description": "Career break length in months"},
         "starts_in_months": {"type": "integer", "description": "Months until the career break starts"},
         "income_reduction_percent": {"type": "number", "description": "Explicit income reduction during the career break, from zero to one hundred percent"},
         "goal_amount_today": {"type": "number", "description": "Current home cost in rupees"},
         "current_horizon_years": {"type": "integer", "description": "Current planned home timeline"},
         "proposed_horizon_years": {"type": "integer", "description": "New home timeline to compare"},
         "child_arrival_years": {"type": "integer", "description": "Years until the child may arrive"},
         "added_monthly_cost": {"type": "number", "description": "Expected added monthly family cost in rupees"},
         "education_cost_today": {"type": "number", "description": "Education amount in today's rupees"},
     },
     ["event_type"]),
    (analyze_financial_emergency, "Respond to a life event and, when applicable, rework the completed emergency-mode plan without applying it yet. Use income_shock for lost/reduced income, urgent_cost for money needed now, and new_child for a recent birth. Re-call it when the user wants a named goal protected.",
     {
         "emergency_type": {"type": "string", "description": "income_shock, urgent_cost, or new_child"},
         "description": {"type": "string", "description": "Short verbatim description of what happened"},
         "monthly_income_after": {"type": "number", "description": "Income remaining each month during an income shock"},
         "duration_months": {"type": "integer", "description": "How many months the income shock may last"},
         "one_time_cost": {"type": "number", "description": "Rupees needed immediately for an urgent cost"},
         "recovery_months": {"type": "integer", "description": "Months over which to rebuild the emergency reserve"},
         "protected_goal_names": {
             "type": "array",
             "items": {"type": "string"},
             "description": "Exact goal names the user refuses to pause, if any",
         },
     },
     ["emergency_type", "description"]),
    (commit_emergency_plan, "Apply the latest viable emergency proposal only after the user explicitly accepts it, or undo an already applied emergency plan.",
     {
         "action": {
             "type": "string",
             "description": "accept or undo",
         },
     },
     ["action"]),
    (assess_risk_profile, "Score the user's verbatim answers to the 2 behavioral risk scenario questions into a risk profile.",
     {"answers": {"type": "array", "items": {"type": "string"},
                  "description": "The user's verbatim answers to the 2 scenario questions, in order"}}, ["answers"]),
    (add_family, "Capture family details: spouse age, children with ages, other dependents count.",
     {"spouse_age": {"type": "integer", "description": "Age of spouse if any, omit otherwise"},
      "children": {"type": "array", "items": {"type": "object", "properties": {"age": {"type": "integer"}}},
                   "description": "List of children with their ages"},
      "dependents_count": {"type": "integer", "description": "Other dependents (e.g., parents); 0 if none"}},
     []),
    (pull_mf_central, "Fetch the caller's existing mutual fund portfolio from MF Central (mocked). Call only after Maya has explained MF Central, why the data is needed, and the user explicitly agrees to trigger OTP. The browser will request mock OTP 1234.",
     {"user_confirmed_consent": {"type": "boolean", "description": "True only after the user explicitly agrees to trigger the MF Central OTP"},
      "consent_context": {"type": "string", "description": "Brief summary of what Maya explained before triggering OTP"},
      "holding_edits": {"type": "array",
                        "description": "Optional corrections to MF Central holdings",
                        "items": {"type": "object",
                                  "properties": {"fund": {"type": "string"},
                                                 "current_value": {"type": "number"},
                                                 "monthly_sip": {"type": "number"}}}}},
     ["user_confirmed_consent", "consent_context"]),
    (pull_account_aggregator, "Pull bank, EPF, NPS, stocks and cash flows via Finvu Account Aggregator (mocked). Call first only after Maya has explained AA, what data is pulled, why it helps, and the user explicitly agrees to trigger OTP. When the user agrees to Finvu OTP, call this in the same assistant turn; do not only announce that the OTP is being triggered. Later correction calls reuse consent.",
     {"user_confirmed_consent": {"type": "boolean", "description": "True only after the user explicitly agrees to trigger the Finvu OTP"},
      "consent_context": {"type": "string", "description": "Brief summary of what Maya explained before triggering OTP"},
      "monthly_income": {"type": "number", "description": "Optional user-corrected monthly income"},
      "monthly_expenses": {"type": "number", "description": "Optional user-corrected monthly expenses excluding loan repayments"},
      "monthly_emi": {"type": "number", "description": "Optional user-corrected monthly loan repayment"},
      "investments": {"type": "number", "description": "Optional user-corrected monthly investments from bank statement"},
      "household_expenses": {"type": "number", "description": "Optional user-corrected household expenses"},
      "utilities": {"type": "number", "description": "Optional user-corrected utilities"},
      "entertainment": {"type": "number", "description": "Optional user-corrected entertainment"},
      "epf": {"type": "number", "description": "Optional user-corrected EPF value"},
      "nps": {"type": "number", "description": "Optional user-corrected NPS value"},
      "stocks": {"type": "number", "description": "Optional user-corrected stocks value"}},
     ["user_confirmed_consent", "consent_context"]),
    (add_manual_asset, "Add a voice-mentioned asset that AA didn't return — PPF, fixed deposit, gold, real estate, US stocks, international stocks, etc.",
     {"name": {"type": "string", "description": "User-friendly label like 'PPF account'"},
      "asset_type": {"type": "string", "description": "Category: ppf, fd, gold, real_estate, us_stocks, international_stocks, other"},
      "value": {"type": "number", "description": "Current value in INR"}},
     ["name", "value"]),
    (confirm_financial_snapshot, "Mark financial data ready for goals in two confirmations. First call after the user confirms AA-derived income, expenses, monthly loan repayments and methodology, with user_confirmed_cashflow true and user_confirmed_investments false. Later call only after showing MF holdings plus Finvu EPF, NPS and stocks, handling edits/additions, and getting investment confirmation.",
     {"user_confirmed_cashflow": {"type": "boolean", "description": "True only after the user explicitly confirms income, expenses, monthly loan repayments and cash-flow methodology"},
      "user_confirmed_investments": {"type": "boolean", "description": "True only after the user explicitly confirms MF holdings plus EPF, NPS, stocks and any additions"},
      "user_confirmed_financial_data": {"type": "boolean", "description": "Backward-compatible: true only if the user confirmed both cash flow and investments"},
      "user_answered_additional_assets": {"type": "boolean", "description": "True only after the user answered the additional-investments question"},
      "confirmation_context": {"type": "string", "description": "Brief summary of the user's confirmation and additions/no additions"}},
     ["user_confirmed_cashflow", "user_confirmed_investments", "user_answered_additional_assets", "confirmation_context"]),
    (add_goal, "Register a financial goal (max 4) and get its inflation-adjusted future cost. For an emergency fund, omit target_amount_today so the tool uses six months of confirmed monthly outflow.",
     {"name": {"type": "string"}, "target_amount_today": {"type": "number", "description": "Cost in today's rupees"},
      "horizon_years": {"type": "integer"}, "priority": {"type": "integer", "description": "1 = most important"}},
     ["name", "priority"]),
    (project_existing_corpus, "Project the existing portfolio to a goal's horizon and earmark it (waterfall by priority).",
     {"goal_name": {"type": "string"}}, ["goal_name"]),
    (compute_gap_and_sip, "Compute the funding gap and required monthly SIP for a goal, with affordability.",
     {"goal_name": {"type": "string"},
      "expected_return": {"type": "number", "description": "Override annual return as decimal; omit to use risk profile default"}},
     ["goal_name"]),
    (reprioritize, "Re-fund goals in priority order within the user's comfortable monthly budget; returns trade-offs.",
     {"max_affordable_sip": {"type": "number", "description": "Monthly amount the user is comfortable investing"}},
     ["max_affordable_sip"]),
    (build_goal_portfolio, "Build the phased portfolio for a single goal: horizon decides phase count (short=1, medium=2, long=3) and allocation. Call once per funded goal.",
     {"goal_name": {"type": "string"}}, ["goal_name"]),
    (show_artifact, "Re-summon a card the user already saw. Call this when the user asks 'show me X again', 'what was that home goal again', 'pull up my plan'. Kinds: risk_reveal, family_recap, mfc_review, income_snapshot, investments_review, goal_types_picker, inflation_curve, sip_split, plan_hero. Special: 'goals_recap' rebuilds a 'Where we're heading' summary from the current goals — call this whenever the user wants to see the full list of goals in flight.",
     {"kind": {"type": "string", "description": "Artifact kind to re-summon, or 'goals_recap' to build a live goals summary"}},
     ["kind"]),
    (generate_plan_pdf, "Generate the final financial plan PDF from everything gathered. Set language to 'hi' when the user has conversed primarily in Hindi; otherwise use 'en'.",
     {"language": {"type": "string", "enum": ["en", "hi"],
                   "description": "PDF language: 'hi' for a Hindi conversation, otherwise 'en'."}},
     ["language"]),
]


def register_tools(llm) -> ToolsSchema:
    """Register all 9 handlers on the LLM service; returns the ToolsSchema for the context."""
    schemas = []
    for fn, description, properties, required in TOOL_SPECS:
        schemas.append(FunctionSchema(name=fn.__name__, description=description,
                                      properties=properties, required=required))
        llm.register_function(fn.__name__, _wrap(fn))
    return ToolsSchema(standard_tools=schemas)


def _wrap(fn):
    """Console-log every tool call (the demo debug view) and never let one crash the call."""
    async def handler(params: FunctionCallParams):
        arguments = dict(params.arguments)
        logger.opt(colors=True).info(
            f"<yellow>🔧 TOOL CALL {fn.__name__}({json.dumps(arguments)})</yellow>")
        record_tool_call(fn.__name__, arguments)
        try:
            result = await fn(arguments)
        except Exception as e:
            logger.exception(f"Tool {fn.__name__} failed")
            result = {"error": str(e),
                      "instruction": "Apologize briefly and try a different step."}
        record_tool_result(fn.__name__, result)
        logger.opt(colors=True).info(
            f"<cyan>🔧 TOOL RESULT {fn.__name__} → {json.dumps(result, default=str)[:600]}</cyan>")
        await params.result_callback(result)
        # Push the updated state to the browser UI (no-op for voice-only / tests).
        await ui_bus.emit({"type": "state", "payload": snapshot(last_event=fn.__name__)})
    return handler
