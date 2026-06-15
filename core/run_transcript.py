"""End-of-run transcript capture with tool calls."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from loguru import logger

from pipecat.frames.frames import (
    Frame,
    LLMFullResponseEndFrame,
    LLMFullResponseStartFrame,
    LLMTextFrame,
    TranscriptionFrame,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor


_current_recorder: "RunTranscriptRecorder | None" = None


def bind(recorder: "RunTranscriptRecorder"):
    global _current_recorder
    _current_recorder = recorder


def unbind():
    global _current_recorder
    _current_recorder = None


def record_tool_call(name: str, arguments: dict[str, Any]):
    if _current_recorder:
        _current_recorder.add_tool_call(name, arguments)


def record_tool_result(name: str, result: Any):
    if _current_recorder:
        _current_recorder.add_tool_result(name, result)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _json_safe(value: Any) -> Any:
    try:
        json.dumps(value)
        return value
    except TypeError:
        return json.loads(json.dumps(value, default=str))


@dataclass
class TranscriptEvent:
    type: str
    timestamp: str = field(default_factory=_now_iso)
    role: str | None = None
    text: str | None = None
    name: str | None = None
    arguments: Any | None = None
    result: Any | None = None


class RunTranscriptRecorder:
    def __init__(self, *, output_dir: str = "output/transcripts"):
        self.output_dir = output_dir
        self.events: list[TranscriptEvent] = []
        self._assistant_chunks: list[str] = []
        self._assistant_active = False
        self._saved_path: str | None = None

    def add_user_transcript(self, text: str):
        if text.strip():
            self.events.append(TranscriptEvent(type="message", role="user", text=text))

    def start_assistant_response(self):
        self._flush_assistant_response()
        self._assistant_active = True

    def add_assistant_text(self, text: str):
        if text:
            self._assistant_chunks.append(text)

    def end_assistant_response(self):
        self._flush_assistant_response()
        self._assistant_active = False

    def add_tool_call(self, name: str, arguments: dict[str, Any]):
        self._flush_assistant_response()
        self.events.append(
            TranscriptEvent(
                type="tool_call",
                name=name,
                arguments=_json_safe(arguments),
            )
        )

    def add_tool_result(self, name: str, result: Any):
        self.events.append(
            TranscriptEvent(
                type="tool_result",
                name=name,
                result=_json_safe(result),
            )
        )

    def save_once(self) -> str:
        if self._saved_path:
            return self._saved_path

        self._flush_assistant_response()
        os.makedirs(self.output_dir, exist_ok=True)
        filename = f"run_transcript_{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}.json"
        path = os.path.abspath(os.path.join(self.output_dir, filename))
        payload = {
            "created_at": _now_iso(),
            "events": [
                {key: value for key, value in event.__dict__.items() if value is not None}
                for event in self.events
            ],
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        self._saved_path = path
        logger.info(f"Run transcript saved: {path}")
        return path

    def _flush_assistant_response(self):
        text = "".join(self._assistant_chunks).strip()
        if text:
            self.events.append(TranscriptEvent(type="message", role="assistant", text=text))
        self._assistant_chunks = []


class RunTranscriptTap(FrameProcessor):
    """Pipeline tap that records user and assistant transcript frames."""

    def __init__(self, recorder: RunTranscriptRecorder, *, name: str = "run_transcript_tap"):
        super().__init__(name=name)
        self._recorder = recorder

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        if direction == FrameDirection.DOWNSTREAM:
            if isinstance(frame, TranscriptionFrame):
                self._recorder.add_user_transcript(frame.text)
            elif isinstance(frame, LLMFullResponseStartFrame):
                self._recorder.start_assistant_response()
            elif isinstance(frame, LLMTextFrame):
                self._recorder.add_assistant_text(frame.text)
            elif isinstance(frame, LLMFullResponseEndFrame):
                self._recorder.end_assistant_response()

        await self.push_frame(frame, direction)
