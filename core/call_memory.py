"""Call-start restore and call-end checkpoint orchestration."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from loguru import logger

from core import session
from core.conversation_store import ConversationStore, LoadedCheckpoint, SavedCheckpoint
from core.conversation_summary import enhance_checkpoint_summary
from core.run_transcript import RunTranscriptRecorder


DEMO_USER_ID = "rakshit"


def normalize_memory_mode(value: str | None) -> str:
    return value if value in {"resume", "simulator", "emergency"} else "fresh"


@dataclass(frozen=True)
class CallMemoryContext:
    mode: str
    user_id: str
    conversation_id: str
    resumed: bool
    initial_state_payload: dict
    greeting_instruction: str | None = None
    loaded_checkpoint: LoadedCheckpoint | None = None


def prepare_call_memory(
    *,
    memory_mode: str,
    user_id: str,
    conversation_id: str,
    store: ConversationStore,
) -> CallMemoryContext:
    mode = normalize_memory_mode(memory_mode)
    if mode == "simulator":
        session.seed_simulator_profile()
        return CallMemoryContext(
            mode=mode,
            user_id=user_id,
            conversation_id=conversation_id,
            resumed=False,
            initial_state_payload=session.export_state(),
            greeting_instruction=simulator_greeting_instruction(),
        )
    if mode == "emergency":
        session.seed_emergency_plan()
        return CallMemoryContext(
            mode=mode,
            user_id=user_id,
            conversation_id=conversation_id,
            resumed=False,
            initial_state_payload=session.export_state(),
            greeting_instruction=emergency_greeting_instruction(),
        )

    session.reset()
    loaded = store.load_latest(user_id) if mode == "resume" else None
    if loaded:
        try:
            session.restore_state(loaded.state_payload)
        except ValueError:
            loaded = None
    if loaded:
        session.STATE.is_returning_session = True
        session.STATE.resume_confirmed = False
        session.STATE.resume_completed_plan = bool(loaded.summary.get("completed_plan"))
        session.STATE.restored_financial_data = bool(
            session.STATE.portfolio or session.STATE.aa_assets
        )
        greeting = returning_greeting_instruction(loaded)
    else:
        mode = "fresh"
        greeting = None

    return CallMemoryContext(
        mode=mode,
        user_id=user_id,
        conversation_id=conversation_id,
        resumed=loaded is not None,
        initial_state_payload=session.export_state(),
        greeting_instruction=greeting,
        loaded_checkpoint=loaded,
    )


def returning_greeting_instruction(checkpoint: LoadedCheckpoint) -> str:
    summary = checkpoint.summary
    open_items = summary.get("open_items") or []
    open_item = open_items[0] if open_items else "Ask what they want to continue."
    if summary.get("completed_plan"):
        opening = "The saved plan is complete. Ask what has changed or what they want to review."
    else:
        opening = summary.get("recommended_next_start") or open_item
    return (
        "This is a returning session. Welcome Rakshit back in under forty words. "
        f"Saved recap: {summary.get('conversation_summary') or summary.get('card_summary')}. "
        f"Open item: {open_item}. Opening instruction: {opening} "
        "On this first turn, do not call any tool. Ask whether they want to continue or "
        "change anything. After they answer, call confirm_resume."
    )


def simulator_greeting_instruction() -> str:
    return (
        "This is the simulator entry experience. The caller is Rakshit and the demo has "
        "already loaded and confirmed their balanced risk profile, family, mutual funds, "
        "Account Aggregator holdings, income, expenses, and monthly loan repayments. "
        "Welcome Rakshit in under forty words. Say their financial picture is ready, then "
        "ask exactly this choice: would you like to plan for a traditional goal, or use me "
        "as a financial decision simulator? Do not call a tool until they answer. After "
        "they answer, call choose_experience."
    )


def emergency_greeting_instruction() -> str:
    return (
        "This is emergency mode. Rakshit's completed plan is already loaded, including "
        "the emergency fund, Pune home, and daughter's education goals. Your first spoken "
        "turn must be exactly: What's up, Rakshit? What's the emergency? Do not call a tool "
        "until Rakshit answers. Then ask only the missing amount or duration, one question "
        "at a time, before calling analyze_financial_emergency."
    )


class CallMemoryFinalizer:
    def __init__(
        self,
        *,
        store: ConversationStore,
        context: CallMemoryContext,
        recorder: RunTranscriptRecorder,
    ):
        self.store = store
        self.context = context
        self.recorder = recorder
        self._attempted = False
        self.checkpoint: SavedCheckpoint | None = None
        self.summary_task: asyncio.Task | None = None

    def save_once(self) -> SavedCheckpoint | None:
        if self._attempted:
            return self.checkpoint
        self._attempted = True
        if self.context.mode in {"simulator", "emergency"}:
            return None
        try:
            self.checkpoint = self.store.save_checkpoint(
                user_id=self.context.user_id,
                conversation_id=self.context.conversation_id,
                transcript=self.recorder.to_payload(),
                state_payload=session.export_state(),
                initial_state_payload=self.context.initial_state_payload,
                successful_state_change=self.recorder.has_successful_state_change(),
            )
            if self.checkpoint:
                self.summary_task = asyncio.create_task(
                    enhance_checkpoint_summary(self.store, self.checkpoint)
                )
        except Exception as exc:
            logger.warning(f"Could not save conversation memory: {exc}")
        return self.checkpoint
