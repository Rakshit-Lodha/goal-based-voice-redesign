import asyncio

from core import session
from core.call_memory import CallMemoryFinalizer, prepare_call_memory
from core.conversation_store import ConversationStore
from core.run_transcript import RunTranscriptRecorder
from core.session import STATE
from agent import tools


def _save_memory(store: ConversationStore, *, completed: bool = False):
    initial = session.export_state()
    STATE.risk_profile = "balanced"
    if completed:
        STATE.plan_pdf_path = None
    current = session.export_state()
    saved = store.save_checkpoint(
        user_id="rakshit",
        conversation_id="saved",
        transcript={
            "created_at": "now",
            "events": [{"type": "message", "role": "user", "text": "Continue my plan"}],
        },
        state_payload=current,
        initial_state_payload=initial,
    )
    assert saved
    if completed:
        summary_path = saved.directory / "summary.json"
        summary = store._read_json(summary_path)
        summary["completed_plan"] = True
        summary["headline"] = "Review or update your wealth plan"
        store.replace_summary(saved, summary)
    return saved


def test_fresh_mode_resets_even_when_memory_exists(tmp_path):
    store = ConversationStore(tmp_path)
    _save_memory(store)
    STATE.risk_profile = "aggressive"

    context = prepare_call_memory(
        memory_mode="fresh",
        user_id="rakshit",
        conversation_id="new",
        store=store,
    )

    assert context.resumed is False
    assert STATE.risk_profile is None
    assert STATE.name == session.KYC_NAME


def test_resume_restores_state_and_sets_return_gate(tmp_path):
    store = ConversationStore(tmp_path)
    _save_memory(store)
    session.reset()

    context = prepare_call_memory(
        memory_mode="resume",
        user_id="rakshit",
        conversation_id="new",
        store=store,
    )

    assert context.resumed is True
    assert STATE.risk_profile == "balanced"
    assert STATE.is_returning_session is True
    assert STATE.resume_confirmed is False
    assert "do not call any tool" in context.greeting_instruction.lower()
    assert "confirm_resume" in session.next_step()


def test_resume_without_memory_falls_back_fresh(tmp_path):
    context = prepare_call_memory(
        memory_mode="resume",
        user_id="rakshit",
        conversation_id="new",
        store=ConversationStore(tmp_path),
    )

    assert context.mode == "fresh"
    assert context.resumed is False
    assert STATE.risk_profile is None


def test_completed_resume_uses_review_opening(tmp_path):
    store = ConversationStore(tmp_path)
    _save_memory(store, completed=True)

    context = prepare_call_memory(
        memory_mode="resume",
        user_id="rakshit",
        conversation_id="new",
        store=store,
    )
    STATE.resume_confirmed = True

    assert context.resumed is True
    assert STATE.resume_completed_plan is True
    assert "what has changed" in session.next_step().lower()


def test_finalizer_saves_only_once(tmp_path):
    async def run():
        store = ConversationStore(tmp_path)
        context = prepare_call_memory(
            memory_mode="fresh",
            user_id="rakshit",
            conversation_id="new",
            store=store,
        )
        STATE.risk_profile = "balanced"
        recorder = RunTranscriptRecorder(output_dir=str(tmp_path / "transcripts"))
        recorder.add_user_transcript("I want a balanced plan")
        finalizer = CallMemoryFinalizer(store=store, context=context, recorder=recorder)

        first = finalizer.save_once()
        second = finalizer.save_once()
        if finalizer.summary_task:
            await finalizer.summary_task

        assert first is second
        assert len(list((tmp_path / "rakshit").glob("*/state.json"))) == 1

    asyncio.run(run())


def test_successful_state_changing_tool_result_makes_checkpoint_meaningful(tmp_path):
    async def run():
        store = ConversationStore(tmp_path)
        context = prepare_call_memory(
            memory_mode="fresh",
            user_id="rakshit",
            conversation_id="tool_change",
            store=store,
        )
        recorder = RunTranscriptRecorder(output_dir=str(tmp_path / "transcripts"))
        recorder.add_user_transcript("Save this update")
        recorder.add_tool_result("assess_risk_profile", {"risk_profile": "balanced"})
        finalizer = CallMemoryFinalizer(store=store, context=context, recorder=recorder)

        checkpoint = finalizer.save_once()
        if finalizer.summary_task:
            await finalizer.summary_task

        assert checkpoint is not None
        assert store.load_latest("rakshit").conversation_id == "tool_change"

    asyncio.run(run())


def test_resume_confirmation_releases_gate():
    session.reset()
    STATE.is_returning_session = True

    result = asyncio.run(tools.confirm_resume({"user_confirmed": True, "choice": "continue"}))

    assert result["resume_confirmed"] is True
    assert STATE.resume_confirmed is True
    assert "confirm_resume" not in result["next_step"]


def test_restored_provider_data_requires_new_consent_for_refresh():
    session.reset()
    STATE.portfolio = {"total_monthly_sip": 0}
    STATE.aa_assets = {"epf": 1, "nps": 2, "stocks": 3}
    STATE.restored_financial_data = True

    result = asyncio.run(tools.pull_account_aggregator({}))

    assert result["error"] == "missing: Account Aggregator consent"
    assert STATE.restored_financial_data is True
