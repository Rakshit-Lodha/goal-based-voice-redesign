import asyncio

from agent import tools
from core import session
from core.call_memory import CallMemoryFinalizer, prepare_call_memory
from core.conversation_store import ConversationStore
from core.run_transcript import RunTranscriptRecorder
from core.session import STATE


def _run(coro):
    return asyncio.run(coro)


def _simulator_context(tmp_path):
    return prepare_call_memory(
        memory_mode="simulator",
        user_id="rakshit",
        conversation_id="simulator",
        store=ConversationStore(tmp_path),
    )


def test_simulator_mode_seeds_a_complete_pre_goal_profile(tmp_path):
    context = _simulator_context(tmp_path)

    assert context.mode == "simulator"
    assert context.resumed is False
    assert STATE.is_simulator_session is True
    assert STATE.risk_profile == "balanced"
    assert STATE.family == {
        "spouse_age": 25,
        "children": [],
        "dependents_count": 0,
    }
    assert STATE.portfolio["total_value"] == 1_800_000
    assert STATE.aa_assets == {"epf": 450_000, "nps": 50_000, "stocks": 500_000}
    assert STATE.financial_snapshot_confirmed is True
    assert STATE.ratios["idle_surplus"] == 40_000
    assert "choose_experience" in session.next_step()
    assert "financial decision simulator" in context.greeting_instruction.lower()


def test_simulator_call_never_replaces_cross_session_memory(tmp_path):
    store = ConversationStore(tmp_path)
    context = prepare_call_memory(
        memory_mode="simulator",
        user_id="rakshit",
        conversation_id="simulator",
        store=store,
    )
    recorder = RunTranscriptRecorder(output_dir=str(tmp_path / "transcripts"))
    recorder.add_user_transcript("Use the decision simulator")
    recorder.add_tool_result("choose_experience", {"choice": "simulator"})

    finalizer = CallMemoryFinalizer(store=store, context=context, recorder=recorder)

    assert finalizer.save_once() is None
    assert store.load_latest("rakshit") is None


def test_simulator_choice_opens_scenario_menu(monkeypatch, tmp_path):
    emitted = []

    async def capture_artifact(kind, data):
        emitted.append((kind, data))

    _simulator_context(tmp_path)
    monkeypatch.setattr(tools.ui_bus, "emit_artifact", capture_artifact)

    result = _run(tools.choose_experience({"choice": "decision simulator"}))

    assert result["choice"] == "simulator"
    assert STATE.simulator_choice == "simulator"
    assert emitted[0][0] == "simulator_menu"
    assert len(emitted[0][1]["scenarios"]) == 3
    assert "career break" in result["next_step"]


def test_traditional_choice_skips_directly_to_goals(monkeypatch, tmp_path):
    emitted = []

    async def capture_artifact(kind, data):
        emitted.append((kind, data))

    _simulator_context(tmp_path)
    monkeypatch.setattr(tools.ui_bus, "emit_artifact", capture_artifact)

    result = _run(tools.choose_experience({"choice": "traditional goals"}))

    assert result["choice"] == "traditional"
    assert emitted[0][0] == "goal_types_picker"
    assert "which traditional goal" in result["next_step"].lower()
    assert "ask the two behavioral" not in result["next_step"].lower()
    assert "trigger the otp" not in result["next_step"].lower()


def test_career_break_simulation_is_deterministic_and_non_mutating(monkeypatch, tmp_path):
    emitted = []

    async def capture_artifact(kind, data):
        emitted.append((kind, data))

    _simulator_context(tmp_path)
    _run(tools.choose_experience({"choice": "simulator"}))
    monkeypatch.setattr(tools.ui_bus, "emit_artifact", capture_artifact)
    persistent_before = session.export_state()

    result = _run(tools.simulate_life_event({
        "event_type": "career_break",
        "duration_months": 12,
        "starts_in_months": 24,
        "income_reduction_percent": 100,
    }))

    assert result["scenario"]["reserve_required"] == 900_000
    assert result["scenario"]["additional_reserve"] == 460_000
    assert result["scenario"]["monthly_reserve_build"] == 19_000
    assert result["status"] == "viable"
    assert emitted[0][0] == "scenario_comparison"
    assert session.export_state() == persistent_before


def test_home_and_family_simulations_return_before_after_tradeoffs(tmp_path):
    _simulator_context(tmp_path)
    _run(tools.choose_experience({"choice": "simulator"}))

    home = _run(tools.simulate_life_event({
        "event_type": "home_timing",
        "goal_amount_today": 10_000_000,
        "current_horizon_years": 5,
        "proposed_horizon_years": 8,
    }))
    family = _run(tools.simulate_life_event({
        "event_type": "starting_family",
        "child_arrival_years": 2,
        "added_monthly_cost": 15_000,
        "education_cost_today": 3_000_000,
    }))

    assert home["scenario"]["current"]["required_sip"] > 0
    assert home["scenario"]["proposed"]["required_sip"] > 0
    assert len(home["comparisons"]) == 3
    assert family["scenario"]["education_horizon_years"] == 20
    assert family["scenario"]["education_sip"] > 0
    assert len(family["comparisons"]) == 3


def test_simulation_requires_explicit_scenario_inputs(tmp_path):
    _simulator_context(tmp_path)
    _run(tools.choose_experience({"choice": "simulator"}))

    result = _run(tools.simulate_life_event({
        "event_type": "home_timing",
        "goal_amount_today": 10_000_000,
    }))

    assert result["error"] == "missing: the home scenario amount and two timelines"
