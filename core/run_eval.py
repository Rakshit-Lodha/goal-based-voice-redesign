"""Binary evals for saved live-run transcripts."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


EXPECTED_TOOL_ORDER = [
    "assess_risk_profile",
    "add_family",
    "pull_mf_central",
    "pull_account_aggregator",
    "add_manual_asset",
    "confirm_financial_snapshot",
    "add_goal",
    "project_existing_corpus",
    "compute_gap_and_sip",
    "reprioritize",
    "build_goal_portfolio",
    "generate_plan_pdf",
]


@dataclass
class EvalCheck:
    name: str
    passed: bool
    detail: str = ""


@dataclass
class EvalResult:
    passed: bool
    checks: list[EvalCheck] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "checks": [check.__dict__ for check in self.checks],
        }


def load_transcript(path: str | Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def evaluate_transcript(transcript: dict[str, Any]) -> EvalResult:
    events = transcript.get("events", [])
    checks = [
        _has_user_and_assistant_messages(events),
        _tool_calls_have_results(events),
        _tool_order_is_allowed(events),
        _consent_before_provider_pulls(events),
        _financial_snapshot_before_goals(events),
        _plan_pdf_generated(events),
        _assistant_does_not_expose_tool_json(events),
    ]
    return EvalResult(passed=all(check.passed for check in checks), checks=checks)


def evaluate_transcript_file(path: str | Path) -> EvalResult:
    return evaluate_transcript(load_transcript(path))


def _tool_calls(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [event for event in events if event.get("type") == "tool_call"]


def _tool_results(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [event for event in events if event.get("type") == "tool_result"]


def _has_user_and_assistant_messages(events: list[dict[str, Any]]) -> EvalCheck:
    user_count = sum(1 for e in events if e.get("type") == "message" and e.get("role") == "user")
    assistant_count = sum(
        1 for e in events if e.get("type") == "message" and e.get("role") == "assistant"
    )
    return EvalCheck(
        name="conversation_has_both_sides",
        passed=user_count > 0 and assistant_count > 0,
        detail=f"user_messages={user_count}, assistant_messages={assistant_count}",
    )


def _tool_calls_have_results(events: list[dict[str, Any]]) -> EvalCheck:
    failures = []
    pending = []
    for event in events:
        if event.get("type") == "tool_call":
            pending.append(event.get("name"))
        elif event.get("type") == "tool_result":
            name = event.get("name")
            if not pending:
                failures.append(f"unexpected result {name}")
            elif pending.pop(0) != name:
                failures.append(f"result {name} did not match oldest pending call")
    failures.extend(f"missing result for {name}" for name in pending)
    return EvalCheck(
        name="tool_calls_have_matching_results",
        passed=not failures,
        detail="; ".join(failures) if failures else f"tool_calls={len(_tool_calls(events))}",
    )


def _tool_order_is_allowed(events: list[dict[str, Any]]) -> EvalCheck:
    failures = []
    seen = set()
    for event in _tool_calls(events):
        name = event.get("name")
        if name not in EXPECTED_TOOL_ORDER:
            failures.append(f"unknown tool {name}")
            continue
        if name == "pull_account_aggregator" and "pull_mf_central" not in seen:
            failures.append("pull_account_aggregator appeared before pull_mf_central")
        elif name == "confirm_financial_snapshot" and "pull_account_aggregator" not in seen:
            failures.append("confirm_financial_snapshot appeared before pull_account_aggregator")
        elif name == "project_existing_corpus" and "add_goal" not in seen:
            failures.append("project_existing_corpus appeared before add_goal")
        elif name == "compute_gap_and_sip" and "project_existing_corpus" not in seen:
            failures.append("compute_gap_and_sip appeared before project_existing_corpus")
        elif name == "reprioritize" and "compute_gap_and_sip" not in seen:
            failures.append("reprioritize appeared before compute_gap_and_sip")
        elif name == "build_goal_portfolio" and "compute_gap_and_sip" not in seen:
            failures.append("build_goal_portfolio appeared before compute_gap_and_sip")
        elif name == "generate_plan_pdf" and "build_goal_portfolio" not in seen:
            failures.append("generate_plan_pdf appeared before build_goal_portfolio")
        seen.add(name)
    return EvalCheck(
        name="tool_order_is_allowed",
        passed=not failures,
        detail="; ".join(failures) if failures else "prerequisites respected",
    )


def _consent_before_provider_pulls(events: list[dict[str, Any]]) -> EvalCheck:
    failures = []
    for event in _tool_calls(events):
        name = event.get("name")
        if name not in {"pull_mf_central", "pull_account_aggregator"}:
            continue
        args = event.get("arguments") or {}
        if args.get("user_confirmed_consent") is not True:
            failures.append(f"{name} missing user_confirmed_consent=true")
        if not str(args.get("consent_context") or "").strip():
            failures.append(f"{name} missing consent_context")
    return EvalCheck(
        name="consent_required_for_data_pulls",
        passed=not failures,
        detail="; ".join(failures) if failures else "consent arguments present",
    )


def _financial_snapshot_before_goals(events: list[dict[str, Any]]) -> EvalCheck:
    finances_confirmed = False
    failures = []
    for event in events:
        if event.get("type") != "tool_result":
            continue
        if event.get("name") == "confirm_financial_snapshot":
            result = event.get("result") or {}
            finances_confirmed = result.get("financial_snapshot_confirmed") is True
        if event.get("name") == "add_goal" and not finances_confirmed:
            failures.append("add_goal result appeared before financial snapshot confirmation")
    return EvalCheck(
        name="financial_snapshot_confirmed_before_goals",
        passed=not failures,
        detail="; ".join(failures) if failures else f"confirmed={finances_confirmed}",
    )


def _plan_pdf_generated(events: list[dict[str, Any]]) -> EvalCheck:
    for event in _tool_results(events):
        if event.get("name") != "generate_plan_pdf":
            continue
        result = event.get("result") or {}
        if result.get("url") or result.get("path"):
            return EvalCheck("plan_pdf_generated", True, "generate_plan_pdf returned a link/path")
        return EvalCheck("plan_pdf_generated", False, "generate_plan_pdf result lacked url/path")
    return EvalCheck("plan_pdf_generated", False, "generate_plan_pdf was not called")


def _assistant_does_not_expose_tool_json(events: list[dict[str, Any]]) -> EvalCheck:
    suspicious = []
    forbidden = ["tool_call", "tool_result", "narration_hint", '"progress"', '"next_step"']
    for event in events:
        if event.get("type") == "message" and event.get("role") == "assistant":
            text = event.get("text") or ""
            if any(marker in text for marker in forbidden):
                suspicious.append(text[:80])
    return EvalCheck(
        name="assistant_does_not_expose_internal_json",
        passed=not suspicious,
        detail="; ".join(suspicious) if suspicious else "no internal markers found",
    )
