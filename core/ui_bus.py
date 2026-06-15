"""Bridge from tool handlers to the browser UI over the WebRTC data channel.

The Pipecat RTVIProcessor is bound here once per call; tools push state
snapshots through emit(), which the React client receives as server messages.
No-ops cleanly when no UI is attached (e.g. the voice-only dev runner or tests).
"""

from typing import Literal

from loguru import logger

_rtvi = None

ArtifactKind = Literal[
    "risk_reveal",
    "family_recap",
    "mfc_consent",
    "mfc_review",
    "aa_consent",
    "income_snapshot",
    "investments_review",
    "inflation_curve",
    "sip_split",
    "funds_picker",
    "plan_hero",
]


def bind(rtvi) -> None:
    global _rtvi
    _rtvi = rtvi


def unbind() -> None:
    global _rtvi
    _rtvi = None


async def emit(data: dict) -> None:
    if _rtvi is None:
        logger.warning(f"ui_bus emit skipped; no RTVI client bound: {data.get('type')}")
        return
    try:
        await _rtvi.send_server_message(data)
    except Exception as e:
        logger.warning(f"ui_bus emit failed: {e}")


async def emit_artifact(kind: ArtifactKind, data: dict) -> None:
    await emit({"type": "artifact", "kind": kind, "data": data})
