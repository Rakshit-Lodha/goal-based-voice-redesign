import asyncio

import pytest

from pipecat.audio.filters.rnnoise_filter import RNNoiseFilter
from pipecat.frames.frames import (
    BotStartedSpeakingFrame,
    BotStoppedSpeakingFrame,
    InterimTranscriptionFrame,
    TranscriptionFrame,
    VADUserStartedSpeakingFrame,
)
from pipecat.turns.types import ProcessFrameResult

from core.audio_input import (
    IntentionalUserTurnStartStrategy,
    make_transport_params,
    make_user_aggregator_params,
    transcript_rejection_reason,
)


def test_transport_enables_rnnoise_without_using_removed_transport_vad_field():
    params = make_transport_params()

    assert isinstance(params.audio_in_filter, RNNoiseFilter)
    assert not hasattr(params, "vad_analyzer")


def test_user_aggregator_owns_tuned_silero_vad():
    params = make_user_aggregator_params()

    assert params.vad_analyzer is not None
    assert params.vad_analyzer.params.confidence == pytest.approx(0.68)
    assert params.vad_analyzer.params.start_secs == pytest.approx(0.15)
    assert params.vad_analyzer.params.stop_secs == pytest.approx(0.30)
    assert params.vad_analyzer.params.min_volume == pytest.approx(0.35)
    assert len(params.user_turn_strategies.start) == 1
    start_strategy = params.user_turn_strategies.start[0]
    assert isinstance(start_strategy, IntentionalUserTurnStartStrategy)


def test_vad_starts_turn_only_while_bot_is_quiet():
    strategy = IntentionalUserTurnStartStrategy()

    async def exercise():
        await strategy.process_frame(BotStartedSpeakingFrame())
        speaking_result = await strategy.process_frame(VADUserStartedSpeakingFrame())
        await strategy.process_frame(BotStoppedSpeakingFrame())
        quiet_result = await strategy.process_frame(VADUserStartedSpeakingFrame())
        return speaking_result, quiet_result

    speaking_result, quiet_result = asyncio.run(exercise())
    assert speaking_result == ProcessFrameResult.CONTINUE
    assert quiet_result == ProcessFrameResult.STOP


@pytest.mark.parametrize("text", ["yes", "no", "okay", "42", "wait"])
def test_intentional_one_word_reply_can_interrupt(text):
    strategy = IntentionalUserTurnStartStrategy()

    async def exercise():
        await strategy.process_frame(BotStartedSpeakingFrame())
        return await strategy.process_frame(TranscriptionFrame(text, "", 0))

    assert asyncio.run(exercise()) == ProcessFrameResult.STOP


def test_interim_transcript_cannot_interrupt():
    strategy = IntentionalUserTurnStartStrategy()

    async def exercise():
        await strategy.process_frame(BotStartedSpeakingFrame())
        return await strategy.process_frame(InterimTranscriptionFrame("background noise", "", 0))

    assert asyncio.run(exercise()) == ProcessFrameResult.CONTINUE


@pytest.mark.parametrize(
    "text",
    [
        "yes",
        "no",
        "okay",
        "42",
        "1.5 crore",
        "I want to plan for retirement",
    ],
)
def test_transcript_gate_keeps_short_and_financial_answers(text):
    assert transcript_rejection_reason(text) is None


@pytest.mark.parametrize(
    "text",
    [
        "",
        "   ",
        "...",
        "[background noise]",
        "(inaudible)",
        "music",
        "uh um hmm",
    ],
)
def test_transcript_gate_rejects_only_clear_noise_artifacts(text):
    assert transcript_rejection_reason(text) is not None
