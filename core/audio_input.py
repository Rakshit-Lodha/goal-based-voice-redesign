"""Noise suppression, VAD, and conservative transcript filtering."""

import re

from loguru import logger

from pipecat.audio.filters.rnnoise_filter import RNNoiseFilter
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.frames.frames import (
    BotStartedSpeakingFrame,
    BotStoppedSpeakingFrame,
    Frame,
    InterimTranscriptionFrame,
    TranscriptionFrame,
    VADUserStartedSpeakingFrame,
)
from pipecat.processors.aggregators.llm_response_universal import LLMUserAggregatorParams
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.transports.base_transport import TransportParams
from pipecat.turns.types import ProcessFrameResult
from pipecat.turns.user_start import BaseUserTurnStartStrategy
from pipecat.turns.user_turn_strategies import UserTurnStrategies


_FILLER_WORDS = {"ah", "eh", "erm", "hm", "hmm", "uh", "uhh", "um", "umm"}
_ONE_WORD_INTERRUPTS = {
    "continue",
    "correct",
    "go",
    "no",
    "okay",
    "ok",
    "pause",
    "repeat",
    "resume",
    "stop",
    "sure",
    "wait",
    "yes",
    "yeah",
    "yep",
}
_NON_SPEECH_RE = re.compile(
    r"^[\[(<]?\s*(?:background\s+)?(?:inaudible|music|noise|silence)\s*[\])>]?$",
    re.IGNORECASE,
)


def make_transport_params() -> TransportParams:
    """Build transport audio settings shared by every server entrypoint."""
    return TransportParams(
        audio_in_enabled=True,
        audio_out_enabled=True,
        audio_in_filter=RNNoiseFilter(),
    )


def make_user_aggregator_params() -> LLMUserAggregatorParams:
    """Attach Silero VAD where Pipecat 1.3 consumes it."""
    return LLMUserAggregatorParams(
        vad_analyzer=SileroVADAnalyzer(
            params=VADParams(
                confidence=0.68,
                start_secs=0.15,
                stop_secs=0.30,
                min_volume=0.35,
            )
        ),
        user_turn_strategies=UserTurnStrategies(
            start=[IntentionalUserTurnStartStrategy()],
        ),
    )


def transcript_rejection_reason(text: str) -> str | None:
    """Return a reason only for transcripts that are unambiguously non-speech."""
    normalized = " ".join(text.split()).strip()
    if not normalized:
        return "empty"
    if not any(character.isalnum() for character in normalized):
        return "punctuation-only"
    if _NON_SPEECH_RE.fullmatch(normalized):
        return "non-speech label"

    words = re.findall(r"[a-z]+", normalized.lower())
    if words and all(word in _FILLER_WORDS for word in words):
        return "filler-only"
    return None


class IntentionalUserTurnStartStrategy(BaseUserTurnStartStrategy):
    """Use VAD normally, but require recognized speech to interrupt Maya."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._bot_speaking = False

    async def reset(self):
        self._bot_speaking = False

    async def process_frame(self, frame: Frame) -> ProcessFrameResult:
        if isinstance(frame, BotStartedSpeakingFrame):
            self._bot_speaking = True
        elif isinstance(frame, BotStoppedSpeakingFrame):
            self._bot_speaking = False
        elif isinstance(frame, VADUserStartedSpeakingFrame):
            if not self._bot_speaking:
                await self.trigger_user_turn_started()
                return ProcessFrameResult.STOP
        elif isinstance(frame, TranscriptionFrame):
            words = frame.text.split()
            one_word = words[0].lower().strip(".,!?") if len(words) == 1 else ""
            intentional = (
                len(words) >= 2
                or one_word in _ONE_WORD_INTERRUPTS
                or (one_word and any(character.isdigit() for character in one_word))
            )
            if not self._bot_speaking or intentional:
                await self.trigger_user_turn_started()
                return ProcessFrameResult.STOP

        return ProcessFrameResult.CONTINUE


class TranscriptGate(FrameProcessor):
    """Keep obvious STT noise artifacts out of the transcript and LLM context."""

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        if direction == FrameDirection.DOWNSTREAM and isinstance(
            frame, (InterimTranscriptionFrame, TranscriptionFrame)
        ):
            reason = transcript_rejection_reason(frame.text)
            if reason:
                logger.info(f"Dropped {reason} transcript before LLM: {frame.text!r}")
                return

        await self.push_frame(frame, direction)
