import asyncio

from agent import tools
from core import session
from core.call_memory import CallMemoryFinalizer, prepare_call_memory
from core.conversation_store import ConversationStore
from core.run_transcript import RunTranscriptRecorder
from core.session import STATE


def _run(coro):
    return asyncio.run(coro)


def _emergency_context(tmp_path):
    return prepare_call_memory(
        memory_mode="emergency",
        user_id="rakshit",
        conversation_id="emergency",
        store=ConversationStore(tmp_path),
    )


def test_emergency_mode_loads_a_completed_plan_and_exact_opening(tmp_path):
    context = _emergency_context(tmp_path)

    assert context.mode == "emergency"
    assert context.resumed is False
    assert STATE.is_emergency_session is True
    assert STATE.is_simulator_session is False
    assert [goal.name for goal in STATE.goals] == [
        "Emergency fund",
        "Buy a house in Pune",
        "Daughter's education",
    ]
    assert sum(goal.required_sip or 0 for goal in STATE.goals) == 60_000
    assert set(STATE.proposed_portfolios) == {
        "Buy a house in Pune",
        "Daughter's education",
    }
    assert "What's up, Rakshit? What's the emergency?" in context.greeting_instruction
    assert "analyze_financial_emergency" in session.next_step()
    assert "is_emergency_session" not in session.export_state()["state"]


def test_emergency_call_never_replaces_cross_session_memory(tmp_path):
    store = ConversationStore(tmp_path)
    context = prepare_call_memory(
        memory_mode="emergency",
        user_id="rakshit",
        conversation_id="emergency",
        store=store,
    )
    recorder = RunTranscriptRecorder(output_dir=str(tmp_path / "transcripts"))
    recorder.add_user_transcript("I lost my job")

    finalizer = CallMemoryFinalizer(store=store, context=context, recorder=recorder)

    assert finalizer.save_once() is None
    assert store.load_latest("rakshit") is None


def test_income_shock_reworks_every_unprotected_goal(monkeypatch, tmp_path):
    emitted = []

    async def capture_artifact(kind, data):
        emitted.append((kind, data))

    _emergency_context(tmp_path)
    monkeypatch.setattr(tools.ui_bus, "emit_artifact", capture_artifact)

    result = _run(tools.analyze_financial_emergency({
        "emergency_type": "income_shock",
        "description": "I lost my job",
        "monthly_income_after": 0,
        "duration_months": 6,
    }))

    assert result["status"] == "viable"
    assert result["scenario"]["monthly_freed"] == 60_000
    assert result["scenario"]["reserve_required"] == 450_000
    assert result["scenario"]["reserve_gap"] == 0
    assert result["scenario"]["runway_months"] == 7.6
    assert result["emotional_tone"] == "job_loss"
    assert result["supportive_opening"].startswith("I am really sorry")
    assert [step["label"] for step in result["guidance_steps"]] == [
        "Protect what keeps life running",
        "Make goals flexible, not abandoned",
        "Use the reserve with checkpoints",
    ]
    runway = result["runway_plan"]
    assert runway["current_liquid_cash"] == 570_000
    assert runway["current_runway_months"] == 7.6
    twelve, eighteen = runway["options"]
    assert twelve["additional_required"] == 330_000
    assert [(item["fund"], item["amount"]) for item in twelve["withdrawals"]] == [
        ("ICICI Prudential Infrastructure Fund", 150_000),
        ("Quant Mid Cap Fund", 180_000),
    ]
    assert eighteen["additional_required"] == 780_000
    assert [(item["fund"], item["amount"]) for item in eighteen["withdrawals"]] == [
        ("ICICI Prudential Infrastructure Fund", 150_000),
        ("Quant Mid Cap Fund", 280_000),
        ("HDFC Liquid Fund", 150_000),
        ("HDFC Short Term Debt Fund", 200_000),
    ]
    assert result["recommended_runway_months"] == 12
    assert "missing" not in result
    assert [item["status"] for item in result["goal_changes"]] == [
        "protected",
        "paused",
        "paused",
    ]
    assert emitted[0][0] == "emergency_shockwave"
    assert STATE.goals[1].required_sip == 50_500


def test_user_can_protect_a_goal_and_renegotiate(tmp_path):
    _emergency_context(tmp_path)

    result = _run(tools.analyze_financial_emergency({
        "emergency_type": "income_shock",
        "description": "I lost my job",
        "monthly_income_after": 0,
        "duration_months": 6,
        "protected_goal_names": ["Daughter's education"],
    }))

    changes = {item["name"]: item for item in result["goal_changes"]}
    assert changes["Daughter's education"]["status"] == "protected"
    assert changes["Daughter's education"]["after_sip"] == 9_500
    assert changes["Buy a house in Pune"]["after_sip"] == 0
    assert result["scenario"]["monthly_freed"] == 50_500
    assert result["scenario"]["runway_months"] == 6.7


def test_urgent_cost_uses_reserve_and_builds_it_back(tmp_path):
    _emergency_context(tmp_path)

    result = _run(tools.analyze_financial_emergency({
        "emergency_type": "urgent_cost",
        "description": "I need money for an urgent treatment",
        "one_time_cost": 300_000,
        "recovery_months": 6,
    }))

    assert result["status"] == "viable"
    assert result["scenario"]["reserve_after"] == 270_000
    assert result["scenario"]["monthly_rebuild_needed"] == 50_000
    assert result["scenario"]["monthly_recovery_capacity"] == 100_000


def test_new_child_is_congratulated_before_any_number_is_requested(tmp_path):
    _emergency_context(tmp_path)

    result = _run(tools.analyze_financial_emergency({
        "emergency_type": "new_child",
        "description": "We just had a baby",
    }))

    assert result["emotional_tone"] == "celebratory"
    assert result["supportive_opening"].startswith("Congratulations")
    assert result["proposal_ready"] is False
    assert result["comparisons"] == []
    assert [step["label"] for step in result["guidance_steps"]] == [
        "Protect the family first",
        "Reset the monthly rhythm",
        "Then fund the future",
    ]
    assert "which area feels most urgent" in result["next_step"].lower()
    premature = _run(tools.commit_emergency_plan({"action": "accept"}))
    assert premature["error"] == "missing: a calculated emergency proposal"


def test_accept_and_undo_are_explicit_and_reversible(tmp_path):
    _emergency_context(tmp_path)
    _run(tools.analyze_financial_emergency({
        "emergency_type": "income_shock",
        "description": "I lost my job",
        "monthly_income_after": 0,
        "duration_months": 6,
    }))

    accepted = _run(tools.commit_emergency_plan({"action": "accept"}))

    assert accepted["applied"] is True
    assert STATE.emergency_plan_applied is True
    assert STATE.goals[1].required_sip == 0
    assert STATE.goals[1].horizon_years == 11
    assert STATE.goals[2].required_sip == 0
    assert STATE.proposed_portfolios == {}

    undone = _run(tools.commit_emergency_plan({"action": "undo"}))

    assert undone["undone"] is True
    assert STATE.emergency_plan_applied is False
    assert STATE.goals[1].required_sip == 50_500
    assert STATE.goals[1].horizon_years == 10
    assert STATE.goals[2].required_sip == 9_500
    assert set(STATE.proposed_portfolios) == {
        "Buy a house in Pune",
        "Daughter's education",
    }


def test_emergency_analysis_requires_explicit_numbers(tmp_path):
    _emergency_context(tmp_path)

    result = _run(tools.analyze_financial_emergency({
        "emergency_type": "income_shock",
        "description": "My income stopped",
    }))

    assert result["error"] == "missing: the new monthly income and duration"
