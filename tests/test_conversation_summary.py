import asyncio

from core import session
from core.conversation_store import ConversationStore
from core.conversation_summary import enhance_checkpoint_summary
from core.session import STATE


def _checkpoint(tmp_path, *, user_text: str = "I need to confirm the home budget"):
    store = ConversationStore(tmp_path)
    initial = session.export_state()
    STATE.risk_profile = "balanced"
    current = session.export_state()
    saved = store.save_checkpoint(
        user_id="rakshit",
        conversation_id="summary",
        transcript={
            "created_at": "now",
            "events": (
                [{"type": "message", "role": "user", "text": user_text}]
                if user_text
                else []
            ),
        },
        state_payload=current,
        initial_state_payload=initial,
    )
    assert saved
    return store, saved


def _valid_summary():
    return {
        "headline": "Continue your home plan",
        "card_summary": "You paused to confirm the home budget with your spouse.",
        "conversation_summary": "Rakshit corrected the earlier home target and kept the goal active.",
        "decisions": ["The corrected home target replaces the earlier target."],
        "open_items": ["Confirm the home budget with the spouse."],
        "recommended_next_start": "Welcome Rakshit back and ask whether the home budget was confirmed.",
        "completed_plan": False,
    }


def test_valid_llm_summary_replaces_fallback(tmp_path):
    store, saved = _checkpoint(tmp_path)

    async def fake(_request):
        return _valid_summary()

    assert asyncio.run(enhance_checkpoint_summary(store, saved, llm_call=fake))
    summary = store._read_json(saved.directory / "summary.json")
    assert summary["status"] == "ready"
    assert summary["open_items"] == ["Confirm the home budget with the spouse."]


def test_invalid_json_or_missing_fields_retains_fallback(tmp_path):
    store, saved = _checkpoint(tmp_path)
    before = store._read_json(saved.directory / "summary.json")

    async def fake(_request):
        return "{bad json"

    assert not asyncio.run(enhance_checkpoint_summary(store, saved, llm_call=fake))
    assert store._read_json(saved.directory / "summary.json") == before


def test_missing_required_summary_fields_retain_fallback(tmp_path):
    store, saved = _checkpoint(tmp_path)
    before = store._read_json(saved.directory / "summary.json")

    async def fake(_request):
        return {"headline": "Continue your plan"}

    assert not asyncio.run(enhance_checkpoint_summary(store, saved, llm_call=fake))
    assert store._read_json(saved.directory / "summary.json") == before


def test_timeout_or_provider_exception_retains_fallback(tmp_path):
    store, saved = _checkpoint(tmp_path)
    before = store._read_json(saved.directory / "summary.json")

    async def slow(_request):
        await asyncio.sleep(0.02)
        return _valid_summary()

    assert not asyncio.run(
        enhance_checkpoint_summary(store, saved, llm_call=slow, timeout_seconds=0.001)
    )
    assert store._read_json(saved.directory / "summary.json") == before


def test_provider_exception_retains_fallback(tmp_path):
    store, saved = _checkpoint(tmp_path)
    before = store._read_json(saved.directory / "summary.json")

    async def failing(_request):
        raise RuntimeError("provider unavailable")

    assert not asyncio.run(enhance_checkpoint_summary(store, saved, llm_call=failing))
    assert store._read_json(saved.directory / "summary.json") == before


def test_summarizer_input_cannot_mutate_saved_state(tmp_path):
    store, saved = _checkpoint(tmp_path)
    state_before = store._read_json(saved.directory / "state.json")

    async def mutating(request):
        request["authoritative_state"]["risk_profile"] = "mutated"
        return _valid_summary()

    assert asyncio.run(enhance_checkpoint_summary(store, saved, llm_call=mutating))
    assert store._read_json(saved.directory / "state.json") == state_before


def test_sensitive_card_or_reused_consent_is_rejected(tmp_path):
    store, saved = _checkpoint(tmp_path)

    async def sensitive(_request):
        value = _valid_summary()
        value["card_summary"] = "Your holdings are ₹12,00,000."
        return value

    assert not asyncio.run(enhance_checkpoint_summary(store, saved, llm_call=sensitive))

    async def stale_consent(_request):
        value = _valid_summary()
        value["recommended_next_start"] = "Tell them their consent is still valid."
        return value

    assert not asyncio.run(enhance_checkpoint_summary(store, saved, llm_call=stale_consent))
    assert store._read_json(saved.directory / "summary.json")["status"] == "fallback"


def test_empty_transcript_is_not_summarized(tmp_path):
    store, saved = _checkpoint(tmp_path, user_text="")
    called = False

    async def fake(_request):
        nonlocal called
        called = True
        return _valid_summary()

    assert not asyncio.run(enhance_checkpoint_summary(store, saved, llm_call=fake))
    assert called is False
