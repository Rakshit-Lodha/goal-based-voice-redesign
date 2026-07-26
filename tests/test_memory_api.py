import asyncio

from fastapi.testclient import TestClient

import server
from core import session
from core.conversation_store import ConversationStore
from core.session import STATE


def _save_checkpoint(store: ConversationStore, *, completed: bool = False):
    initial = session.export_state()
    STATE.risk_profile = "balanced"
    current = session.export_state()
    saved = store.save_checkpoint(
        user_id="rakshit",
        conversation_id="api_memory",
        transcript={
            "created_at": "now",
            "events": [{"type": "message", "role": "user", "text": "Save my plan"}],
        },
        state_payload=current,
        initial_state_payload=initial,
    )
    assert saved
    if completed:
        summary = store._read_json(saved.directory / "summary.json")
        summary["completed_plan"] = True
        summary["headline"] = "Review or update your wealth plan"
        store.replace_summary(saved, summary)
    return saved


def test_latest_memory_returns_unavailable_without_checkpoint(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "conversation_store", ConversationStore(tmp_path))

    response = TestClient(server.app).get("/api/memory/latest?user_id=rakshit")

    assert response.status_code == 200
    assert response.json() == {"available": False}


def test_latest_memory_returns_only_display_safe_fields(tmp_path, monkeypatch):
    store = ConversationStore(tmp_path)
    _save_checkpoint(store)
    monkeypatch.setattr(server, "conversation_store", store)

    response = TestClient(server.app).get("/api/memory/latest?user_id=rakshit")

    assert response.status_code == 200
    body = response.json()
    assert body["available"] is True
    assert body["summary_status"] == "fallback"
    assert body["user_name"] == "Rakshit"
    assert set(body) == {
        "available",
        "user_id",
        "user_name",
        "conversation_id",
        "last_conversation_at",
        "headline",
        "summary",
        "completed_plan",
        "summary_status",
    }
    assert "state" not in body
    assert "transcript" not in body
    assert "portfolio" not in body


def test_completed_and_corrupt_checkpoints_degrade_correctly(tmp_path, monkeypatch):
    store = ConversationStore(tmp_path)
    saved = _save_checkpoint(store, completed=True)
    monkeypatch.setattr(server, "conversation_store", store)
    client = TestClient(server.app)

    assert client.get("/api/memory/latest").json()["completed_plan"] is True
    (saved.directory / "state.json").write_text("{bad", encoding="utf-8")
    assert client.get("/api/memory/latest").json() == {"available": False}


def test_invalid_user_id_is_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "conversation_store", ConversationStore(tmp_path))

    response = TestClient(server.app).get("/api/memory/latest?user_id=../secret")

    assert response.status_code == 400


def test_cors_allows_vite_origin(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "conversation_store", ConversationStore(tmp_path))

    response = TestClient(server.app).get(
        "/api/memory/latest",
        headers={"Origin": "http://localhost:5173"},
    )

    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_offer_accepts_simulator_and_defaults_invalid_or_missing_mode_to_fresh(tmp_path, monkeypatch):
    captured = []

    class FakeHandler:
        async def handle_web_request(self, _request, on_connection):
            await on_connection(object())
            await asyncio.sleep(0)
            return {"sdp": "answer", "type": "answer", "pc_id": "pc"}

    class FakeTransport:
        def __init__(self, **_kwargs):
            pass

    async def fake_run_bot(_transport, **kwargs):
        captured.append(kwargs)

    monkeypatch.setattr(server, "_webrtc", FakeHandler())
    monkeypatch.setattr(server, "SmallWebRTCTransport", FakeTransport)
    monkeypatch.setattr(server, "_params", lambda: object())
    monkeypatch.setattr(server, "run_bot", fake_run_bot)
    monkeypatch.setattr(server, "conversation_store", ConversationStore(tmp_path))
    client = TestClient(server.app)
    offer = {"sdp": "v=0", "type": "offer", "pc_id": None, "restart_pc": False}

    assert client.post("/api/offer", json=offer).status_code == 200
    assert client.post("/api/offer?memory_mode=invalid", json=offer).status_code == 200
    assert client.post("/api/offer?memory_mode=resume", json=offer).status_code == 200
    assert client.post("/api/offer?memory_mode=simulator", json=offer).status_code == 200
    assert client.post("/api/offer?memory_mode=emergency", json=offer).status_code == 200

    assert [item["memory_mode"] for item in captured] == [
        "fresh",
        "fresh",
        "resume",
        "simulator",
        "emergency",
    ]


def test_trickle_ice_patch_accepts_mode_query(monkeypatch):
    captured = []

    class FakeHandler:
        async def handle_patch_request(self, request):
            captured.append(request)

    monkeypatch.setattr(server, "_webrtc", FakeHandler())

    response = TestClient(server.app).patch(
        "/api/offer?memory_mode=resume",
        json={"pc_id": "pc", "candidates": []},
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert len(captured) == 1
