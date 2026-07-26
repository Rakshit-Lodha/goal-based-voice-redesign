"""Own FastAPI app hosting the Northstar Wealth voice bot + serving plan PDFs.

One port for everything: WebRTC signaling (POST /api/offer), the generated
plan PDFs (GET /output/...), and a health check. The React client (Vite, port
5173 in dev) connects here over WebRTC; live plan state streams back to it via
RTVI server messages emitted from the tools.

Run:  python server.py     (or: uvicorn server:app --port 8000)
"""

import asyncio
import json
import os

from dotenv import load_dotenv
from loguru import logger

load_dotenv(override=True)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from pipecat.transports.base_transport import TransportParams
from pipecat.transports.smallwebrtc.connection import SmallWebRTCConnection
from aiortc import RTCIceServer
from pipecat.transports.smallwebrtc.request_handler import (
    IceCandidate,
    SmallWebRTCRequest,
    SmallWebRTCRequestHandler,
    SmallWebRTCPatchRequest,
)
from pipecat.transports.smallwebrtc.transport import SmallWebRTCTransport

from bot import run_bot
from core.audio_input import make_transport_params
from core.call_memory import DEMO_USER_ID, normalize_memory_mode
from core.conversation_store import ConversationStore, validate_user_id
from core import consent

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
WEB_DIST_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web", "dist")
os.makedirs(OUTPUT_DIR, exist_ok=True)

app = FastAPI(title="Northstar Wealth")

# Dev: Vite serves the UI from a different origin, so allow it to call /api/offer.
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174,http://localhost:4173,http://127.0.0.1:4173",
    ).split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve generated plan PDFs at /output/<file>.
app.mount("/output", StaticFiles(directory=OUTPUT_DIR), name="output")

def _ice_servers() -> list[RTCIceServer]:
    configured = os.getenv("ICE_SERVERS")
    if configured:
        return [RTCIceServer(**item) for item in json.loads(configured)]
    return [RTCIceServer(urls="stun:stun.l.google.com:19302")]


_webrtc = SmallWebRTCRequestHandler(ice_servers=_ice_servers())
conversation_store = ConversationStore()


def _params() -> TransportParams:
    return make_transport_params()


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/api/memory/latest")
async def latest_memory(user_id: str = DEMO_USER_ID):
    try:
        validate_user_id(user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    checkpoint = conversation_store.load_latest(user_id)
    if not checkpoint:
        return {"available": False}
    summary = checkpoint.summary
    return {
        "available": True,
        "user_id": user_id,
        "user_name": checkpoint.state_payload["state"].get("name") or "Rakshit",
        "conversation_id": checkpoint.conversation_id,
        "last_conversation_at": checkpoint.saved_at,
        "headline": summary["headline"],
        "summary": summary["card_summary"],
        "completed_plan": summary["completed_plan"],
        "summary_status": summary["status"],
    }


@app.post("/api/offer")
async def offer(
    request: dict,
    memory_mode: str | None = None,
    user_id: str = DEMO_USER_ID,
):
    """WebRTC signaling: take the browser's SDP offer, spin up the bot, return the answer."""
    try:
        validate_user_id(user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    resolved_mode = normalize_memory_mode(memory_mode)
    conversation_id = conversation_store.new_conversation_id()

    async def on_connection(connection: SmallWebRTCConnection):
        transport = SmallWebRTCTransport(webrtc_connection=connection, params=_params())
        # run_bot blocks until the call ends; run it alongside this request.
        asyncio.create_task(run_bot(
            transport,
            memory_mode=resolved_mode,
            user_id=user_id,
            conversation_id=conversation_id,
            conversation_store=conversation_store,
        ))

    answer = await _webrtc.handle_web_request(
        SmallWebRTCRequest.from_dict(request), on_connection
    )
    return answer


@app.patch("/api/offer")
async def offer_patch(request: dict):
    """WebRTC trickle ICE: add browser ICE candidates to the existing peer connection."""
    candidates = [
        IceCandidate(
            candidate=item["candidate"],
            sdp_mid=item.get("sdp_mid", item.get("sdpMid")),
            sdp_mline_index=item.get("sdp_mline_index", item.get("sdpMLineIndex")),
        )
        for item in request.get("candidates", [])
    ]
    await _webrtc.handle_patch_request(
        SmallWebRTCPatchRequest(pc_id=request["pc_id"], candidates=candidates)
    )
    return {"ok": True}


@app.post("/api/otp")
async def otp(request: dict):
    """Simple browser-entered OTP bridge for mocked MF Central / Finvu consent."""
    accepted = await consent.submit_otp(str(request.get("request_id", "")), str(request.get("otp", "")))
    return {"accepted": accepted}


if os.path.isdir(WEB_DIST_DIR):
    @app.get("/memory", include_in_schema=False)
    @app.get("/memory/", include_in_schema=False)
    @app.get("/simulator", include_in_schema=False)
    @app.get("/simulator/", include_in_schema=False)
    async def memory_app():
        return FileResponse(os.path.join(WEB_DIST_DIR, "index.html"))

    app.mount("/", StaticFiles(directory=WEB_DIST_DIR, html=True), name="web")


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    logger.info(f"Northstar Wealth API on http://localhost:{port} (UI dev server: http://localhost:5173)")
    uvicorn.run(app, host="0.0.0.0", port=port)
