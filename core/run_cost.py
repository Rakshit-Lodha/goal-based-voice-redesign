"""Per-run usage and cost accounting for the voice pipeline."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any

from loguru import logger

from pipecat.frames.frames import Frame, InputAudioRawFrame, MetricsFrame
from pipecat.metrics.metrics import (
    LLMUsageMetricsData,
    ProcessingMetricsData,
    TextAggregationMetricsData,
    TTFBMetricsData,
    TTSUsageMetricsData,
    TurnMetricsData,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor


def _env_float(name: str, default: float = 0.0) -> float:
    raw = os.getenv(name)
    if raw in (None, ""):
        return default
    try:
        return float(raw)
    except ValueError:
        logger.warning(f"Ignoring invalid {name}={raw!r}; expected a number.")
        return default


@dataclass(frozen=True)
class CostRates:
    """Pricing inputs. Defaults are zero so stale vendor prices are never baked in."""

    llm_input_per_1m_tokens: float = 0.0
    llm_output_per_1m_tokens: float = 0.0
    llm_cached_input_per_1m_tokens: float = 0.0
    llm_cache_creation_input_per_1m_tokens: float | None = None
    tts_per_1m_chars: float = 0.0
    stt_per_audio_minute: float = 0.0
    currency: str = "USD"

    @classmethod
    def from_env(cls) -> "CostRates":
        input_rate = _env_float("COST_LLM_INPUT_PER_1M_TOKENS")
        return cls(
            llm_input_per_1m_tokens=input_rate,
            llm_output_per_1m_tokens=_env_float("COST_LLM_OUTPUT_PER_1M_TOKENS"),
            llm_cached_input_per_1m_tokens=_env_float("COST_LLM_CACHED_INPUT_PER_1M_TOKENS"),
            llm_cache_creation_input_per_1m_tokens=_env_float(
                "COST_LLM_CACHE_CREATION_INPUT_PER_1M_TOKENS",
                input_rate,
            ),
            tts_per_1m_chars=_env_float("COST_TTS_PER_1M_CHARS"),
            stt_per_audio_minute=_env_float("COST_STT_PER_AUDIO_MINUTE"),
            currency=os.getenv("COST_CURRENCY", "USD"),
        )


@dataclass
class LatencySummary:
    count: int
    avg_ms: float
    p95_ms: float
    max_ms: float


@dataclass
class RunCostSnapshot:
    input_audio_seconds: float
    llm_prompt_tokens: int
    llm_cached_input_tokens: int
    llm_cache_creation_input_tokens: int
    llm_completion_tokens: int
    tts_chars: int
    stt_cost: float
    llm_cost: float
    tts_cost: float
    total_cost: float
    currency: str
    latencies: dict[str, LatencySummary] = field(default_factory=dict)


class RunCostTracker:
    def __init__(self, rates: CostRates | None = None, *, output_dir: str = "output/metrics"):
        self.rates = rates or CostRates.from_env()
        self.output_dir = output_dir
        self.input_audio_seconds = 0.0
        self.llm_prompt_tokens = 0
        self.llm_cached_input_tokens = 0
        self.llm_cache_creation_input_tokens = 0
        self.llm_completion_tokens = 0
        self.tts_chars = 0
        self.latencies: dict[str, list[float]] = {}
        self.llm_usage_events: list[dict[str, Any]] = []
        self.tts_usage_events: list[dict[str, Any]] = []
        self.latency_events: list[dict[str, Any]] = []
        self._logged = False
        self._saved_path: str | None = None

    def add_input_audio(self, frame: InputAudioRawFrame):
        if frame.sample_rate:
            self.input_audio_seconds += frame.num_frames / frame.sample_rate

    def add_metrics(self, frame: MetricsFrame):
        for item in frame.data:
            if isinstance(item, LLMUsageMetricsData):
                usage = item.value
                self.llm_prompt_tokens += usage.prompt_tokens
                self.llm_completion_tokens += usage.completion_tokens
                self.llm_cached_input_tokens += usage.cache_read_input_tokens or 0
                self.llm_cache_creation_input_tokens += usage.cache_creation_input_tokens or 0
                self.llm_usage_events.append({
                    "processor": item.processor,
                    "model": item.model,
                    "prompt_tokens": usage.prompt_tokens,
                    "completion_tokens": usage.completion_tokens,
                    "total_tokens": usage.total_tokens,
                    "cache_read_input_tokens": usage.cache_read_input_tokens or 0,
                    "cache_creation_input_tokens": usage.cache_creation_input_tokens or 0,
                    "reasoning_tokens": usage.reasoning_tokens or 0,
                })
            elif isinstance(item, TTSUsageMetricsData):
                self.tts_chars += item.value
                self.tts_usage_events.append({
                    "processor": item.processor,
                    "model": item.model,
                    "chars": item.value,
                })
            elif isinstance(item, TTFBMetricsData):
                self._add_latency("ttfb", item.processor, item.model, item.value * 1000)
            elif isinstance(item, ProcessingMetricsData):
                self._add_latency("processing", item.processor, item.model, item.value * 1000)
            elif isinstance(item, TextAggregationMetricsData):
                self._add_latency("text_aggregation", item.processor, item.model, item.value * 1000)
            elif isinstance(item, TurnMetricsData):
                self._add_latency(
                    "turn_e2e_processing",
                    item.processor,
                    item.model,
                    item.e2e_processing_time_ms,
                )

    def _add_latency(self, metric: str, processor: str, model: str | None, value_ms: float):
        key = f"{metric}:{processor}"
        if model:
            key += f":{model}"
        self.latencies.setdefault(key, []).append(value_ms)
        self.latency_events.append({
            "metric": metric,
            "processor": processor,
            "model": model,
            "value_ms": value_ms,
        })

    def _latency_summaries(self) -> dict[str, LatencySummary]:
        summaries = {}
        for key, values in self.latencies.items():
            ordered = sorted(values)
            p95_index = min(round((len(ordered) - 1) * 0.95), len(ordered) - 1)
            summaries[key] = LatencySummary(
                count=len(values),
                avg_ms=sum(values) / len(values),
                p95_ms=ordered[p95_index],
                max_ms=max(values),
            )
        return summaries

    def snapshot(self) -> RunCostSnapshot:
        rates = self.rates
        regular_input_tokens = max(
            self.llm_prompt_tokens
            - self.llm_cached_input_tokens
            - self.llm_cache_creation_input_tokens,
            0,
        )
        cache_creation_rate = (
            rates.llm_cache_creation_input_per_1m_tokens
            if rates.llm_cache_creation_input_per_1m_tokens is not None
            else rates.llm_input_per_1m_tokens
        )

        llm_cost = (
            regular_input_tokens * rates.llm_input_per_1m_tokens
            + self.llm_cached_input_tokens * rates.llm_cached_input_per_1m_tokens
            + self.llm_cache_creation_input_tokens * cache_creation_rate
            + self.llm_completion_tokens * rates.llm_output_per_1m_tokens
        ) / 1_000_000
        tts_cost = self.tts_chars * rates.tts_per_1m_chars / 1_000_000
        stt_cost = (self.input_audio_seconds / 60) * rates.stt_per_audio_minute
        total_cost = stt_cost + llm_cost + tts_cost

        return RunCostSnapshot(
            input_audio_seconds=self.input_audio_seconds,
            llm_prompt_tokens=self.llm_prompt_tokens,
            llm_cached_input_tokens=self.llm_cached_input_tokens,
            llm_cache_creation_input_tokens=self.llm_cache_creation_input_tokens,
            llm_completion_tokens=self.llm_completion_tokens,
            tts_chars=self.tts_chars,
            stt_cost=stt_cost,
            llm_cost=llm_cost,
            tts_cost=tts_cost,
            total_cost=total_cost,
            currency=rates.currency,
            latencies=self._latency_summaries(),
        )

    def log_summary_once(self):
        if self._logged:
            return
        self._logged = True
        s = self.snapshot()
        logger.info(
            "Run cost summary: "
            f"total={s.total_cost:.6f} {s.currency} "
            f"(llm={s.llm_cost:.6f}, tts={s.tts_cost:.6f}, stt={s.stt_cost:.6f}); "
            f"usage=input_audio={s.input_audio_seconds:.1f}s, "
            f"llm_prompt={s.llm_prompt_tokens}, llm_completion={s.llm_completion_tokens}, "
            f"llm_cached_input={s.llm_cached_input_tokens}, "
            f"tts_chars={s.tts_chars}"
        )
        if s.latencies:
            latency_parts = [
                f"{name}=count:{summary.count},avg:{summary.avg_ms:.1f}ms,"
                f"p95:{summary.p95_ms:.1f}ms,max:{summary.max_ms:.1f}ms"
                for name, summary in sorted(s.latencies.items())
            ]
            logger.info("Run latency summary: " + "; ".join(latency_parts))

    def save_once(self, *, metadata: dict[str, Any] | None = None) -> str:
        if self._saved_path:
            return self._saved_path

        os.makedirs(self.output_dir, exist_ok=True)
        filename = f"run_metrics_{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}.json"
        path = os.path.abspath(os.path.join(self.output_dir, filename))
        payload = self.to_dict(metadata=metadata)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        self._saved_path = path
        logger.info(f"Run metrics saved: {path}")
        return path

    def to_dict(self, *, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        snapshot = self.snapshot()
        rates = asdict(self.rates)
        regular_input_tokens = max(
            snapshot.llm_prompt_tokens
            - snapshot.llm_cached_input_tokens
            - snapshot.llm_cache_creation_input_tokens,
            0,
        )
        return {
            "created_at": datetime.now(UTC).isoformat(),
            "metadata": metadata or {},
            "rates": rates,
            "usage": {
                "input_audio_seconds": snapshot.input_audio_seconds,
                "input_audio_minutes": snapshot.input_audio_seconds / 60,
                "llm_prompt_tokens": snapshot.llm_prompt_tokens,
                "llm_regular_input_tokens": regular_input_tokens,
                "llm_cached_input_tokens": snapshot.llm_cached_input_tokens,
                "llm_cache_creation_input_tokens": snapshot.llm_cache_creation_input_tokens,
                "llm_completion_tokens": snapshot.llm_completion_tokens,
                "llm_total_tokens": snapshot.llm_prompt_tokens + snapshot.llm_completion_tokens,
                "tts_chars": snapshot.tts_chars,
                "llm_usage_events_count": len(self.llm_usage_events),
                "tts_usage_events_count": len(self.tts_usage_events),
            },
            "costs": {
                "currency": snapshot.currency,
                "llm_cost": snapshot.llm_cost,
                "tts_cost": snapshot.tts_cost,
                "stt_cost": snapshot.stt_cost,
                "total_cost": snapshot.total_cost,
            },
            "latencies": {
                key: asdict(value)
                for key, value in sorted(snapshot.latencies.items())
            },
            "raw_metrics": {
                "llm_usage_events": self.llm_usage_events,
                "tts_usage_events": self.tts_usage_events,
                "latency_events": self.latency_events,
            },
        }


class RunCostMeter(FrameProcessor):
    """Pipeline tap that forwards frames unchanged while collecting usage."""

    def __init__(self, tracker: RunCostTracker, *, name: str = "run_cost_meter"):
        super().__init__(name=name)
        self._tracker = tracker

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        if direction == FrameDirection.DOWNSTREAM:
            if isinstance(frame, InputAudioRawFrame):
                self._tracker.add_input_audio(frame)
            elif isinstance(frame, MetricsFrame):
                self._tracker.add_metrics(frame)

        await self.push_frame(frame, direction)
