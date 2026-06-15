import json

from pipecat.frames.frames import InputAudioRawFrame, MetricsFrame
from pipecat.metrics.metrics import (
    LLMTokenUsage,
    LLMUsageMetricsData,
    ProcessingMetricsData,
    TTFBMetricsData,
    TTSUsageMetricsData,
    TurnMetricsData,
)

from core.run_cost import CostRates, RunCostTracker


def test_run_cost_totals_llm_tts_and_stt_usage():
    tracker = RunCostTracker(
        CostRates(
            llm_input_per_1m_tokens=2.5,
            llm_output_per_1m_tokens=10,
            llm_cached_input_per_1m_tokens=1.25,
            tts_per_1m_chars=100,
            stt_per_audio_minute=0.02,
        )
    )

    tracker.add_input_audio(
        InputAudioRawFrame(
            audio=b"\0" * 16_000 * 2 * 30,
            sample_rate=16_000,
            num_channels=1,
        )
    )
    tracker.add_metrics(
        MetricsFrame(
            data=[
                LLMUsageMetricsData(
                    processor="llm",
                    model="gpt-4o",
                    value=LLMTokenUsage(
                        prompt_tokens=1_000,
                        completion_tokens=200,
                        total_tokens=1_200,
                        cache_read_input_tokens=100,
                    ),
                ),
                TTSUsageMetricsData(processor="tts", model="bulbul:v3", value=1_000),
            ]
        )
    )

    snapshot = tracker.snapshot()

    assert snapshot.input_audio_seconds == 30
    assert snapshot.llm_prompt_tokens == 1_000
    assert snapshot.llm_cached_input_tokens == 100
    assert snapshot.llm_completion_tokens == 200
    assert snapshot.tts_chars == 1_000
    assert snapshot.stt_cost == 0.01
    assert snapshot.llm_cost == 0.004375
    assert snapshot.tts_cost == 0.1
    assert snapshot.total_cost == 0.114375


def test_run_cost_uses_input_rate_for_cache_creation_by_default():
    tracker = RunCostTracker(CostRates(llm_input_per_1m_tokens=2))
    tracker.add_metrics(
        MetricsFrame(
            data=[
                LLMUsageMetricsData(
                    processor="llm",
                    model="gpt-4o",
                    value=LLMTokenUsage(
                        prompt_tokens=1_000,
                        completion_tokens=0,
                        total_tokens=1_000,
                        cache_creation_input_tokens=400,
                    ),
                )
            ]
        )
    )

    assert tracker.snapshot().llm_cost == 0.002


def test_run_cost_summarizes_latency_metrics():
    tracker = RunCostTracker()

    tracker.add_metrics(
        MetricsFrame(
            data=[
                TTFBMetricsData(processor="llm", model="gpt-4o", value=0.10),
                TTFBMetricsData(processor="llm", model="gpt-4o", value=0.20),
                TTFBMetricsData(processor="llm", model="gpt-4o", value=0.30),
                ProcessingMetricsData(processor="tts", model="bulbul:v3", value=0.05),
                TurnMetricsData(
                    processor="turn",
                    model=None,
                    is_complete=True,
                    probability=0.90,
                    e2e_processing_time_ms=125,
                ),
            ]
        )
    )

    latencies = tracker.snapshot().latencies

    ttfb = latencies["ttfb:llm:gpt-4o"]
    assert ttfb.count == 3
    assert ttfb.avg_ms == 200
    assert ttfb.p95_ms == 300
    assert ttfb.max_ms == 300
    assert latencies["processing:tts:bulbul:v3"].avg_ms == 50
    assert latencies["turn_e2e_processing:turn"].avg_ms == 125


def test_run_cost_saves_recomputable_metrics_file(tmp_path):
    tracker = RunCostTracker(
        CostRates(
            llm_input_per_1m_tokens=2.5,
            llm_output_per_1m_tokens=10,
            tts_per_1m_chars=100,
            stt_per_audio_minute=0.02,
        ),
        output_dir=str(tmp_path),
    )
    tracker.add_input_audio(
        InputAudioRawFrame(
            audio=b"\0" * 16_000 * 2 * 60,
            sample_rate=16_000,
            num_channels=1,
        )
    )
    tracker.add_metrics(
        MetricsFrame(
            data=[
                LLMUsageMetricsData(
                    processor="llm",
                    model="gpt-4o",
                    value=LLMTokenUsage(
                        prompt_tokens=1_000,
                        completion_tokens=200,
                        total_tokens=1_200,
                    ),
                ),
                TTSUsageMetricsData(processor="tts", model="bulbul:v3", value=1_000),
                TTFBMetricsData(processor="llm", model="gpt-4o", value=0.25),
            ]
        )
    )

    path = tracker.save_once(metadata={"llm_model": "gpt-4o", "transcript_path": "x.json"})
    with open(path, encoding="utf-8") as f:
        payload = json.load(f)

    assert payload["metadata"]["llm_model"] == "gpt-4o"
    assert payload["metadata"]["transcript_path"] == "x.json"
    assert payload["usage"]["input_audio_minutes"] == 1
    assert payload["usage"]["llm_prompt_tokens"] == 1_000
    assert payload["usage"]["llm_completion_tokens"] == 200
    assert payload["usage"]["tts_chars"] == 1_000
    assert payload["costs"]["total_cost"] == 0.1245
    assert payload["raw_metrics"]["llm_usage_events"][0]["total_tokens"] == 1_200
    assert payload["raw_metrics"]["tts_usage_events"][0]["chars"] == 1_000
    assert payload["raw_metrics"]["latency_events"][0]["value_ms"] == 250
    assert tracker.save_once(metadata={"llm_model": "ignored"}) == path
