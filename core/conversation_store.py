"""Small, file-backed store for cross-session conversation checkpoints."""

from __future__ import annotations

import json
import os
import re
import tempfile
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core import session


STORE_SCHEMA_VERSION = 1
_SAFE_USER_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_SAFE_DIRECTORY = re.compile(r"^[A-Za-z0-9_-]+$")


def _now() -> datetime:
    return datetime.now(UTC)


def _iso_now() -> str:
    return _now().isoformat()


def validate_user_id(user_id: str) -> str:
    if not isinstance(user_id, str) or not _SAFE_USER_ID.fullmatch(user_id):
        raise ValueError("invalid user_id")
    return user_id


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)


def fallback_summary(state: dict[str, Any]) -> dict[str, Any]:
    goals = sorted(
        (goal for goal in state.get("goals", []) if isinstance(goal, dict)),
        key=lambda goal: goal.get("priority", 999),
    )
    plan_path = state.get("plan_pdf_path")
    completed_plan = bool(plan_path)

    if completed_plan:
        headline = "Review or update your wealth plan"
        card_summary = "Your completed plan is ready whenever you want to review what has changed."
        open_items = ["Review changes since the completed plan."]
        next_start = "Welcome the user back and ask what has changed or what they want to review."
    elif goals:
        goal_name = _safe_goal_name(str(goals[0].get("name") or "goal"))
        headline = f"Continue your {goal_name} plan"
        card_summary = f"Your {goal_name} goal is saved and ready to continue."
        open_items = [_goal_open_item(goals[0], state)]
        next_start = f"Welcome the user back and ask whether they want to continue the {goal_name} goal."
    else:
        headline = "Continue your guided wealth plan"
        card_summary = "Your planning progress is saved and ready to continue."
        open_items = [_next_open_item(state)]
        next_start = "Welcome the user back and ask whether they want to continue their saved plan."

    return {
        "schema_version": STORE_SCHEMA_VERSION,
        "status": "fallback",
        "generated_at": _iso_now(),
        "headline": headline,
        "card_summary": card_summary,
        "conversation_summary": card_summary,
        "decisions": [],
        "open_items": open_items,
        "recommended_next_start": next_start,
        "completed_plan": completed_plan,
    }


def _safe_goal_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z '\-]", "", value).strip().lower()
    cleaned = re.sub(
        r"\b(?:rupees?|lakhs?|crores?|thousand|million|account)\b",
        "",
        cleaned,
    )
    cleaned = " ".join(cleaned.split())
    return cleaned[:40] or "goal"


def _goal_open_item(goal: dict[str, Any], state: dict[str, Any]) -> str:
    name = _safe_goal_name(str(goal.get("name") or "goal")).capitalize()
    if goal.get("required_sip") is None:
        return f"Complete the funding gap for the {name} goal."
    if goal.get("funded", True) and goal.get("name") not in state.get("proposed_portfolios", {}):
        return f"Complete the portfolio for the {name} goal."
    return f"Review the next step for the {name} goal."


def _next_open_item(state: dict[str, Any]) -> str:
    if not state.get("risk_profile"):
        return "Complete the risk profile."
    if not state.get("family"):
        return "Complete the family snapshot."
    if not state.get("portfolio"):
        return "Choose whether to connect investment data."
    if not state.get("aa_assets"):
        return "Choose whether to connect the broader financial snapshot."
    if not state.get("financial_snapshot_confirmed"):
        return "Confirm the saved financial snapshot."
    return "Choose the first planning goal."


@dataclass(frozen=True)
class SavedCheckpoint:
    user_id: str
    conversation_id: str
    saved_at: str
    directory: Path
    summary: dict[str, Any]


@dataclass(frozen=True)
class LoadedCheckpoint:
    user_id: str
    conversation_id: str
    saved_at: str
    directory: Path
    state_payload: dict[str, Any]
    transcript: dict[str, Any]
    summary: dict[str, Any]


class ConversationStore:
    def __init__(self, root: str | Path | None = None):
        configured = root or os.getenv("CONVERSATION_DIR")
        self.root = Path(configured) if configured else Path(__file__).resolve().parents[1] / "output" / "conversations"

    def new_conversation_id(self) -> str:
        return uuid.uuid4().hex

    def save_checkpoint(
        self,
        *,
        user_id: str,
        conversation_id: str,
        transcript: dict[str, Any],
        state_payload: dict[str, Any],
        initial_state_payload: dict[str, Any],
        successful_state_change: bool = False,
    ) -> SavedCheckpoint | None:
        user_id = validate_user_id(user_id)
        if not _SAFE_DIRECTORY.fullmatch(conversation_id):
            raise ValueError("invalid conversation_id")
        session.validate_state(state_payload)
        if not successful_state_change and state_payload == initial_state_payload:
            return None

        saved_at = _iso_now()
        directory_name = f"{_now().strftime('%Y%m%dT%H%M%S%fZ')}_{conversation_id}"
        directory = self.root / user_id / directory_name
        state_file = {
            "schema_version": STORE_SCHEMA_VERSION,
            "user_id": user_id,
            "conversation_id": conversation_id,
            "saved_at": saved_at,
            "financial_snapshot_observed_at": state_payload["state"].get(
                "financial_snapshot_observed_at"
            ),
            "state": state_payload["state"],
        }
        summary = fallback_summary(state_payload["state"])
        atomic_write_json(directory / "transcript.json", transcript)
        atomic_write_json(directory / "state.json", state_file)
        atomic_write_json(directory / "summary.json", summary)
        atomic_write_json(
            self.root / user_id / "latest.json",
            {
                "schema_version": STORE_SCHEMA_VERSION,
                "conversation_id": conversation_id,
                "checkpoint_directory": directory_name,
                "saved_at": saved_at,
            },
        )
        return SavedCheckpoint(user_id, conversation_id, saved_at, directory, summary)

    def load_latest(self, user_id: str) -> LoadedCheckpoint | None:
        user_id = validate_user_id(user_id)
        user_directory = self.root / user_id
        pointer = self._read_json(user_directory / "latest.json")
        if not pointer or pointer.get("schema_version") != STORE_SCHEMA_VERSION:
            return None
        directory_name = pointer.get("checkpoint_directory")
        if not isinstance(directory_name, str) or not _SAFE_DIRECTORY.fullmatch(directory_name):
            return None
        directory = user_directory / directory_name
        state_file = self._read_json(directory / "state.json")
        transcript = self._read_json(directory / "transcript.json")
        summary = self._read_json(directory / "summary.json")
        if not state_file or not transcript or not summary:
            return None
        if (
            state_file.get("schema_version") != STORE_SCHEMA_VERSION
            or state_file.get("user_id") != user_id
            or state_file.get("conversation_id") != pointer.get("conversation_id")
        ):
            return None
        state_payload = {
            "schema_version": state_file["schema_version"],
            "state": state_file.get("state"),
        }
        try:
            session.validate_state(state_payload)
        except ValueError:
            return None
        if not _valid_summary(summary):
            summary = fallback_summary(state_payload["state"])
        return LoadedCheckpoint(
            user_id=user_id,
            conversation_id=state_file["conversation_id"],
            saved_at=state_file.get("saved_at") or pointer.get("saved_at") or "",
            directory=directory,
            state_payload=state_payload,
            transcript=transcript,
            summary=summary,
        )

    def replace_summary(self, checkpoint: SavedCheckpoint, summary: dict[str, Any]) -> None:
        if not _valid_summary(summary):
            raise ValueError("invalid summary")
        atomic_write_json(checkpoint.directory / "summary.json", summary)

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any] | None:
        try:
            with path.open(encoding="utf-8") as handle:
                value = json.load(handle)
            return value if isinstance(value, dict) else None
        except (OSError, json.JSONDecodeError):
            return None


def _valid_summary(summary: dict[str, Any]) -> bool:
    return (
        summary.get("schema_version") == STORE_SCHEMA_VERSION
        and summary.get("status") in {"pending", "ready", "fallback", "failed"}
        and isinstance(summary.get("headline"), str)
        and isinstance(summary.get("card_summary"), str)
        and isinstance(summary.get("conversation_summary"), str)
        and isinstance(summary.get("decisions"), list)
        and all(isinstance(item, str) for item in summary["decisions"])
        and isinstance(summary.get("open_items"), list)
        and all(isinstance(item, str) for item in summary["open_items"])
        and isinstance(summary.get("recommended_next_start"), str)
        and isinstance(summary.get("completed_plan"), bool)
    )
