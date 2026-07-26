"""Pure deterministic financial math. No LLM, no I/O. All currency INR, rates as decimals."""

import math

# Annual growth assumptions for projecting existing holdings
EQUITY_GROWTH = 0.11
DEBT_GROWTH = 0.07

# Inflation by goal category
DEFAULT_INFLATION = 0.06
EDUCATION_INFLATION = 0.10
PROPERTY_INFLATION = 0.07

# Expected portfolio return by risk profile
EXPECTED_RETURN = {"conservative": 0.09, "balanced": 0.11, "aggressive": 0.13}

EQUITY_BAND = {"conservative": 0.30, "balanced": 0.55, "aggressive": 0.75}

# risk profile -> (equity, debt, gold) allocation
ALLOCATION = {
    "conservative": (0.30, 0.60, 0.10),
    "balanced": (0.55, 0.40, 0.05),
    "aggressive": (0.75, 0.20, 0.05),
}

# Horizon buckets and per-bucket phase glide paths.
# Each phase: (fraction_of_horizon, equity, debt, gold). Allocations sum to 1.
HORIZON_SHORT_MAX = 3   # years ≤ 3 → short
HORIZON_MEDIUM_MAX = 7  # 4-7 → medium, > 7 → long

PHASE_PLAN = {
    "short":  [(1.00, 0.00, 0.95, 0.05)],
    "medium": [(0.60, 0.50, 0.40, 0.10),
               (0.40, 0.20, 0.75, 0.05)],
    "long":   [(0.50, 0.80, 0.15, 0.05),
               (0.30, 0.50, 0.40, 0.10),
               (0.20, 0.20, 0.70, 0.10)],
}

# Funds that fill each sub-bucket within a phase's allocation, with intra-bucket
# weights and a one-line rationale for narration.
FUND_PALETTE = {
    "equity": [
        ("UTI Nifty 50 Index Fund",     0.60, "Low-cost core owning India's 50 biggest companies."),
        ("Parag Parikh Flexi Cap Fund", 0.40, "Manager moves across caps for extra growth."),
    ],
    "debt": [
        ("HDFC Short Term Debt Fund", 0.70, "Steady low-volatility cushion."),
        ("HDFC Liquid Fund",          0.30, "Cash-like, near-zero risk."),
    ],
    "gold": [
        ("Nippon India Gold Savings Fund", 1.00, "Hedge that holds up when equity wobbles."),
    ],
}


def round_to_500(x: float) -> int:
    """Round to the nearest ₹500."""
    return int(round(x / 500.0) * 500)


def inflation_for_goal(goal_name: str) -> float:
    """Pick inflation rate from goal name keywords."""
    name = goal_name.lower()
    if any(k in name for k in ("education", "college", "school", "study", "studies", "mba", "degree")):
        return EDUCATION_INFLATION
    if any(k in name for k in ("house", "home", "property", "flat", "apartment", "plot")):
        return PROPERTY_INFLATION
    return DEFAULT_INFLATION


def inflate(amount_today: float, years: int, rate: float) -> float:
    """Future cost of a goal: amount × (1 + inflation)^years."""
    return amount_today * (1 + rate) ** years


def financial_ratios(monthly_income: float, monthly_expenses: float, monthly_emi: float = 0.0,
                     existing_monthly_sip: float = 0.0) -> dict:
    """Surplus, savings rate, DTI with qualitative bands, and idle surplus."""
    surplus = monthly_income - monthly_expenses - monthly_emi
    savings_rate = surplus / monthly_income if monthly_income else 0.0
    dti = monthly_emi / monthly_income if monthly_income else 0.0

    if savings_rate > 0.15:
        savings_band = "good"
    elif savings_rate >= 0.05:
        savings_band = "average"
    else:
        savings_band = "bad"

    if dti < 0.05:
        dti_band = "good"
    elif dti <= 0.25:
        dti_band = "average"
    else:
        dti_band = "bad"

    return {
        "surplus": round(surplus),
        "savings_rate": round(savings_rate, 4),
        "savings_band": savings_band,
        "debt_to_income": round(dti, 4),
        "dti_band": dti_band,
        "idle_surplus": round(surplus - existing_monthly_sip),
    }


def simulate_career_break(
    *,
    monthly_income: float,
    essential_outflow: float,
    idle_surplus: float,
    debt_fund_cushion: float,
    duration_months: int,
    starts_in_months: int,
    income_reduction_percent: float,
) -> dict:
    """Estimate the reserve and pre-break monthly saving requirement."""
    income_during = monthly_income * (1 - income_reduction_percent / 100)
    cash_position_during = income_during - essential_outflow
    reserve_required = max(0.0, -cash_position_during) * duration_months
    additional_reserve = max(0.0, reserve_required - debt_fund_cushion)
    monthly_reserve_build = (
        additional_reserve / starts_in_months
        if starts_in_months > 0
        else additional_reserve
    )
    return {
        "income_during": round(income_during),
        "cash_position_before": round(monthly_income - essential_outflow),
        "cash_position_during": round(cash_position_during),
        "reserve_required": round(reserve_required),
        "debt_fund_cushion": round(debt_fund_cushion),
        "additional_reserve": round(additional_reserve),
        "monthly_reserve_build": round_to_500(monthly_reserve_build),
        "goal_surplus_after_build": round(idle_surplus - monthly_reserve_build),
    }


def simulate_home_timing(
    *,
    amount_today: float,
    current_horizon_years: int,
    proposed_horizon_years: int,
    portfolio_value: float,
    portfolio_monthly_sip: float,
    equity_value: float,
    debt_value: float,
    expected_return: float,
    idle_surplus: float,
) -> dict:
    """Compare a home goal at two purchase timelines."""
    growth = blended_growth(equity_value, debt_value)

    def home_case(years: int) -> dict:
        target = inflate(amount_today, years, PROPERTY_INFLATION)
        projected = (
            lumpsum_fv(portfolio_value, growth, years)
            + sip_fv(portfolio_monthly_sip, growth, years)
        )
        gap = max(0.0, target - projected)
        sip = round_to_500(required_sip(gap, expected_return, years))
        return {
            "horizon_years": years,
            "inflated_target": round(target),
            "projected_existing": round(projected),
            "gap": round(gap),
            "required_sip": sip,
            "affordability": affordability(sip, idle_surplus),
        }

    current = home_case(current_horizon_years)
    proposed = home_case(proposed_horizon_years)
    return {
        "amount_today": round(amount_today),
        "current": current,
        "proposed": proposed,
        "sip_delta": proposed["required_sip"] - current["required_sip"],
    }


def simulate_starting_family(
    *,
    child_arrival_years: int,
    added_monthly_cost: float,
    education_cost_today: float,
    expected_return: float,
    idle_surplus: float,
) -> dict:
    """Estimate childcare pressure plus a higher-education monthly investment."""
    education_horizon = child_arrival_years + 18
    education_target = inflate(
        education_cost_today,
        education_horizon,
        EDUCATION_INFLATION,
    )
    education_sip = round_to_500(
        required_sip(education_target, expected_return, education_horizon)
    )
    rounded_monthly_cost = round_to_500(added_monthly_cost)
    total_monthly_pressure = rounded_monthly_cost + education_sip
    return {
        "child_arrival_years": child_arrival_years,
        "education_horizon_years": education_horizon,
        "education_target": round(education_target),
        "education_sip": education_sip,
        "added_monthly_cost": rounded_monthly_cost,
        "remaining_surplus": round(idle_surplus - total_monthly_pressure),
        "affordability": affordability(total_monthly_pressure, idle_surplus),
    }


def _emergency_goal_changes(
    goals: list[dict],
    protected_goal_names: set[str],
    delay_months: int,
) -> list[dict]:
    """Return a temporary pause proposal without mutating the live plan."""
    changes = []
    for goal in goals:
        before_sip = float(goal.get("required_sip") or 0)
        name = str(goal.get("name") or "")
        protected = name.lower() in protected_goal_names or before_sip <= 0
        before_horizon = int(goal.get("horizon_years") or 0)
        after_horizon = (
            before_horizon
            if protected
            else math.ceil((before_horizon * 12 + delay_months) / 12)
        )
        changes.append({
            "name": name,
            "before_sip": round(before_sip),
            "after_sip": round(before_sip if protected else 0),
            "before_horizon_years": before_horizon,
            "after_horizon_years": after_horizon,
            "delay_months": 0 if protected else delay_months,
            "status": "protected" if protected else "paused",
        })
    return changes


def simulate_income_emergency(
    *,
    monthly_income_after: float,
    duration_months: int,
    essential_outflow: float,
    liquid_reserve: float,
    goals: list[dict],
    protected_goal_names: set[str],
) -> dict:
    """Restructure goal SIPs around a temporary loss of monthly income."""
    changes = _emergency_goal_changes(
        goals,
        protected_goal_names,
        duration_months,
    )
    protected_sip = sum(
        item["after_sip"]
        for item in changes
        if item["status"] == "protected"
    )
    monthly_draw = max(
        0.0,
        essential_outflow + protected_sip - monthly_income_after,
    )
    reserve_required = monthly_draw * duration_months
    reserve_gap = max(0.0, reserve_required - liquid_reserve)
    runway_months = (
        round(liquid_reserve / monthly_draw, 1)
        if monthly_draw > 0
        else None
    )
    return {
        "monthly_income_after": round(monthly_income_after),
        "duration_months": duration_months,
        "essential_outflow": round(essential_outflow),
        "liquid_reserve": round(liquid_reserve),
        "monthly_draw": round(monthly_draw),
        "reserve_required": round(reserve_required),
        "reserve_gap": round(reserve_gap),
        "runway_months": runway_months,
        "monthly_freed": sum(
            item["before_sip"] - item["after_sip"] for item in changes
        ),
        "goal_changes": changes,
        "status": "viable" if reserve_gap <= 0 else "needs_adjustment",
    }


def plan_runway_extensions(
    *,
    liquid_cash: float,
    monthly_draw: float,
    holdings: list[dict],
    target_months: tuple[int, ...] = (12, 18),
) -> dict:
    """Build tax-aware-instruction-ready fund withdrawals for longer runway.

    The ordering is intentional: clean up flagged holdings first, use liquid and
    short-duration debt next, and disturb suitable core equity only as a last
    resort. Tax itself is not estimated here.
    """

    def withdrawal_priority(holding: dict) -> tuple:
        category = str(holding.get("category") or "").lower()
        fund = str(holding.get("fund") or "").lower()
        if holding.get("flag") == "underperformer":
            return (0, int(holding.get("rating") or 0))
        if "liquid" in category or "liquid" in fund:
            return (1, 0)
        if holding.get("type") == "debt":
            return (2, 0)
        return (3, -int(holding.get("rating") or 0))

    def rationale(holding: dict) -> str:
        category = str(holding.get("category") or "").lower()
        fund = str(holding.get("fund") or "").lower()
        if holding.get("flag") == "underperformer":
            return "Exit this weaker holding before disturbing stronger core funds."
        if "liquid" in category or "liquid" in fund:
            return "Already low-volatility and quick to convert into runway."
        if holding.get("type") == "debt":
            return "Use lower-volatility debt before selling suitable core equity."
        return "Use only after weaker and lower-volatility holdings are exhausted."

    ordered_holdings = sorted(
        (
            holding
            for holding in holdings
            if float(holding.get("current_value") or 0) > 0
        ),
        key=withdrawal_priority,
    )
    options = []
    for months in target_months:
        target_cash = monthly_draw * months
        additional_required = max(0.0, target_cash - liquid_cash)
        remaining = additional_required
        withdrawals = []
        for holding in ordered_holdings:
            if remaining <= 0:
                break
            amount = min(float(holding["current_value"]), remaining)
            if amount <= 0:
                continue
            withdrawals.append({
                "fund": holding["fund"],
                "amount": round(amount),
                "available_value": round(float(holding["current_value"])),
                "rationale": rationale(holding),
            })
            remaining -= amount
        options.append({
            "target_months": months,
            "target_liquid_cash": round(target_cash),
            "additional_required": round(additional_required),
            "withdrawals": withdrawals,
            "remaining_gap": round(max(0.0, remaining)),
            "fully_fundable": remaining <= 0,
        })
    return {
        "current_liquid_cash": round(liquid_cash),
        "current_runway_months": (
            round(liquid_cash / monthly_draw, 1)
            if monthly_draw > 0
            else None
        ),
        "options": options,
        "execution_note": (
            "Before redeeming, use units held beyond the applicable exit-load and tax "
            "period first, and verify the final order with a regulated adviser."
        ),
    }


def simulate_urgent_cost(
    *,
    one_time_cost: float,
    recovery_months: int,
    liquid_reserve: float,
    idle_surplus: float,
    goals: list[dict],
    protected_goal_names: set[str],
) -> dict:
    """Fund an urgent cost and show the temporary goal pause needed to recover."""
    changes = _emergency_goal_changes(
        goals,
        protected_goal_names,
        recovery_months,
    )
    reserve_used = min(one_time_cost, liquid_reserve)
    immediate_gap = max(0.0, one_time_cost - liquid_reserve)
    monthly_freed = sum(
        item["before_sip"] - item["after_sip"] for item in changes
    )
    monthly_rebuild_needed = reserve_used / recovery_months
    recovery_capacity = idle_surplus + monthly_freed
    return {
        "one_time_cost": round(one_time_cost),
        "recovery_months": recovery_months,
        "liquid_reserve": round(liquid_reserve),
        "reserve_used": round(reserve_used),
        "reserve_after": round(liquid_reserve - reserve_used),
        "immediate_gap": round(immediate_gap),
        "monthly_rebuild_needed": round_to_500(monthly_rebuild_needed),
        "monthly_recovery_capacity": round(recovery_capacity),
        "monthly_freed": round(monthly_freed),
        "goal_changes": changes,
        "status": (
            "viable"
            if immediate_gap <= 0 and monthly_rebuild_needed <= recovery_capacity
            else "needs_adjustment"
        ),
    }


def lumpsum_fv(present_value: float, annual_rate: float, years: float) -> float:
    """FV of a lumpsum: PV × (1 + g)^n."""
    return present_value * (1 + annual_rate) ** years


def sip_fv(monthly_sip: float, annual_rate: float, years: float) -> float:
    """FV of a monthly SIP (annuity-due): sip × [((1+r)^(12n) − 1) / r] × (1+r), r = annual/12."""
    if monthly_sip <= 0:
        return 0.0
    r = annual_rate / 12
    m = 12 * years
    return monthly_sip * (((1 + r) ** m - 1) / r) * (1 + r)


def required_sip(target: float, annual_rate: float, years: float) -> float:
    """Monthly SIP needed to reach target: target × r / (((1+r)^(12n) − 1) × (1+r))."""
    if target <= 0:
        return 0.0
    r = annual_rate / 12
    m = 12 * years
    return target * r / ((((1 + r) ** m) - 1) * (1 + r))


def years_to_target(monthly_sip: float, target: float, annual_rate: float) -> float:
    """Solve the SIP FV formula for n (in years, 1 decimal) given a fixed SIP."""
    if target <= 0:
        return 0.0
    if monthly_sip <= 0:
        return math.inf
    r = annual_rate / 12
    months = math.log(target * r / (monthly_sip * (1 + r)) + 1) / math.log(1 + r)
    return round(months / 12, 1)


def blended_growth(equity_value: float, debt_value: float) -> float:
    """Value-weighted growth rate across equity and debt holdings."""
    total = equity_value + debt_value
    if total <= 0:
        return DEBT_GROWTH
    return (equity_value * EQUITY_GROWTH + debt_value * DEBT_GROWTH) / total


def affordability(required: float, idle_surplus: float) -> str:
    """comfortable (≤70% of surplus) / tight (70–100%) / unaffordable (>100%)."""
    if idle_surplus <= 0:
        return "unaffordable"
    ratio = required / idle_surplus
    if ratio <= 0.70:
        return "comfortable"
    if ratio <= 1.0:
        return "tight"
    return "unaffordable"


# Deterministic risk scoring for the 2-question flow. Each free-text answer
# scores -1 (conservative), 0 (balanced), or +1 (aggressive) by keyword match;
# conservative keywords win ties within an answer. Threshold is ±1 because with
# only 2 questions a single strong tilt should move the user off balanced.
#   total >= 1 -> aggressive, total <= -1 -> conservative, else balanced.
# Ambiguous words ("steady", "growth", "stable") are intentionally excluded —
# they appear in both Q1 neutral phrasing and Q2 conservative/aggressive
# phrasing and would misclassify.
_AGGRESSIVE_KW = ("top up", "topup", "buy more", "invest more", "add more", "buy the dip",
                  "opportunity", "double down", "lump sum",
                  "maximize", "maximise", "max returns", "highest returns", "aggressive")
_CONSERVATIVE_KW = ("exit", "sell", "withdraw", "redeem", "stop", "panic", "scared",
                    "afraid", "worried", "worry", "fd", "fixed deposit", "safe", "pull out",
                    "protect", "preserve", "conservative", "low risk", "low-risk")


def score_risk_answer(answer: str) -> int:
    a = answer.lower()
    if any(k in a for k in _CONSERVATIVE_KW):
        return -1
    if any(k in a for k in _AGGRESSIVE_KW):
        return 1
    return 0


def horizon_bucket(years: int) -> str:
    """Categorize a goal by years-to-target: short / medium / long."""
    if years <= HORIZON_SHORT_MAX:
        return "short"
    if years <= HORIZON_MEDIUM_MAX:
        return "medium"
    return "long"


def build_phases(bucket: str, horizon_years: int, monthly_sip: float) -> list[dict]:
    """Per-goal phase plan: each phase has duration, allocation, fund-level SIPs.

    Phase durations are rounded to whole years; the last phase absorbs rounding
    so durations sum exactly to horizon_years.
    """
    plan = PHASE_PLAN[bucket]
    phases = []
    accumulated = 0
    for i, (frac, eq, debt, gold) in enumerate(plan, start=1):
        if i == len(plan):
            years_in_phase = max(1, horizon_years - accumulated)
        else:
            years_in_phase = max(1, round(frac * horizon_years))
            accumulated += years_in_phase
        funds = []
        for sub_bucket, share in (("equity", eq), ("debt", debt), ("gold", gold)):
            if share <= 0:
                continue
            for name, weight, rationale in FUND_PALETTE[sub_bucket]:
                sip = round_to_500(monthly_sip * share * weight)
                if sip <= 0:
                    continue
                funds.append({"fund": name, "bucket": sub_bucket,
                              "monthly_sip": sip, "rationale": rationale})
        phases.append({
            "phase": i,
            "duration_years": years_in_phase,
            "allocation": {"equity": eq, "debt": debt, "gold": gold},
            "funds": funds,
        })
    return phases


def risk_profile_from_answers(answers: list[str]) -> dict:
    total = sum(score_risk_answer(a) for a in answers)
    if total >= 1:
        profile = "aggressive"
    elif total <= -1:
        profile = "conservative"
    else:
        profile = "balanced"
    return {
        "risk_profile": profile,
        "score": total,
        "equity_band": EQUITY_BAND[profile],
        "expected_return": EXPECTED_RETURN[profile],
    }
