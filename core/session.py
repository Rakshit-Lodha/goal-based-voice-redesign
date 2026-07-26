"""In-memory session state (one call at a time) + progress checklist + next_step logic."""

import json
import os
import datetime as _dt
from dataclasses import asdict, dataclass, field
from typing import Any

# Demo persona — caller is treated as already KYC-verified, so Maya never asks
# for name or age. Both prompts.py and reset() read from these constants.
KYC_NAME = "Rakshit"
KYC_AGE = 28
STATE_SCHEMA_VERSION = 1


@dataclass
class Goal:
    name: str
    target_amount_today: float
    horizon_years: int
    priority: int  # 1 = highest
    inflated_target: float | None = None
    projected_from_existing: float | None = None
    required_sip: float | None = None
    funded: bool = True


@dataclass
class SessionState:
    name: str | None = None
    age: int | None = None
    monthly_income: float | None = None
    monthly_expenses: float | None = None
    monthly_emi: float | None = None
    expense_breakdown: dict | None = None
    portfolio: dict | None = None
    ratios: dict | None = None
    risk_profile: str | None = None
    risk_answers: list[str] = field(default_factory=list)
    # Family captured in stage 2: {spouse_age, children: [{age}], dependents_count}.
    family: dict | None = None
    # AA-pulled non-MF holdings: {epf, nps, stocks, ...}. Narrated, not yet in gap math.
    aa_assets: dict | None = None
    # True only after the user has accepted AA-derived cash flow/assets and answered
    # the additional-investments check.
    cashflow_confirmed: bool = False
    investments_confirmed: bool = False
    financial_snapshot_confirmed: bool = False
    # Voice-added extras (PPF, FDs, gold, real estate): list of {name, asset_type, value}.
    additional_assets: list = field(default_factory=list)
    goals: list[Goal] = field(default_factory=list)
    gap_result: dict | None = None
    # Per-goal phase plans keyed by goal name (see finmath.build_phases).
    proposed_portfolios: dict = field(default_factory=dict)
    plan_pdf_path: str | None = None
    # fraction of the existing corpus not yet earmarked to a goal (waterfall)
    corpus_fraction_remaining: float = 1.0
    # Most recent total SIP across funded goals that the user has already
    # been shown — used to emit a cascade_diff toast when a revise loop
    # bumps the total up or down.
    last_published_total_sip: float = 0.0
    # When provider-backed data was last observed. Restored data is deliberately
    # described as previous-session data until the user authorizes a refresh.
    financial_snapshot_observed_at: str | None = None
    # Call-scoped resume flags. These are never exported to cross-session memory.
    is_returning_session: bool = False
    resume_confirmed: bool = False
    resume_completed_plan: bool = False
    restored_financial_data: bool = False
    # Call-scoped simulator flags. Simulator calls use a deterministic demo
    # snapshot and never restore or publish cross-session memory.
    is_simulator_session: bool = False
    simulator_choice: str | None = None
    last_simulation: dict | None = None
    # Call-scoped emergency flags. Emergency calls begin from a completed demo
    # plan, but never overwrite the user's cross-session memory.
    is_emergency_session: bool = False
    pending_emergency_plan: dict | None = None
    emergency_original_goals: list[dict] = field(default_factory=list)
    emergency_original_portfolios: dict = field(default_factory=dict)
    emergency_plan_applied: bool = False


STATE = SessionState()

_PERSISTENT_FIELDS = (
    "name",
    "age",
    "monthly_income",
    "monthly_expenses",
    "monthly_emi",
    "expense_breakdown",
    "portfolio",
    "ratios",
    "risk_profile",
    "risk_answers",
    "family",
    "aa_assets",
    "cashflow_confirmed",
    "investments_confirmed",
    "financial_snapshot_confirmed",
    "additional_assets",
    "goals",
    "gap_result",
    "proposed_portfolios",
    "plan_pdf_path",
    "corpus_fraction_remaining",
    "last_published_total_sip",
    "financial_snapshot_observed_at",
)

_OPTIONAL_NUMBER_FIELDS = {
    "monthly_income",
    "monthly_expenses",
    "monthly_emi",
}
_NUMBER_FIELDS = {
    "corpus_fraction_remaining",
    "last_published_total_sip",
}
_OPTIONAL_DICT_FIELDS = {
    "expense_breakdown",
    "portfolio",
    "ratios",
    "family",
    "aa_assets",
    "gap_result",
}
_BOOL_FIELDS = {
    "cashflow_confirmed",
    "investments_confirmed",
    "financial_snapshot_confirmed",
}


def reset():
    # mutate in place: other modules hold a reference to STATE
    STATE.__dict__.update(SessionState().__dict__)
    STATE.name = KYC_NAME
    STATE.age = KYC_AGE
    global _tick
    _tick = 0
    # Clear the re-summon cache so a fresh call doesn't replay last call's data.
    from core import ui_bus
    ui_bus.reset_artifact_cache()
    return STATE


def seed_simulator_profile() -> SessionState:
    """Start a repeatable demo call with all pre-goal information confirmed."""
    reset()
    from core import finmath, portfolio_data

    STATE.risk_profile = "balanced"
    STATE.risk_answers = ["Hold steady", "Balanced growth"]
    STATE.family = {
        "spouse_age": 25,
        "children": [],
        "dependents_count": 0,
    }
    STATE.portfolio = portfolio_data.lookup(STATE.name or KYC_NAME)
    STATE.aa_assets = {
        "epf": 450_000,
        "nps": 50_000,
        "stocks": 500_000,
    }
    STATE.monthly_income = 150_000
    STATE.monthly_expenses = 70_000
    STATE.monthly_emi = 25_000
    STATE.expense_breakdown = {
        "investments": 20_000,
        "household_expenses": 30_000,
        "utilities": 8_000,
        "entertainment": 12_000,
        "emis": 25_000,
    }
    STATE.ratios = finmath.financial_ratios(
        STATE.monthly_income,
        STATE.monthly_expenses,
        STATE.monthly_emi,
        STATE.portfolio["total_monthly_sip"],
    )
    STATE.cashflow_confirmed = True
    STATE.investments_confirmed = True
    STATE.financial_snapshot_confirmed = True
    STATE.financial_snapshot_observed_at = _dt.datetime.now(_dt.UTC).isoformat()
    STATE.is_simulator_session = True
    return STATE


def seed_emergency_plan() -> SessionState:
    """Start a repeatable emergency call from an already completed demo plan."""
    seed_simulator_profile()
    from core import finmath

    STATE.family = {
        "spouse_age": 25,
        "children": [{"age": 6}],
        "dependents_count": 0,
    }
    STATE.goals = [
        Goal(
            name="Emergency fund",
            target_amount_today=570_000,
            horizon_years=1,
            priority=1,
            inflated_target=570_000,
            projected_from_existing=570_000,
            required_sip=0,
        ),
        Goal(
            name="Buy a house in Pune",
            target_amount_today=10_000_000,
            horizon_years=10,
            priority=2,
            inflated_target=19_671_514,
            projected_from_existing=7_160_004,
            required_sip=50_500,
        ),
        Goal(
            name="Daughter's education",
            target_amount_today=3_000_000,
            horizon_years=12,
            priority=3,
            inflated_target=9_415_285,
            projected_from_existing=0,
            required_sip=9_500,
        ),
    ]
    STATE.proposed_portfolios = {
        goal.name: {
            "goal": goal.name,
            "horizon_bucket": finmath.horizon_bucket(goal.horizon_years),
            "horizon_years": goal.horizon_years,
            "monthly_sip": goal.required_sip,
            "phases": finmath.build_phases(
                finmath.horizon_bucket(goal.horizon_years),
                goal.horizon_years,
                goal.required_sip or 0,
            ),
        }
        for goal in STATE.goals
        if (goal.required_sip or 0) > 0
    }
    STATE.last_published_total_sip = 60_000
    STATE.is_simulator_session = False
    STATE.is_emergency_session = True
    return STATE


def export_state() -> dict[str, Any]:
    """Return the schema-versioned, JSON-safe persistent session state."""
    raw = asdict(STATE)
    state = {field_name: raw[field_name] for field_name in _PERSISTENT_FIELDS}
    if state["plan_pdf_path"] and not os.path.exists(state["plan_pdf_path"]):
        state["plan_pdf_path"] = None
    # Fail here rather than publishing a checkpoint that cannot be read back.
    json.dumps(state)
    return {"schema_version": STATE_SCHEMA_VERSION, "state": state}


def _validated_state(payload: dict[str, Any]) -> SessionState:
    if not isinstance(payload, dict):
        raise ValueError("state checkpoint must be an object")
    if payload.get("schema_version") != STATE_SCHEMA_VERSION:
        raise ValueError("unsupported state schema")
    raw = payload.get("state")
    if not isinstance(raw, dict):
        raise ValueError("state checkpoint is missing state")

    candidate = SessionState(name=KYC_NAME, age=KYC_AGE)
    for field_name in _PERSISTENT_FIELDS:
        if field_name not in raw:
            continue
        value = raw[field_name]
        if field_name in _OPTIONAL_NUMBER_FIELDS:
            if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float))):
                raise ValueError(f"{field_name} must be a number or null")
        elif field_name in _NUMBER_FIELDS:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"{field_name} must be a number")
        elif field_name in _OPTIONAL_DICT_FIELDS:
            if value is not None and not isinstance(value, dict):
                raise ValueError(f"{field_name} must be an object or null")
        elif field_name in _BOOL_FIELDS:
            if not isinstance(value, bool):
                raise ValueError(f"{field_name} must be a boolean")
        elif field_name == "age":
            if value is not None and (isinstance(value, bool) or not isinstance(value, int)):
                raise ValueError("age must be an integer or null")
        elif field_name in {"name", "risk_profile", "financial_snapshot_observed_at"}:
            if value is not None and not isinstance(value, str):
                raise ValueError(f"{field_name} must be a string or null")
        elif field_name == "plan_pdf_path":
            if value is not None and not isinstance(value, str):
                raise ValueError("plan_pdf_path must be a string or null")
            if value and not os.path.exists(value):
                value = None
        elif field_name == "risk_answers":
            if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
                raise ValueError("risk_answers must be a list of strings")
        elif field_name == "additional_assets":
            if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
                raise ValueError("additional_assets must be a list of objects")
        elif field_name == "proposed_portfolios":
            if not isinstance(value, dict):
                raise ValueError("proposed_portfolios must be an object")
        elif field_name == "goals":
            if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
                raise ValueError("goals must be a list of objects")
            try:
                value = [_validated_goal(item) for item in value]
            except (TypeError, ValueError) as exc:
                raise ValueError("invalid saved goal") from exc
        setattr(candidate, field_name, value)

    return candidate


def _validated_goal(value: dict[str, Any]) -> Goal:
    goal = Goal(**value)
    if not isinstance(goal.name, str) or not goal.name.strip():
        raise ValueError("goal name must be a non-empty string")
    if isinstance(goal.target_amount_today, bool) or not isinstance(
        goal.target_amount_today, (int, float)
    ):
        raise ValueError("goal target must be a number")
    if isinstance(goal.horizon_years, bool) or not isinstance(goal.horizon_years, int):
        raise ValueError("goal horizon must be an integer")
    if isinstance(goal.priority, bool) or not isinstance(goal.priority, int):
        raise ValueError("goal priority must be an integer")
    for field_name in (
        "inflated_target",
        "projected_from_existing",
        "required_sip",
    ):
        field_value = getattr(goal, field_name)
        if field_value is not None and (
            isinstance(field_value, bool) or not isinstance(field_value, (int, float))
        ):
            raise ValueError(f"goal {field_name} must be a number or null")
    if not isinstance(goal.funded, bool):
        raise ValueError("goal funded must be a boolean")
    return goal


def validate_state(payload: dict[str, Any]) -> None:
    """Raise ``ValueError`` if a checkpoint cannot be safely restored."""
    _validated_state(payload)


def restore_state(payload: dict[str, Any]) -> SessionState:
    """Validate a saved state and replace ``STATE`` atomically.

    Unsupported schemas are rejected. Unknown state fields are ignored so adding
    a field in a future compatible writer does not partially mutate this process.
    """
    candidate = _validated_state(payload)
    STATE.__dict__.update(candidate.__dict__)
    return STATE


def get_goal(name: str) -> Goal | None:
    name = name.strip().lower()
    for g in STATE.goals:
        if g.name.strip().lower() == name:
            return g
    return None


def progress() -> dict:
    s = STATE
    gaps_done = bool(s.goals) and all(g.required_sip is not None for g in s.goals if g.funded)
    funded = [g for g in s.goals if g.funded and (g.required_sip or 0) > 0]
    plan_done = bool(funded) and all(g.name in s.proposed_portfolios for g in funded)
    return {
        "risk": "done" if s.risk_profile else "pending",
        "family": "done" if s.family else "pending",
        "mfc": "done" if s.portfolio else "pending",
        "aa": "done" if s.aa_assets else "pending",
        "finances": "done" if s.ratios and s.financial_snapshot_confirmed else "pending",
        "goals": "done" if len(s.goals) >= 1 else "pending",
        "gap": "done" if gaps_done else "pending",
        "portfolio_plan": "done" if plan_done else "pending",
        "pdf": "done" if s.plan_pdf_path else "pending",
    }


def next_step() -> str:
    s = STATE
    if s.is_emergency_session:
        if not s.pending_emergency_plan:
            return (
                "Respond to what happened before discussing numbers. Match the emotional "
                "register: acknowledge a loss or shock, congratulate a positive transition, "
                "then give a brief three-part way to think about it. Reuse every fact the user "
                "already provided. Ask only one genuinely missing input before calling "
                "analyze_financial_emergency."
            )
        if not s.pending_emergency_plan.get("proposal_ready", True):
            return (
                "This is an orientation, not a proposal to accept. Continue with the supportive "
                "decision framework and ask which area feels most urgent: monthly cash flow, "
                "financial protection, or the longer-term goal. Do not ask for a list of numbers."
            )
        if not s.emergency_plan_applied:
            return (
                "Explain the emergency proposal and its effect on every goal. Ask which goal "
                "must be protected or whether the user accepts it. Re-run "
                "analyze_financial_emergency when they protect a goal; call "
                "commit_emergency_plan only after they explicitly accept."
            )
        return (
            "Confirm the emergency plan is active, state the immediate action and ask whether "
            "they want to undo it or make one more adjustment."
        )
    if s.is_returning_session and not s.resume_confirmed:
        return ("Welcome the user back, briefly mention the saved open item, and ask whether "
                "they want to continue or change anything. Do not call a financial tool until "
                "they answer, then call confirm_resume.")
    if s.is_returning_session and s.resume_completed_plan:
        return ("This saved plan is complete. Ask what has changed or what they want to review. "
                "Do not immediately close the call or regenerate the plan.")
    if s.is_simulator_session and not s.simulator_choice:
        return ("Ask the user to choose one of two paths: traditional goal planning, or a "
                "financial decision simulation. After they answer, call choose_experience.")
    if s.is_simulator_session and s.simulator_choice == "simulator":
        if not s.last_simulation:
            return ("Ask which decision they want to test: a career break, buying a home "
                    "earlier or later, or starting a family. Collect only the inputs required "
                    "for that scenario, one question at a time, then call simulate_life_event.")
        return ("Explain the before-and-after comparison from the latest simulation, including "
                "the trade-off and recommended action. Then ask whether they want to adjust "
                "this scenario, test another decision, or switch to traditional goal planning.")
    if s.is_simulator_session and s.simulator_choice == "traditional" and not s.goals:
        return ("The financial profile is already confirmed. Briefly say the user can plan for "
                "safety, long-term independence, or an aspiration. Ask which traditional goal "
                "they want to plan first; do not repeat risk, family, consent, or data collection.")
    if not s.risk_profile:
        return ("Ask the two behavioral risk questions one at a time, then call "
                "assess_risk_profile with both verbatim answers.")
    if not s.family:
        return ("Ask about family — spouse age, each child's age, any other dependents. "
                "Then call add_family.")
    if not s.portfolio:
        return ("Do not call pull_mf_central yet unless the user has explicitly agreed. "
                "First explain that the next step is to pull all investment data, starting "
                "with MF Central: a SEBI-regulated consolidated mutual fund view from CAMS "
                "and KFintech, formerly Karvy. Explain that this helps analyze holdings, "
                "spot underperforming funds, and make the financial plan richer. Ask for "
                "permission to trigger the OTP. If they agree, say you are triggering the "
                "MF Central OTP now, then call pull_mf_central.")
    if not s.aa_assets:
        return ("Do not call pull_account_aggregator yet unless the user has explicitly agreed. "
                "First explain Finvu Account Aggregator: an RBI-regulated encrypted consent "
                "flow that can pull bank, EPF, NPS, stock, income and expense data. Explain "
                "that this helps analyze cash flow, stocks, EPF, income, expenses and makes "
                "the financial plan seamless and richer. Ask permission to trigger the OTP. "
                "If they agree, say you are triggering the Finvu OTP now, then call "
                "pull_account_aggregator in the same assistant turn. Do not merely say the "
                "OTP is being triggered. If you already said it and AA is still pending, call "
                "pull_account_aggregator immediately.")
    if not s.financial_snapshot_confirmed:
        if not s.cashflow_confirmed:
            return ("Do not move to investments or goals yet. First show the Account Aggregator "
                    "income and expense snapshot: explain it came from the last three months of "
                    "bank data, show average monthly income, average monthly outflow, expense "
                    "breakup, monthly loan repayments, savings rate and monthly loan repayments "
                    "as a share of income. Ask if the user wants "
                    "to edit any income or expense number. If they edit, call "
                    "pull_account_aggregator again with only those corrections and then show the "
                    "updated cash-flow snapshot. Only after the user confirms income and expenses "
                    "are correct, call confirm_financial_snapshot with user_confirmed_cashflow true "
                    "and user_confirmed_investments false.")
        if not s.investments_confirmed:
            return ("Cash flow is confirmed. Before moving on, recap the savings rate and "
                    "monthly loan repayments as a share of income with their good / average / bad "
                    "labels. Then move to "
                    "investments: show MF Central holdings plus Finvu EPF, NPS and stocks as a "
                    "list. Ask if the user wants to edit or add investments such as PPF, fixed deposits, "
                    "gold, real estate, US stocks or "
                    "international stocks. For each added item, call add_manual_asset. If they "
                    "correct EPF, NPS or stocks, call pull_account_aggregator again with only "
                    "those corrections. Once the user confirms investments and has answered the "
                    "additions question, call confirm_financial_snapshot with both "
                    "user_confirmed_cashflow and user_confirmed_investments true.")
    # MF portfolio review is narrative-only — gated by portfolio + aa_assets both being set.
    if len(s.goals) < 1:
        return ("Before goals, briefly review the MF Central portfolio: explain that funds are "
                "judged by category suitability for the user's risk profile and by a score based "
                "on consistency versus category average plus downside protection. Mention good "
                "funds and underperformers from the portfolio payload without listing every fund. "
                "Then discuss goals (1-4 max). First explain the goal-planning framework: default "
                "primary goals are emergency fund and retirement because they create safety and "
                "long-term independence. Explain emergency fund as six months of runway for job "
                "loss, medical issues or any disruption, then call add_goal with no "
                "target_amount_today so the tool computes it. Also suggest retirement anchored "
                "to age 60 and child education if relevant.")
    pending_gap = next((g for g in sorted(s.goals, key=lambda g: g.priority)
                        if g.funded and g.required_sip is None), None)
    if pending_gap:
        return (f"For goal '{pending_gap.name}': call project_existing_corpus, then "
                f"compute_gap_and_sip. Present the gap honestly. Complete this goal's "
                f"planning before moving to the next goal.")
    funded_goals = [g for g in sorted(s.goals, key=lambda g: g.priority)
                    if g.funded and (g.required_sip or 0) > 0]
    pending_plan = next((g for g in funded_goals if g.name not in s.proposed_portfolios), None)
    if pending_plan:
        if not s.proposed_portfolios:
            return ("If the total SIP felt tight, negotiate with reprioritize first. "
                    "Otherwise: in two or three sentences explain the phasing method "
                    "(short goals are one phase debt-heavy; medium two phases balanced; "
                    "long three phases equity-heavy with a glide-down to debt), then "
                    f"call build_goal_portfolio for '{pending_plan.name}'.")
        return f"Call build_goal_portfolio for '{pending_plan.name}' next."
    if not s.plan_pdf_path:
        return ("Only after every captured funded goal has its gap and portfolio complete, "
                "call generate_plan_pdf, then summarize 3 action items and close warmly.")
    return "Plan is done. Summarize the 3 action items and say a warm goodbye."


# Monotonic counter — every snapshot() call gets a fresh value so the browser
# can distinguish two consecutive state events that happen to share the same
# last_event (e.g. confirm_financial_snapshot called twice for the two
# confirmation stages). The artifact queue uses this to advance the queue on
# every distinct tool call instead of only on tool-name changes.
_tick: int = 0


def snapshot(last_event: str | None = None) -> dict:
    """JSON-serializable mirror of the whole session for the browser UI."""
    global _tick
    _tick += 1
    s = STATE
    return {
        "name": s.name,
        "age": s.age,
        "monthly_income": s.monthly_income,
        "monthly_expenses": s.monthly_expenses,
        "monthly_emi": s.monthly_emi,
        "expense_breakdown": s.expense_breakdown,
        "ratios": s.ratios,
        "risk_profile": s.risk_profile,
        "family": s.family,
        "aa_assets": s.aa_assets,
        "cashflow_confirmed": s.cashflow_confirmed,
        "investments_confirmed": s.investments_confirmed,
        "financial_snapshot_confirmed": s.financial_snapshot_confirmed,
        "additional_assets": s.additional_assets,
        "portfolio": s.portfolio,
        "goals": [asdict(g) for g in s.goals],
        "proposed_portfolios": s.proposed_portfolios,
        "plan_pdf_url": f"/output/{os.path.basename(s.plan_pdf_path)}" if s.plan_pdf_path else None,
        "progress": progress(),
        "last_event": last_event,
        "simulator_mode": s.is_simulator_session,
        "simulator_choice": s.simulator_choice,
        "last_simulation": s.last_simulation,
        "emergency_mode": s.is_emergency_session,
        "pending_emergency_plan": s.pending_emergency_plan,
        "emergency_plan_applied": s.emergency_plan_applied,
        "tick": _tick,
    }


def tool_response(payload: dict, narration_hint: str) -> dict:
    """Shared wrapper: every tool result re-anchors the LLM with progress + next_step."""
    return {
        **payload,
        "narration_hint": narration_hint,
        "progress": progress(),
        "next_step": next_step(),
    }


def missing(what: str, ask: str) -> dict:
    """Guard-rail response when a tool is called before its prerequisites exist."""
    return {
        "error": f"missing: {what}",
        "instruction": f"You haven't collected {what} yet. {ask}",
        "progress": progress(),
        "next_step": next_step(),
    }
