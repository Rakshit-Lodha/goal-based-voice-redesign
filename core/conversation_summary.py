"""Bounded post-call summary enhancement for saved conversation checkpoints."""

from __future__ import annotations

import asyncio
import copy
import json
import os
import re
from datetime import UTC, datetime
from typing import Any, Awaitable, Callable

from loguru import logger

from core.conversation_store import (
    STORE_SCHEMA_VERSION,
    ConversationStore,
    SavedCheckpoint,
)


SummaryCall = Callable[[dict[str, Any]], Awaitable[dict[str, Any] | str]]
_CARD_SENSITIVE = re.compile(
    r"(?:\d|₹|\$|\b(?:rupees?|lakhs?|crores?|thousand|million|account\s*(?:id|number))\b)",
    re.IGNORECASE,
)
_STALE_CONSENT = re.compile(
    r"\bconsent\b.{0,40}\b(?:still valid|reus(?:e|able)|active|authori[sz]ed)\b",
    re.IGNORECASE,
)


async def enhance_checkpoint_summary(
    store: ConversationStore,
    checkpoint: SavedCheckpoint,
    *,
    llm_call: SummaryCall | None = None,
    timeout_seconds: float = 8.0,
) -> bool:
    """Replace a fallback summary after a valid bounded LLM response."""
    transcript = store._read_json(checkpoint.directory / "transcript.json")
    state_file = store._read_json(checkpoint.directory / "state.json")
    if not transcript or not state_file or not _has_user_message(transcript):
        return False

    request = _summary_request(transcript, state_file.get("state") or {})
    try:
        call = llm_call or _openai_summary_call
        raw = await asyncio.wait_for(call(copy.deepcopy(request)), timeout=timeout_seconds)
        candidate = _normalize_summary(raw)
        store.replace_summary(checkpoint, candidate)
        return True
    except Exception as exc:
        logger.warning(f"Memory summary enhancement skipped; fallback retained: {exc}")
        return False


def _has_user_message(transcript: dict[str, Any]) -> bool:
    return any(
        event.get("type") == "message"
        and event.get("role") == "user"
        and isinstance(event.get("text"), str)
        and event["text"].strip()
        for event in transcript.get("events", [])
        if isinstance(event, dict)
    )


def _summary_request(transcript: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    return {
        "instructions": (
            "Summarize this wealth-planning call for a returning user. Saved state and tool "
            "results are authoritative. Do not invent or change amounts, goals, people, dates, "
            "confirmations, or consent. Treat corrections as replacing old facts. Never imply "
            "old provider consent remains valid. headline and card_summary must contain no "
            "financial amounts, account identifiers, or sensitive holdings. Return one JSON "
            "object with exactly: headline, card_summary, conversation_summary, decisions "
            "(string array), open_items (string array), recommended_next_start, completed_plan "
            "(boolean). recommended_next_start is an instruction, not spoken dialogue."
        ),
        "transcript": transcript.get("events", []),
        "authoritative_state": state,
    }


async def _openai_summary_call(request: dict[str, Any]) -> str:
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not configured")
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])
    response = await client.chat.completions.create(
        model=os.getenv("MEMORY_SUMMARY_MODEL", "gpt-4o-mini"),
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": request["instructions"]},
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "transcript": request["transcript"],
                        "authoritative_state": request["authoritative_state"],
                    },
                    ensure_ascii=False,
                ),
            },
        ],
    )
    return response.choices[0].message.content or ""


def _normalize_summary(raw: dict[str, Any] | str) -> dict[str, Any]:
    value = json.loads(raw) if isinstance(raw, str) else raw
    if not isinstance(value, dict):
        raise ValueError("summary must be an object")
    required_strings = (
        "headline",
        "card_summary",
        "conversation_summary",
        "recommended_next_start",
    )
    for key in required_strings:
        if not isinstance(value.get(key), str) or not value[key].strip():
            raise ValueError(f"summary is missing {key}")
    for key in ("decisions", "open_items"):
        if not isinstance(value.get(key), list) or not all(
            isinstance(item, str) for item in value[key]
        ):
            raise ValueError(f"summary has invalid {key}")
    if not isinstance(value.get("completed_plan"), bool):
        raise ValueError("summary has invalid completed_plan")
    if _CARD_SENSITIVE.search(value["headline"]) or _CARD_SENSITIVE.search(value["card_summary"]):
        raise ValueError("entry-card summary contains sensitive financial detail")
    if _STALE_CONSENT.search(" ".join(str(item) for item in value.values())):
        raise ValueError("summary attempts to reuse prior consent")

    return {
        "schema_version": STORE_SCHEMA_VERSION,
        "status": "ready",
        "generated_at": datetime.now(UTC).isoformat(),
        **{key: value[key] for key in required_strings},
        "decisions": value["decisions"],
        "open_items": value["open_items"],
        "completed_plan": value["completed_plan"],
    }
