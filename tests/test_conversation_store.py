import json

import pytest

from core import session
from core.conversation_store import ConversationStore
from core.session import STATE


def _transcript(text: str = "I want to plan for a home") -> dict:
    return {
        "created_at": "2026-07-26T05:00:00+00:00",
        "events": [{"type": "message", "role": "user", "text": text}],
    }


def _meaningful_state() -> tuple[dict, dict]:
    initial = session.export_state()
    STATE.risk_profile = "balanced"
    STATE.risk_answers = ["hold", "balanced growth"]
    return initial, session.export_state()


def test_meaningful_save_creates_complete_checkpoint_and_loads_it(tmp_path):
    store = ConversationStore(tmp_path)
    initial, current = _meaningful_state()

    saved = store.save_checkpoint(
        user_id="rakshit",
        conversation_id="conversation_one",
        transcript=_transcript(),
        state_payload=current,
        initial_state_payload=initial,
    )

    assert saved is not None
    assert (saved.directory / "transcript.json").exists()
    assert (saved.directory / "state.json").exists()
    assert (saved.directory / "summary.json").exists()
    assert (tmp_path / "rakshit" / "latest.json").exists()
    loaded = store.load_latest("rakshit")
    assert loaded is not None
    assert loaded.state_payload == current
    assert loaded.summary["status"] == "fallback"
    assert "state" not in loaded.summary


def test_two_saves_create_distinct_directories(tmp_path):
    store = ConversationStore(tmp_path)
    initial, current = _meaningful_state()

    first = store.save_checkpoint(
        user_id="rakshit",
        conversation_id="first",
        transcript=_transcript(),
        state_payload=current,
        initial_state_payload=initial,
    )
    second = store.save_checkpoint(
        user_id="rakshit",
        conversation_id="second",
        transcript=_transcript(),
        state_payload=current,
        initial_state_payload=initial,
        successful_state_change=True,
    )

    assert first and second
    assert first.directory != second.directory


def test_non_meaningful_save_does_not_advance_latest(tmp_path):
    store = ConversationStore(tmp_path)
    initial, current = _meaningful_state()
    first = store.save_checkpoint(
        user_id="rakshit",
        conversation_id="meaningful",
        transcript=_transcript(),
        state_payload=current,
        initial_state_payload=initial,
    )
    pointer_before = (tmp_path / "rakshit" / "latest.json").read_text()

    ignored = store.save_checkpoint(
        user_id="rakshit",
        conversation_id="greeting",
        transcript=_transcript("Okay"),
        state_payload=current,
        initial_state_payload=current,
    )

    assert first is not None
    assert ignored is None
    assert (tmp_path / "rakshit" / "latest.json").read_text() == pointer_before
    assert store.load_latest("rakshit").conversation_id == "meaningful"


@pytest.mark.parametrize(
    "user_id",
    ["../rakshit", "rakshit/other", "rakshit%2Fother", "", "rakshit space"],
)
def test_invalid_user_ids_cannot_escape_store(tmp_path, user_id):
    store = ConversationStore(tmp_path)

    with pytest.raises(ValueError):
        store.load_latest(user_id)


def test_missing_or_corrupt_pointer_returns_no_memory(tmp_path):
    store = ConversationStore(tmp_path)
    assert store.load_latest("rakshit") is None
    pointer = tmp_path / "rakshit" / "latest.json"
    pointer.parent.mkdir(parents=True)
    pointer.write_text("{not json", encoding="utf-8")

    assert store.load_latest("rakshit") is None


def test_pointer_to_missing_or_corrupt_state_returns_no_memory(tmp_path):
    store = ConversationStore(tmp_path)
    initial, current = _meaningful_state()
    saved = store.save_checkpoint(
        user_id="rakshit",
        conversation_id="broken",
        transcript=_transcript(),
        state_payload=current,
        initial_state_payload=initial,
    )
    assert saved
    (saved.directory / "state.json").write_text("{bad", encoding="utf-8")

    assert store.load_latest("rakshit") is None


def test_pointer_to_missing_directory_returns_no_memory(tmp_path):
    store = ConversationStore(tmp_path)
    pointer = tmp_path / "rakshit" / "latest.json"
    pointer.parent.mkdir(parents=True)
    pointer.write_text(json.dumps({
        "schema_version": 1,
        "conversation_id": "missing",
        "checkpoint_directory": "missing_directory",
        "saved_at": "now",
    }), encoding="utf-8")

    assert store.load_latest("rakshit") is None


def test_latest_pointer_is_valid_complete_json(tmp_path):
    store = ConversationStore(tmp_path)
    initial, current = _meaningful_state()
    store.save_checkpoint(
        user_id="rakshit",
        conversation_id="atomic",
        transcript=_transcript(),
        state_payload=current,
        initial_state_payload=initial,
    )

    pointer = json.loads((tmp_path / "rakshit" / "latest.json").read_text())
    assert pointer["schema_version"] == 1
    assert pointer["conversation_id"] == "atomic"
