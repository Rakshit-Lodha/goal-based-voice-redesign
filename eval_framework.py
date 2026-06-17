"""Maya / Wealth Expert transcript evaluation framework.

Rubric-driven evaluator. Each section has a list of sub-modules; each sub-module
is either a deterministic 'Tool call' check (run now) or an 'LLM as a judge'
check (defined, stubbed, NOT executed). One sheet per section in the output
workbook. Yes/No verdicts throughout.

LLM calls are never executed in the runnable path. The judge function is a
stub gated behind --judge.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from collections import OrderedDict
from pathlib import Path
from typing import Any, Callable

try:
    import openpyxl
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False

try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

try:
    from dotenv import load_dotenv
    load_dotenv()  # pick up OPENAI_API_KEY from .env if present
except ImportError:
    pass

OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-5.5")
_openai_client = None


def _get_openai_client():
    global _openai_client
    if _openai_client is None:
        if not HAS_OPENAI:
            raise RuntimeError(
                "openai SDK not installed. Run: pip install openai"
            )
        _openai_client = OpenAI()  # reads OPENAI_API_KEY from env
    return _openai_client


# =============================================================================
# Tool → conversation-section mapping (used only for auto-detecting boundaries).
# Multiple rubric sections can map to one underlying tool section (e.g.
# mf_central + portfolio_review both ride pull_mf_central; aa + investments
# both ride pull_account_aggregator).
# =============================================================================

SECTION_TOOLS: "OrderedDict[str, set[str]]" = OrderedDict([
    ("risk_profile",       {"assess_risk_profile"}),
    ("family",             {"add_family"}),
    ("mf_central",         {"pull_mf_central"}),
    ("account_aggregator", {"pull_account_aggregator", "add_manual_asset",
                            "confirm_financial_snapshot"}),
    ("goals_planning",     {"add_goal", "project_existing_corpus",
                            "compute_gap_and_sip", "reprioritize"}),
    ("final_plan",         {"build_goal_portfolio", "generate_plan_pdf"}),
])

# Order of rubric sheets in the output workbook.
RUBRIC_SECTIONS = [
    "risk_profile", "family",
    "mf_central", "portfolio_review",
    "aa", "investments",
    "goals_planning", "final_plan",
]


# =============================================================================
# Output schema
# =============================================================================

COLS = [
    "sub_module", "type", "verdict", "explanation",
    "human_verdict", "human_notes", "agreement",
    "event_range", "transcript_excerpt",
]

EXCERPT_CHAR_LIMIT = 4000

STATUS_FILLS = {"Yes": "C6EFCE", "No": "FFC7CE", "": "FFFFFF"}


# =============================================================================
# Judge prompt templates — strict JSON, calibration-aware.
# =============================================================================

_JUDGE_PREAMBLE = (
    "You are evaluating a single rubric item against a transcript slice from a "
    "financial-advisory voice agent (Maya / Wealth Expert).\n\n"
    "Mark verdict='No' ONLY if Maya: (a) states a fact that contradicts the "
    "tool result, (b) omits a specific behaviour the rubric requires, or "
    "(c) fabricates information not present in the conversation or tool "
    "results. Do NOT mark 'No' merely because phrasing differs.\n\n"
    "Return STRICT JSON ONLY — no prose, no markdown fences:\n"
    '{"verdict": "Yes" | "No", "explanation": "<=40 words"}\n'
)

JUDGE_PROMPTS: dict[str, str] = {
    # ---- risk_profile ----
    "risk_identifying_answer": _JUDGE_PREAMBLE + (
        "\nRUBRIC: Identifying Answer (Risk Profile).\n"
        "YES if: the tool call's `answers` array faithfully reflects each user "
        "answer; STT garbles are disambiguated from context (e.g. 'I will talk "
        "up' → 'top up'); every risk question asked has a captured answer.\n"
        "NO if: a user preference is flipped/mis-mapped; Maya fabricated an "
        "answer not given; Maya skipped a question and called the tool with "
        "incomplete inputs.\n"
        "Mild paraphrasing in tool args is OK — judge intent, not exact strings.\n\n"
        "TRANSCRIPT SLICE (risk Q&A turns):\n{slice}\n\n"
        "TOOL CALL ARGUMENTS:\n{tool_args}\n"
    ),
    "risk_explanation_implication": _JUDGE_PREAMBLE + (
        "\nRUBRIC: Explanation of Risk Profile + Broader Implication.\n"
        "YES requires ALL FOUR:\n"
        "  1. States the risk-profile label (e.g. 'aggressive').\n"
        "  2. States the equity band as a percentage matching the tool result.\n"
        "  3. States the expected return as a percentage matching the tool result.\n"
        "  4. Adds a broader implication tying the profile to volatility "
        "tolerance, planning horizon, drawdown comfort, or upside potential — "
        "not just the bare numbers.\n"
        "NO if any of the three numeric/categorical facts is missing or "
        "contradicts the tool result, OR no broader implication is given, OR "
        "the implication is a generic platitude with no tie to volatility / "
        "horizon / drawdown.\n\n"
        "TRANSCRIPT SLICE (Maya's read-back):\n{slice}\n\n"
        "TOOL RESULT (ground truth):\n{tool_result}\n"
    ),
    "risk_compliance": _JUDGE_PREAMBLE + (
        "\nRUBRIC: Compliance (Risk Profile).\n"
        "YES requires ALL: framed as profiling not advice/guarantees; hedged "
        "language for returns ('expected', 'estimated', 'projected'); no "
        "specific product/fund names during profiling; no promise of capital "
        "protection or guaranteed outperformance.\n"
        "NO if: any guarantee language ('you will earn 13%', 'guaranteed', "
        "'definitely'); names specific products/funds during profiling; "
        "implies the equity band or expected return is a promise.\n\n"
        "TRANSCRIPT SLICE (entire risk-profile section):\n{slice}\n"
    ),

    # ---- family ----
    "family_identifying_composition": _JUDGE_PREAMBLE + (
        "\nRUBRIC: Identifying Family Composition.\n"
        "YES if: Maya correctly captured spouse (existence + age if applicable), "
        "every child mentioned (with age), and any other dependents, mapping "
        "them to the add_family tool args even if STT garbled some turns.\n"
        "NO if: Maya missed a family member the user explicitly mentioned; "
        "fabricated a member; recorded an age inconsistent with what the user "
        "actually said.\n\n"
        "TRANSCRIPT SLICE (family Q&A turns):\n{slice}\n\n"
        "TOOL CALL ARGUMENTS:\n{tool_args}\n"
    ),
    "family_acknowledgement_implication": _JUDGE_PREAMBLE + (
        "\nRUBRIC: Acknowledgement & Plan Impact (Family).\n"
        "YES if: Maya acknowledged the family details warmly AND tied at least "
        "one detail to planning impact (e.g. 'two kids — we'll plan an "
        "education goal', 'spouse working — we can plan joint goals').\n"
        "NO if: the family is captured but never tied to planning, OR Maya "
        "moves on without acknowledgement.\n\n"
        "TRANSCRIPT SLICE (assistant turn(s) after add_family):\n{slice}\n"
    ),

    # ---- mf_central (the *interaction* layer of pull_mf_central) ----
    "mfc_explanation": _JUDGE_PREAMBLE + (
        "\nRUBRIC: Explanation (MF Central).\n"
        "YES if: Before requesting consent, Maya explained what MF Central is "
        "and what specifically will be pulled (e.g. holdings + SIPs across "
        "mutual funds), in plain language.\n"
        "NO if: Maya jumped straight to the OTP/consent request with no "
        "explanation, OR the explanation is so vague the user could not "
        "reasonably consent informed.\n\n"
        "TRANSCRIPT SLICE (around the pull_mf_central call):\n{slice}\n"
    ),
    "mfc_rebuttal": _JUDGE_PREAMBLE + (
        "\nRUBRIC: Rebuttal if Asked (MF Central).\n"
        "If the user pushed back on the MF Central pull (privacy worry, "
        "skepticism, refusal), did Maya respond with a substantive rebuttal "
        "grounded in why MFC is safe / standard / necessary?\n"
        "YES if the user did NOT push back (N/A → mark YES) OR Maya responded "
        "appropriately.\n"
        "NO if the user pushed back and Maya capitulated, ignored, or gave a "
        "non-answer.\n\n"
        "TRANSCRIPT SLICE (whole MF Central interaction):\n{slice}\n"
    ),
    "mfc_consent": _JUDGE_PREAMBLE + (
        "\nRUBRIC: Consent (MF Central).\n"
        "YES if: Maya verbally asked the user for consent to pull MF Central "
        "AND the user verbally agreed BEFORE the tool was called.\n"
        "NO if: the pull happened without an explicit verbal ask, OR without "
        "an explicit verbal user agreement, OR the user objected and the pull "
        "still happened.\n\n"
        "TRANSCRIPT SLICE (turns leading into the pull_mf_central call):\n{slice}\n\n"
        "TOOL CALL ARGUMENTS (for cross-reference; user_confirmed_consent flag "
        "must be true AND verbally backed):\n{tool_args}\n"
    ),

    # ---- portfolio_review (the *content* layer of pull_mf_central) ----
    "portfolio_overview_mf": _JUDGE_PREAMBLE + (
        "\nRUBRIC: Overview of MF (Portfolio Review).\n"
        "YES if: Maya summarized the user's mutual-fund portfolio from the "
        "tool result — at minimum total portfolio value, equity/debt split, "
        "and total monthly SIP — with numbers matching the tool result.\n"
        "NO if: any of those headline numbers is missing, OR any number "
        "contradicts the tool result, OR Maya gives only platitudes "
        "('looks good') without quantitative summary.\n\n"
        "TRANSCRIPT SLICE (Maya's portfolio narration):\n{slice}\n\n"
        "TOOL RESULT (ground truth):\n{tool_result}\n"
    ),
    "portfolio_explaining_next_steps": _JUDGE_PREAMBLE + (
        "\nRUBRIC: Explaining + Next Steps (Portfolio Review).\n"
        "YES if: Maya explained which funds are underperformers vs good funds "
        "(per the tool's fund_reviews / review_methodology) AND named the next "
        "step for the user (e.g. 'we'll move to AA next', 'consider reviewing "
        "the underperformers later').\n"
        "NO if: the underperformer/good split is not communicated, OR no next "
        "step is stated.\n\n"
        "TRANSCRIPT SLICE (Maya's portfolio narration):\n{slice}\n\n"
        "TOOL RESULT (ground truth):\n{tool_result}\n"
    ),

    # ---- aa (the *interaction* layer of pull_account_aggregator) ----
    "aa_consent": _JUDGE_PREAMBLE + (
        "\nRUBRIC: Consent (Account Aggregator).\n"
        "YES if: Maya verbally asked for consent to pull AA AND the user "
        "verbally agreed BEFORE the tool was called.\n"
        "NO if: no explicit verbal ask, no explicit verbal agreement, or "
        "objection-then-pull.\n\n"
        "TRANSCRIPT SLICE (turns leading into pull_account_aggregator):\n{slice}\n\n"
        "TOOL CALL ARGUMENTS:\n{tool_args}\n"
    ),
    "aa_rebuttal": _JUDGE_PREAMBLE + (
        "\nRUBRIC: Rebuttal if Asked (Account Aggregator).\n"
        "If the user pushed back on the AA pull, did Maya rebut substantively?\n"
        "YES if no pushback (N/A → YES), or Maya rebutted appropriately.\n"
        "NO if user pushed back and Maya capitulated/ignored/non-answered.\n\n"
        "TRANSCRIPT SLICE (whole AA interaction):\n{slice}\n"
    ),
    "aa_explanation": _JUDGE_PREAMBLE + (
        "\nRUBRIC: Explanation (Account Aggregator).\n"
        "YES if: Before requesting consent, Maya explained what AA is and what "
        "will be pulled (income / expenses / EMI / investments breakdown), in "
        "plain language.\n"
        "NO if: Maya jumped to OTP/consent with no explanation, OR explanation "
        "is too vague for informed consent.\n\n"
        "TRANSCRIPT SLICE (around the pull_account_aggregator call):\n{slice}\n"
    ),

    # ---- investments (manual asset add-on flow after AA pull) ----
    "investments_updation_addition": _JUDGE_PREAMBLE + (
        "\nRUBRIC: Updation / Addition (Investments — Optional).\n"
        "After the AA pull, Maya should ask whether the user holds any assets "
        "not visible to AA (real estate, gold, ESOPs, fixed deposits, etc.). "
        "If the user named any, they should appear via add_manual_asset.\n"
        "YES if: Maya asked about additional assets AND every asset the user "
        "named was captured via add_manual_asset (or N/A if the user had none "
        "and Maya still asked — YES in that case).\n"
        "NO if: Maya never asked about additional assets, OR the user named "
        "an asset that was not captured.\n\n"
        "TRANSCRIPT SLICE (manual asset turns):\n{slice}\n\n"
        "MANUAL ASSET TOOL CALLS (for ground truth):\n{tool_args}\n"
    ),

    # ---- goals_planning ----
    "goals_introduction": _JUDGE_PREAMBLE + (
        "\nRUBRIC: Introduction (Goals Planning).\n"
        "YES if: Before the first add_goal call, Maya introduced the goals "
        "phase — explained what we're about to do (capture life goals, inflate "
        "to target year, project corpus, find gap, plan SIP).\n"
        "NO if: Maya jumped straight to 'tell me your first goal' with no "
        "framing of what the goals phase will produce.\n\n"
        "TRANSCRIPT SLICE (turns immediately before the first add_goal):\n{slice}\n"
    ),
    "goals_explanation_calc": _JUDGE_PREAMBLE + (
        "\nRUBRIC: Explanation of Goal + Calc (Goals Planning).\n"
        "For EVERY goal, after the relevant tool calls (add_goal, "
        "project_existing_corpus, compute_gap_and_sip), Maya should explain in "
        "plain language: (a) the inflated target, (b) the projected coverage "
        "from existing corpus, (c) the gap, and (d) the required SIP — with "
        "numbers matching the tool results. No fabricated numbers.\n"
        "YES if every goal got that explanation accurately.\n"
        "NO if any goal skipped the math summary, or any number was wrong, or "
        "Maya fabricated a number.\n\n"
        "TRANSCRIPT SLICE (goals narration turns):\n{slice}\n\n"
        "TOOL RESULTS (ground truth):\n{tool_result}\n"
    ),

    # ---- final_plan ----
    "final_plan_explanation_portfolio": _JUDGE_PREAMBLE + (
        "\nRUBRIC: Explanation of Portfolio (Final Plan).\n"
        "After build_goal_portfolio fires (once per goal), Maya should describe "
        "the portfolio per goal — horizon bucket, monthly SIP, allocation "
        "phases — with numbers matching the tool result.\n"
        "YES if every goal's portfolio was described and numbers match.\n"
        "NO if any goal's portfolio is omitted, or numbers contradict the tool "
        "result, or Maya speaks in generalities without per-goal detail.\n\n"
        "TRANSCRIPT SLICE (final plan narration):\n{slice}\n\n"
        "TOOL RESULTS (ground truth):\n{tool_result}\n"
    ),
    "final_plan_answering_questions": _JUDGE_PREAMBLE + (
        "\nRUBRIC: Answering Questions (Final Plan).\n"
        "YES if: Maya invited questions after delivering the plan AND addressed "
        "every user question that followed (or there were no questions and "
        "Maya still invited them — YES in that case).\n"
        "NO if: Maya did not invite questions, OR a user question was ignored / "
        "deflected without an answer.\n\n"
        "TRANSCRIPT SLICE (final plan turns + Q&A tail):\n{slice}\n"
    ),
}


# =============================================================================
# LLM JUDGE — STUB. Wire here only.
# =============================================================================

def run_judge(prompt_key: str, slice_text: str,
              tool_args: str = "", tool_result: str = "") -> dict:
    """Execute the LLM judge for a single rubric item via OpenAI (GPT-5.5).

    Returns: {"verdict": "Yes" | "No" | "", "explanation": str}
    On error, verdict is "" and explanation contains the diagnostic.
    """
    template = JUDGE_PROMPTS.get(prompt_key)
    if template is None:
        return {"verdict": "", "explanation": f"[unknown prompt_key: {prompt_key}]"}
    prompt = (template
              .replace("{slice}", slice_text or "")
              .replace("{tool_args}", tool_args or "")
              .replace("{tool_result}", tool_result or ""))
    try:
        client = _get_openai_client()
    except Exception as e:
        return {"verdict": "", "explanation": f"[client init failed: {e}]"}
    try:
        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
    except Exception as e:
        return {"verdict": "", "explanation": f"[judge call failed: {e}]"}
    text = (resp.choices[0].message.content or "").strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return {"verdict": "",
                "explanation": f"[JSON parse failed: {text[:200]}]"}
    verdict = data.get("verdict", "")
    explanation = (data.get("explanation", "") or "").strip()
    if verdict not in ("Yes", "No"):
        return {"verdict": "",
                "explanation": f"[invalid verdict {verdict!r}: {explanation}]"}
    return {"verdict": verdict, "explanation": explanation}


def _dump_args(call: dict | None) -> str:
    if not call:
        return ""
    return json.dumps(call.get("arguments", {}), ensure_ascii=False, indent=2)


def _dump_result(result_event: dict | None) -> str:
    if not result_event:
        return ""
    r = result_event.get("result", {})
    if isinstance(r, dict):
        r = {k: v for k, v in r.items()
             if k not in ("narration_hint", "progress", "next_step")}
    return json.dumps(r, ensure_ascii=False, indent=2)


def grounding_for(prompt_key: str, events: list[dict]) -> tuple[str, str]:
    """Return (tool_args_blob, tool_result_blob) for a judge prompt key."""
    if prompt_key == "risk_identifying_answer":
        c = find_first_tool_call(events, "assess_risk_profile")
        return (_dump_args(c), "")
    if prompt_key == "risk_explanation_implication":
        c = find_first_tool_call(events, "assess_risk_profile")
        r = result_after(events, c["_idx"], "assess_risk_profile") if c else None
        return ("", _dump_result(r))
    if prompt_key == "risk_compliance":
        return ("", "")

    if prompt_key in ("family_identifying_composition",
                      "family_acknowledgement_implication"):
        c = find_first_tool_call(events, "add_family")
        return (_dump_args(c), "")

    if prompt_key in ("mfc_explanation", "mfc_consent"):
        c = find_first_tool_call(events, "pull_mf_central")
        return (_dump_args(c), "")
    if prompt_key == "mfc_rebuttal":
        return ("", "")

    if prompt_key in ("portfolio_overview_mf", "portfolio_explaining_next_steps"):
        c = find_first_tool_call(events, "pull_mf_central")
        r = result_after(events, c["_idx"], "pull_mf_central") if c else None
        return ("", _dump_result(r))

    if prompt_key in ("aa_consent", "aa_explanation"):
        c = find_first_tool_call(events, "pull_account_aggregator")
        return (_dump_args(c), "")
    if prompt_key == "aa_rebuttal":
        return ("", "")

    if prompt_key == "investments_updation_addition":
        calls = find_all_tool_calls(events, "add_manual_asset")
        blob = json.dumps([c.get("arguments", {}) for c in calls],
                          ensure_ascii=False, indent=2)
        return (blob, "")

    if prompt_key == "goals_introduction":
        return ("", "")
    if prompt_key == "goals_explanation_calc":
        names = ["add_goal", "project_existing_corpus",
                 "compute_gap_and_sip", "reprioritize"]
        all_results = []
        for n in names:
            all_results.extend(find_all_tool_results(events, n))
        all_results.sort(key=lambda e: e["_idx"])
        blob = json.dumps(
            [{
                "tool": e["name"],
                "result": {k: v for k, v in (e.get("result") or {}).items()
                           if k not in ("narration_hint", "progress", "next_step")},
            } for e in all_results],
            ensure_ascii=False, indent=2,
        )
        return ("", blob)

    if prompt_key == "final_plan_explanation_portfolio":
        bgp = find_all_tool_results(events, "build_goal_portfolio")
        blob = json.dumps(
            [{k: v for k, v in (e.get("result") or {}).items()
              if k not in ("narration_hint", "progress", "next_step")}
             for e in bgp],
            ensure_ascii=False, indent=2,
        )
        return ("", blob)
    if prompt_key == "final_plan_answering_questions":
        return ("", "")

    return ("", "")


# =============================================================================
# Transcript parsing & slicing primitives
# =============================================================================

def load_transcript(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    events = data.get("events", [])
    for i, e in enumerate(events):
        e["_idx"] = i
    return events


def tool_to_section(name: str) -> str | None:
    for section, tools in SECTION_TOOLS.items():
        if name in tools:
            return section
    return None


def detect_sections(events: list[dict]) -> dict[str, tuple[int, int]]:
    """Return {tool_section_name: (lo, hi)} inclusive event-index ranges.
    Boundaries are derived from the first occurrence of each section's
    canonical tools — never hard-coded indices."""
    first_idx: dict[str, int] = {}
    last_tool_idx = -1
    for e in events:
        if e["type"] == "tool_call":
            sec = tool_to_section(e["name"])
            if sec and sec not in first_idx:
                first_idx[sec] = e["_idx"]
        if e["type"] in ("tool_call", "tool_result"):
            last_tool_idx = e["_idx"]

    ranges: dict[str, tuple[int, int]] = {}
    if not first_idx:
        ranges["intro"] = (0, len(events) - 1)
        return ranges
    observed = sorted(first_idx.items(), key=lambda kv: kv[1])
    first_start = observed[0][1]
    if first_start > 0:
        ranges["intro"] = (0, first_start - 1)
    for i, (sec, start) in enumerate(observed):
        end = observed[i + 1][1] - 1 if i + 1 < len(observed) else last_tool_idx
        ranges[sec] = (start, end)
    if last_tool_idx + 1 <= len(events) - 1:
        ranges["closing"] = (last_tool_idx + 1, len(events) - 1)
    return ranges


def events_in_range(events: list[dict], lo: int, hi: int) -> list[dict]:
    return [e for e in events if lo <= e["_idx"] <= hi]


def range_str(lo: int, hi: int) -> str:
    if lo > hi:
        return "-"
    return f"{lo}-{hi}" if lo != hi else f"{lo}"


def format_excerpt(events: list[dict], lo: int, hi: int,
                   limit: int = EXCERPT_CHAR_LIMIT) -> str:
    if lo > hi:
        return ""
    lines: list[str] = []
    for e in events_in_range(events, lo, hi):
        idx = e["_idx"]
        if e["type"] == "message":
            role = e.get("role", "?")
            text = (e.get("text") or "").strip()
            lines.append(f"[{idx}] {role}: {text}")
        elif e["type"] == "tool_call":
            args_str = json.dumps(e.get("arguments", {}), ensure_ascii=False)
            if len(args_str) > 280:
                args_str = args_str[:277] + "..."
            lines.append(f"[{idx}] TOOL_CALL {e.get('name')}({args_str})")
        elif e["type"] == "tool_result":
            result = e.get("result", {})
            if isinstance(result, dict):
                trimmed = {k: result[k] for k in result
                           if k not in ("narration_hint", "progress", "next_step")}
                res_str = json.dumps(trimmed, ensure_ascii=False)
            else:
                res_str = json.dumps(result, ensure_ascii=False)
            if len(res_str) > 420:
                res_str = res_str[:417] + "..."
            lines.append(f"[{idx}] TOOL_RESULT {e.get('name')} -> {res_str}")
    text = "\n".join(lines)
    if len(text) > limit:
        text = text[: limit - len(" ...[truncated]")] + " ...[truncated]"
    return text


# ----- locating helpers -----

def find_first_tool_call(events: list[dict], name: str) -> dict | None:
    for e in events:
        if e["type"] == "tool_call" and e.get("name") == name:
            return e
    return None


def find_all_tool_calls(events: list[dict], name: str) -> list[dict]:
    return [e for e in events
            if e["type"] == "tool_call" and e.get("name") == name]


def find_all_tool_results(events: list[dict], name: str) -> list[dict]:
    return [e for e in events
            if e["type"] == "tool_result" and e.get("name") == name]


def result_after(events: list[dict], call_idx: int, name: str) -> dict | None:
    if call_idx + 1 >= len(events):
        return None
    nxt = events[call_idx + 1]
    if nxt["type"] == "tool_result" and nxt.get("name") == name:
        return nxt
    return None


def messages_before_idx(events: list[dict], idx: int, stop_at_tool=True
                        ) -> tuple[int, int]:
    """Walk backward from idx-1 collecting contiguous message events.
    Returns (lo, hi) inclusive. If no messages, returns (idx, idx-1) (empty)."""
    end = idx - 1
    if end < 0:
        return (0, -1)
    start = end
    while start > 0:
        prev = events[start - 1]
        if prev["type"] == "message":
            start -= 1
            continue
        if stop_at_tool and prev["type"] in ("tool_call", "tool_result"):
            break
        break
    if end < start:
        return (idx, idx - 1)
    return (start, end)


def messages_after_idx(events: list[dict], idx: int,
                       role_filter: str | None = None) -> tuple[int, int]:
    """Walk forward from idx+1 collecting contiguous message events.
    Optionally filter by role (e.g. only contiguous assistant messages)."""
    start = idx + 1
    if start >= len(events):
        return (start, start - 1)
    end = start - 1
    while end + 1 < len(events):
        nxt = events[end + 1]
        if nxt["type"] != "message":
            break
        if role_filter and nxt.get("role") != role_filter:
            break
        end += 1
    return (start, end)


# =============================================================================
# Slice functions — each sub-module gets the surgical event range it grades.
# =============================================================================

def slice_section_or_empty(section_range: tuple[int, int] | None
                           ) -> tuple[int, int]:
    return section_range if section_range else (0, -1)


# ---- risk_profile ----

def slice_risk_identifying(events, _):
    call = find_first_tool_call(events, "assess_risk_profile")
    if call is None:
        return (0, -1)
    return messages_before_idx(events, call["_idx"])


def slice_risk_tool(events, _):
    call = find_first_tool_call(events, "assess_risk_profile")
    if call is None:
        return (0, -1)
    res = result_after(events, call["_idx"], "assess_risk_profile")
    return (call["_idx"], res["_idx"] if res else call["_idx"])


def slice_risk_explanation(events, _):
    call = find_first_tool_call(events, "assess_risk_profile")
    if call is None:
        return (0, -1)
    res = result_after(events, call["_idx"], "assess_risk_profile")
    anchor = res["_idx"] if res else call["_idx"]
    return messages_after_idx(events, anchor, role_filter="assistant")


def slice_risk_compliance(events, section_range):
    return slice_section_or_empty(section_range)


# ---- family ----

def slice_family_identifying(events, _):
    call = find_first_tool_call(events, "add_family")
    if call is None:
        return (0, -1)
    return messages_before_idx(events, call["_idx"])


def slice_family_tool(events, _):
    call = find_first_tool_call(events, "add_family")
    if call is None:
        return (0, -1)
    res = result_after(events, call["_idx"], "add_family")
    return (call["_idx"], res["_idx"] if res else call["_idx"])


def slice_family_acknowledgement(events, _):
    call = find_first_tool_call(events, "add_family")
    if call is None:
        return (0, -1)
    res = result_after(events, call["_idx"], "add_family")
    anchor = res["_idx"] if res else call["_idx"]
    return messages_after_idx(events, anchor, role_filter="assistant")


# ---- mf_central ----

def slice_mfc_explanation(events, _):
    """Messages immediately before pull_mf_central — where Maya explains it."""
    call = find_first_tool_call(events, "pull_mf_central")
    if call is None:
        return (0, -1)
    return messages_before_idx(events, call["_idx"])


def slice_mfc_consent(events, _):
    """Same as explanation slice — the consent ask happens in the same turns."""
    return slice_mfc_explanation(events, _)


def slice_mfc_rebuttal(events, section_range):
    """The whole mf_central tool-section, so the judge can spot any pushback."""
    call = find_first_tool_call(events, "pull_mf_central")
    if call is None:
        return (0, -1)
    pre_lo, _ = messages_before_idx(events, call["_idx"])
    res = result_after(events, call["_idx"], "pull_mf_central")
    if section_range:
        return (min(pre_lo, section_range[0]), section_range[1])
    return (pre_lo, res["_idx"] if res else call["_idx"])


# ---- portfolio_review (rides pull_mf_central narration) ----

def slice_portfolio_narration(events, section_range):
    """Assistant turn(s) after pull_mf_central result through end of section."""
    call = find_first_tool_call(events, "pull_mf_central")
    if call is None:
        return (0, -1)
    res = result_after(events, call["_idx"], "pull_mf_central")
    start = (res["_idx"] + 1) if res else (call["_idx"] + 1)
    if section_range:
        return (start, section_range[1])
    end = start - 1
    while end + 1 < len(events) and events[end + 1]["type"] == "message":
        end += 1
    return (start, end)


def slice_portfolio_tool(events, _):
    call = find_first_tool_call(events, "pull_mf_central")
    if call is None:
        return (0, -1)
    res = result_after(events, call["_idx"], "pull_mf_central")
    return (call["_idx"], res["_idx"] if res else call["_idx"])


# ---- aa (interaction layer of pull_account_aggregator) ----

def slice_aa_consent(events, _):
    call = find_first_tool_call(events, "pull_account_aggregator")
    if call is None:
        return (0, -1)
    return messages_before_idx(events, call["_idx"])


def slice_aa_explanation(events, _):
    return slice_aa_consent(events, _)


def slice_aa_rebuttal(events, section_range):
    call = find_first_tool_call(events, "pull_account_aggregator")
    if call is None:
        return (0, -1)
    pre_lo, _ = messages_before_idx(events, call["_idx"])
    if section_range:
        return (min(pre_lo, section_range[0]), section_range[1])
    res = result_after(events, call["_idx"], "pull_account_aggregator")
    return (pre_lo, res["_idx"] if res else call["_idx"])


# ---- investments (manual-asset / additional-pulls layer) ----

def slice_investments_pulls(events, section_range):
    """All pull_account_aggregator + confirm_financial_snapshot events."""
    indices = [e["_idx"] for e in events
               if e["type"] in ("tool_call", "tool_result")
               and e.get("name") in
               ("pull_account_aggregator", "confirm_financial_snapshot")]
    if not indices:
        return slice_section_or_empty(section_range)
    return (min(indices), max(indices))


def slice_investments_updation(events, section_range):
    """The conversation around add_manual_asset calls (if any)."""
    asset_calls = find_all_tool_calls(events, "add_manual_asset")
    if not asset_calls:
        # Use the post-AA-pull narration as the slice so the judge can see the
        # turn where Maya should have asked.
        ag_call = find_first_tool_call(events, "pull_account_aggregator")
        if ag_call is None:
            return slice_section_or_empty(section_range)
        res = result_after(events, ag_call["_idx"], "pull_account_aggregator")
        anchor = res["_idx"] if res else ag_call["_idx"]
        return messages_after_idx(events, anchor)
    lo = asset_calls[0]["_idx"]
    last = asset_calls[-1]["_idx"]
    res = result_after(events, last, "add_manual_asset")
    hi = res["_idx"] if res else last
    # Extend backward to include the preceding assistant prompt.
    pre_lo, _ = messages_before_idx(events, lo)
    lo = min(lo, pre_lo) if pre_lo <= lo else lo
    return (lo, hi)


# ---- goals_planning ----

def slice_goals_introduction(events, _):
    call = find_first_tool_call(events, "add_goal")
    if call is None:
        return (0, -1)
    return messages_before_idx(events, call["_idx"])


def slice_goals_tools(events, section_range):
    calls = [e["_idx"] for e in events
             if e["type"] in ("tool_call", "tool_result")
             and e.get("name") in SECTION_TOOLS["goals_planning"]]
    if not calls:
        return slice_section_or_empty(section_range)
    return (min(calls), max(calls))


def slice_goals_updation(events, section_range):
    """Reprioritize call(s) + surrounding context."""
    repri = find_all_tool_calls(events, "reprioritize")
    if not repri:
        return slice_goals_tools(events, section_range)
    lo = repri[0]["_idx"]
    last = repri[-1]["_idx"]
    res = result_after(events, last, "reprioritize")
    hi = res["_idx"] if res else last
    pre_lo, _ = messages_before_idx(events, lo)
    return (min(lo, pre_lo) if pre_lo <= lo else lo, hi)


def slice_goals_explanation(events, section_range):
    """Whole goals section's narration — the judge needs context per-goal."""
    return slice_section_or_empty(section_range)


# ---- final_plan ----

def slice_final_pdf_tool(events, _):
    calls = [e["_idx"] for e in events
             if e["type"] in ("tool_call", "tool_result")
             and e.get("name") in ("build_goal_portfolio", "generate_plan_pdf")]
    if not calls:
        return (0, -1)
    return (min(calls), max(calls))


def slice_final_explanation_portfolio(events, section_range):
    """Narration describing the portfolio.

    Spans from after the last build_goal_portfolio result through the first
    contiguous assistant turns following generate_plan_pdf — i.e. both the
    pre-PDF portfolio description and the post-PDF action-items recap.
    Ends at the first user message that arrives after the PDF result (which
    is typically a question, owned by 'Answering Questions').
    """
    bgp_results = find_all_tool_results(events, "build_goal_portfolio")
    if not bgp_results:
        return slice_section_or_empty(section_range)
    start = bgp_results[-1]["_idx"] + 1
    pdf_results = find_all_tool_results(events, "generate_plan_pdf")
    pdf_end = pdf_results[-1]["_idx"] if pdf_results else start - 1
    end = max(start - 1, pdf_end)
    i = end + 1
    while i < len(events):
        e = events[i]
        if e["type"] == "message" and e.get("role") == "user":
            break
        end = i
        i += 1
    return (start, end)


def slice_final_answering_questions(events, section_range):
    """Final section + closing tail combined — user questions usually trail."""
    pdf_results = find_all_tool_results(events, "generate_plan_pdf")
    if not pdf_results:
        return slice_section_or_empty(section_range)
    return (pdf_results[-1]["_idx"] + 1, len(events) - 1)


# =============================================================================
# Deterministic check functions  (Tool call sub-modules)
# =============================================================================

def check_risk_accurate_tool_call(events: list[dict]) -> tuple[str, str]:
    call = find_first_tool_call(events, "assess_risk_profile")
    if call is None:
        return "No", "assess_risk_profile was never called"
    args = call.get("arguments", {}) or {}
    answers = args.get("answers")
    if not isinstance(answers, list) or not answers:
        return "No", f"answers arg missing or empty: {answers!r}"
    if not all(isinstance(a, str) and a.strip() for a in answers):
        return "No", f"answers contains non-string/empty entries: {answers!r}"
    res = result_after(events, call["_idx"], "assess_risk_profile")
    if res is None:
        return "No", "no matching tool_result followed the tool_call"
    r = res.get("result", {}) or {}
    rp, eb, er = r.get("risk_profile"), r.get("equity_band"), r.get("expected_return")
    problems = []
    if not (isinstance(rp, str) and rp):
        problems.append(f"risk_profile invalid: {rp!r}")
    if not (isinstance(eb, (int, float)) and 0 < eb <= 1):
        problems.append(f"equity_band out of (0,1]: {eb!r}")
    if not (isinstance(er, (int, float)) and 0 < er <= 0.30):
        problems.append(f"expected_return out of (0,0.30]: {er!r}")
    if problems:
        return "No", "; ".join(problems)
    return "Yes", (f"answers={answers}; risk_profile={rp!r}, "
                   f"equity_band={eb}, expected_return={er}")


def check_family_accurate_tool_call(events: list[dict]) -> tuple[str, str]:
    call = find_first_tool_call(events, "add_family")
    if call is None:
        return "No", "add_family was never called"
    args = call.get("arguments", {}) or {}
    problems = []
    spouse_age = args.get("spouse_age")
    if spouse_age not in (None, 0, "") and not (
            isinstance(spouse_age, (int, float)) and 18 <= spouse_age <= 100):
        problems.append(f"spouse_age out of 18..100: {spouse_age!r}")
    children = args.get("children") or []
    for c in children:
        age = c.get("age") if isinstance(c, dict) else c
        if not (isinstance(age, (int, float)) and 0 <= age <= 30):
            problems.append(f"child age out of 0..30: {age!r}")
    deps = args.get("dependents_count")
    if deps is not None and not (isinstance(deps, int) and deps >= 0):
        problems.append(f"dependents_count not int>=0: {deps!r}")
    if problems:
        return "No", "; ".join(problems)
    return "Yes", (f"spouse_age={spouse_age}, children={children}, "
                   f"dependents_count={deps}")


def check_portfolio_tool_call(events: list[dict]) -> tuple[str, str]:
    call = find_first_tool_call(events, "pull_mf_central")
    if call is None:
        return "No", "pull_mf_central was never called"
    args = call.get("arguments", {}) or {}
    if args.get("user_confirmed_consent") is not True:
        return "No", (f"pull_mf_central called without "
                      f"user_confirmed_consent=true (was {args.get('user_confirmed_consent')!r})")
    res = result_after(events, call["_idx"], "pull_mf_central")
    if res is None:
        return "No", "no matching tool_result followed pull_mf_central"
    r = res.get("result", {}) or {}
    required = ["holdings", "total_value", "total_monthly_sip",
                "equity_value", "debt_value"]
    missing = [k for k in required if k not in r]
    if missing:
        return "No", f"pull_mf_central result missing fields: {missing}"
    return "Yes", (f"pull_mf_central ok; total_value={r.get('total_value')}, "
                   f"equity={r.get('equity_value')}, debt={r.get('debt_value')}, "
                   f"monthly_sip={r.get('total_monthly_sip')}")


def check_investments_pulling(events: list[dict]) -> tuple[str, str]:
    pull_calls = find_all_tool_calls(events, "pull_account_aggregator")
    if not pull_calls:
        return "No", "pull_account_aggregator was never called"
    for c in pull_calls:
        if c.get("arguments", {}).get("user_confirmed_consent") is not True:
            return "No", (f"pull_account_aggregator at event {c['_idx']} "
                          f"missing user_confirmed_consent=true")
    confirms = find_all_tool_results(events, "confirm_financial_snapshot")
    succeeded = any(c.get("result", {}).get("financial_snapshot_confirmed") is True
                    for c in confirms)
    if not succeeded:
        return "No", "no confirm_financial_snapshot returned financial_snapshot_confirmed=true"
    return "Yes", (f"{len(pull_calls)} AA pull(s) with consent; "
                   f"financial_snapshot_confirmed=True")


def check_goals_tool_calls(events: list[dict]) -> tuple[str, str]:
    goals = find_all_tool_results(events, "add_goal")
    if not goals:
        return "No", "no add_goal calls"
    problems = []
    for g in goals:
        target = g.get("result", {}).get("inflated_target")
        if not (isinstance(target, (int, float)) and target > 0):
            problems.append(f"event {g['_idx']}: inflated_target={target!r}")
    proj = find_all_tool_calls(events, "project_existing_corpus")
    gap = find_all_tool_calls(events, "compute_gap_and_sip")
    if not proj:
        problems.append("no project_existing_corpus calls")
    if not gap:
        problems.append("no compute_gap_and_sip calls")
    if problems:
        return "No", "; ".join(problems)
    return "Yes", (f"{len(goals)} goal(s) with positive inflated_target; "
                   f"{len(proj)} project_existing_corpus, "
                   f"{len(gap)} compute_gap_and_sip calls")


def check_goals_updation(events: list[dict]) -> tuple[str, str]:
    gap_results = find_all_tool_results(events, "compute_gap_and_sip")
    unaffordable = [r for r in gap_results
                    if r.get("result", {}).get("affordability") == "unaffordable"]
    repri = find_all_tool_calls(events, "reprioritize")
    if not unaffordable:
        if repri:
            return "Yes", (f"no unaffordable gaps; {len(repri)} reprioritize "
                           f"call(s) (acceptable)")
        return "Yes", "no unaffordable gaps; no reprioritize needed"
    last_un = unaffordable[-1]["_idx"]
    after = [c for c in repri if c["_idx"] > last_un]
    if not after:
        return "No", (f"compute_gap_and_sip flagged unaffordable at "
                      f"event {last_un} but no reprioritize followed")
    return "Yes", (f"unaffordable at event {last_un} resolved by reprioritize "
                   f"at event {after[0]['_idx']}")


def check_final_pdf_tool_call(events: list[dict]) -> tuple[str, str]:
    bgp = find_all_tool_results(events, "build_goal_portfolio")
    if not bgp:
        return "No", "no build_goal_portfolio calls"
    pdf = find_all_tool_results(events, "generate_plan_pdf")
    if not pdf:
        return "No", "generate_plan_pdf was never called"
    last = pdf[-1]
    r = last.get("result", {}) or {}
    artifact = r.get("pdf_file") or r.get("url")
    if not artifact:
        return "No", "generate_plan_pdf result has empty pdf_file/url"
    last_tool_idx = max(e["_idx"] for e in events
                        if e["type"] in ("tool_call", "tool_result"))
    if last["_idx"] != last_tool_idx:
        return "No", (f"generate_plan_pdf is not the last tool event "
                      f"(last_tool_idx={last_tool_idx}, pdf_idx={last['_idx']})")
    return "Yes", (f"{len(bgp)} build_goal_portfolio call(s); "
                   f"pdf artifact={artifact}")


# =============================================================================
# Rubric registry
# =============================================================================

RUBRICS: "OrderedDict[str, list[dict]]" = OrderedDict([
    ("risk_profile", [
        {"name": "Identifying Answer", "type": "LLM as a judge",
         "slice_fn": slice_risk_identifying,
         "judge_prompt": "risk_identifying_answer"},
        {"name": "Accurate Tool Call (Risk Profile)", "type": "Tool call",
         "slice_fn": slice_risk_tool,
         "check_fn": check_risk_accurate_tool_call},
        {"name": "Explanation of Risk Profile + Broader Implication",
         "type": "LLM as a judge",
         "slice_fn": slice_risk_explanation,
         "judge_prompt": "risk_explanation_implication"},
        {"name": "Compliance", "type": "LLM as a judge",
         "slice_fn": slice_risk_compliance,
         "judge_prompt": "risk_compliance"},
    ]),
    ("family", [
        {"name": "Identifying Family Composition", "type": "LLM as a judge",
         "slice_fn": slice_family_identifying,
         "judge_prompt": "family_identifying_composition"},
        {"name": "Accurate Tool Call (Family)", "type": "Tool call",
         "slice_fn": slice_family_tool,
         "check_fn": check_family_accurate_tool_call},
        {"name": "Acknowledgement & Plan Impact", "type": "LLM as a judge",
         "slice_fn": slice_family_acknowledgement,
         "judge_prompt": "family_acknowledgement_implication"},
    ]),
    ("mf_central", [
        {"name": "Explanation", "type": "LLM as a judge",
         "slice_fn": slice_mfc_explanation,
         "judge_prompt": "mfc_explanation"},
        {"name": "Rebuttal (if asked)", "type": "LLM as a judge",
         "slice_fn": slice_mfc_rebuttal,
         "judge_prompt": "mfc_rebuttal"},
        {"name": "Consent", "type": "LLM as a judge",
         "slice_fn": slice_mfc_consent,
         "judge_prompt": "mfc_consent"},
    ]),
    ("portfolio_review", [
        {"name": "Overview of MF", "type": "LLM as a judge",
         "slice_fn": slice_portfolio_narration,
         "judge_prompt": "portfolio_overview_mf"},
        {"name": "Explaining + Next Steps", "type": "LLM as a judge",
         "slice_fn": slice_portfolio_narration,
         "judge_prompt": "portfolio_explaining_next_steps"},
        {"name": "Tool Call", "type": "Tool call",
         "slice_fn": slice_portfolio_tool,
         "check_fn": check_portfolio_tool_call},
    ]),
    ("aa", [
        {"name": "Consent", "type": "LLM as a judge",
         "slice_fn": slice_aa_consent,
         "judge_prompt": "aa_consent"},
        {"name": "Rebuttal", "type": "LLM as a judge",
         "slice_fn": slice_aa_rebuttal,
         "judge_prompt": "aa_rebuttal"},
        {"name": "Explanation", "type": "LLM as a judge",
         "slice_fn": slice_aa_explanation,
         "judge_prompt": "aa_explanation"},
    ]),
    ("investments", [
        {"name": "Pulling All Investments (Tool Call)", "type": "Tool call",
         "slice_fn": slice_investments_pulls,
         "check_fn": check_investments_pulling},
        {"name": "Updation / Addition (Optional)", "type": "LLM as a judge",
         "slice_fn": slice_investments_updation,
         "judge_prompt": "investments_updation_addition"},
    ]),
    ("goals_planning", [
        {"name": "Introduction", "type": "LLM as a judge",
         "slice_fn": slice_goals_introduction,
         "judge_prompt": "goals_introduction"},
        {"name": "Tool Calls", "type": "Tool call",
         "slice_fn": slice_goals_tools,
         "check_fn": check_goals_tool_calls},
        {"name": "Updation or Not", "type": "Tool call",
         "slice_fn": slice_goals_updation,
         "check_fn": check_goals_updation},
        {"name": "Explanation of Goal + Calc", "type": "LLM as a judge",
         "slice_fn": slice_goals_explanation,
         "judge_prompt": "goals_explanation_calc"},
    ]),
    ("final_plan", [
        {"name": "Final PDF Created with Right Values (Tool Call)",
         "type": "Tool call",
         "slice_fn": slice_final_pdf_tool,
         "check_fn": check_final_pdf_tool_call},
        {"name": "Explanation of Portfolio", "type": "LLM as a judge",
         "slice_fn": slice_final_explanation_portfolio,
         "judge_prompt": "final_plan_explanation_portfolio"},
        {"name": "Answering Questions", "type": "LLM as a judge",
         "slice_fn": slice_final_answering_questions,
         "judge_prompt": "final_plan_answering_questions"},
    ]),
])


# Map each rubric section to the tool-section whose range to use as a hint
# for slice functions that take section_range. Some rubric sections piggyback
# on the same tool-section (e.g. portfolio_review on mf_central).
RUBRIC_TO_TOOL_SECTION = {
    "risk_profile": "risk_profile",
    "family": "family",
    "mf_central": "mf_central",
    "portfolio_review": "mf_central",
    "aa": "account_aggregator",
    "investments": "account_aggregator",
    "goals_planning": "goals_planning",
    "final_plan": "final_plan",
}


# =============================================================================
# Per-section row generation
# =============================================================================

def rows_for_section(section: str, events: list[dict],
                     tool_section_ranges: dict[str, tuple[int, int]]
                     ) -> list[dict]:
    rubric = RUBRICS.get(section, [])
    tool_section = RUBRIC_TO_TOOL_SECTION.get(section)
    section_range = tool_section_ranges.get(tool_section) if tool_section else None

    out: list[dict] = []
    for sm in rubric:
        lo, hi = sm["slice_fn"](events, section_range)
        excerpt = format_excerpt(events, lo, hi)
        if sm["type"] == "Tool call":
            verdict, explanation = sm["check_fn"](events)
        else:
            verdict, explanation = "", ""
        out.append({
            "sub_module": sm["name"],
            "type": sm["type"],
            "verdict": verdict,
            "explanation": explanation,
            "human_verdict": "", "human_notes": "", "agreement": "",
            "event_range": range_str(lo, hi),
            "transcript_excerpt": excerpt,
        })
    return out


# =============================================================================
# Workbook writer
# =============================================================================

def _autosize(ws, wide_cols: set[str] | None = None):
    wide_cols = wide_cols or set()
    for col_idx, col_cells in enumerate(ws.columns, start=1):
        header = ws.cell(row=1, column=col_idx).value
        if header in wide_cols:
            ws.column_dimensions[get_column_letter(col_idx)].width = 80
            continue
        max_len = 0
        for c in col_cells:
            v = c.value
            if v is None:
                continue
            first_line_len = len(str(v).split("\n", 1)[0])
            if first_line_len > max_len:
                max_len = first_line_len
        ws.column_dimensions[get_column_letter(col_idx)].width = min(
            max(12, max_len + 2), 60
        )


def write_workbook(out_path: Path, transcript_name: str,
                   section_rows: "OrderedDict[str, list[dict]]") -> None:
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    summary = wb.create_sheet("Summary")
    summary.append(["transcript", transcript_name])
    summary.append([])
    summary.append(["section", "sub_modules", "auto_yes", "auto_no",
                    "judge_pending", "human_pending"])

    totals = {"sub_modules": 0, "auto_yes": 0, "auto_no": 0,
              "judge_pending": 0, "human_pending": 0}

    for section in RUBRIC_SECTIONS:
        if section not in section_rows:
            continue
        rows = section_rows[section]
        ws = wb.create_sheet(section)
        ws.append(COLS)
        for c in ws[1]:
            c.font = Font(bold=True)

        verdict_idx = COLS.index("verdict") + 1
        human_idx = COLS.index("human_verdict") + 1
        agreement_idx = COLS.index("agreement") + 1
        v_letter = get_column_letter(verdict_idx)
        h_letter = get_column_letter(human_idx)
        excerpt_idx = COLS.index("transcript_excerpt") + 1
        explanation_idx = COLS.index("explanation") + 1

        for r in rows:
            ws.append([r.get(col, "") for col in COLS])
            row_num = ws.max_row
            verdict = r.get("verdict", "")
            if verdict in STATUS_FILLS and verdict:
                ws.cell(row=row_num, column=verdict_idx).fill = PatternFill(
                    "solid", fgColor=STATUS_FILLS[verdict])
            ws.cell(row=row_num, column=agreement_idx).value = (
                f'=IF(AND({v_letter}{row_num}<>"",{h_letter}{row_num}<>""),'
                f'IF({v_letter}{row_num}={h_letter}{row_num},"match","mismatch"),'
                f'"(pending)")'
            )
            ws.cell(row=row_num, column=excerpt_idx).alignment = Alignment(
                wrap_text=True, vertical="top")
            ws.cell(row=row_num, column=explanation_idx).alignment = Alignment(
                wrap_text=True, vertical="top")

        ws.freeze_panes = "A2"
        _autosize(ws, wide_cols={"transcript_excerpt", "explanation"})

        sub_modules = len(rows)
        auto_yes = sum(1 for r in rows if r["verdict"] == "Yes")
        auto_no = sum(1 for r in rows if r["verdict"] == "No")
        judge_pending = sum(1 for r in rows
                            if r["type"] == "LLM as a judge" and not r["verdict"])
        human_pending = sum(1 for r in rows if not r["human_verdict"])
        summary.append([section, sub_modules, auto_yes, auto_no,
                        judge_pending, human_pending])
        for k, v in (("sub_modules", sub_modules), ("auto_yes", auto_yes),
                     ("auto_no", auto_no), ("judge_pending", judge_pending),
                     ("human_pending", human_pending)):
            totals[k] += v

    summary.append([])
    summary.append(["TOTAL", totals["sub_modules"], totals["auto_yes"],
                    totals["auto_no"], totals["judge_pending"],
                    totals["human_pending"]])
    _autosize(summary)
    wb.save(out_path)


def write_csv_fallback(out_dir: Path,
                       section_rows: "OrderedDict[str, list[dict]]") -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for section, rows in section_rows.items():
        with (out_dir / f"{section}.csv").open(
                "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(COLS)
            for r in rows:
                w.writerow([r.get(col, "") for col in COLS])


# =============================================================================
# Driver
# =============================================================================

def evaluate_transcript(path: Path):
    """Returns (events, section_rows). Events kept so the caller can run
    the judge with proper grounding."""
    events = load_transcript(path)
    tool_ranges = detect_sections(events)
    out: "OrderedDict[str, list[dict]]" = OrderedDict()
    for section in RUBRIC_SECTIONS:
        out[section] = rows_for_section(section, events, tool_ranges)
    return events, out


def populate_judge_verdicts(events: list[dict],
                            section_rows: "OrderedDict[str, list[dict]]",
                            verbose: bool = True) -> None:
    """Mutates section_rows in place: fills verdict/explanation for every
    'LLM as a judge' sub-module by calling run_judge()."""
    for section, rows in section_rows.items():
        sm_lookup = {sm["name"]: sm for sm in RUBRICS.get(section, [])}
        for row in rows:
            if row["type"] != "LLM as a judge" or row["verdict"]:
                continue
            sm = sm_lookup.get(row["sub_module"])
            if sm is None or "judge_prompt" not in sm:
                continue
            prompt_key = sm["judge_prompt"]
            tool_args, tool_result = grounding_for(prompt_key, events)
            t0 = time.time()
            result = run_judge(
                prompt_key, row["transcript_excerpt"], tool_args, tool_result,
            )
            row["verdict"] = result["verdict"]
            row["explanation"] = result["explanation"]
            if verbose:
                dt = time.time() - t0
                v = result["verdict"] or "ERROR"
                print(f"  judge {section}/{row['sub_module']}: {v} ({dt:.1f}s)")


def summarize(section_rows: "OrderedDict[str, list[dict]]",
              transcript_name: str) -> dict:
    sub_modules = auto_yes = auto_no = judge_pending = human_pending = 0
    for rows in section_rows.values():
        for r in rows:
            sub_modules += 1
            if r["verdict"] == "Yes":
                auto_yes += 1
            elif r["verdict"] == "No":
                auto_no += 1
            if r["type"] == "LLM as a judge" and not r["verdict"]:
                judge_pending += 1
            if not r["human_verdict"]:
                human_pending += 1
    return {
        "transcript": transcript_name,
        "sub_modules": sub_modules,
        "auto_yes": auto_yes, "auto_no": auto_no,
        "judge_pending": judge_pending,
        "human_pending": human_pending,
    }


def main():
    ap = argparse.ArgumentParser(
        description="Maya / Wealth Expert rubric-driven transcript evaluator."
    )
    ap.add_argument("--input-dir", default="./transcripts")
    ap.add_argument("--output-dir", default="./eval_output")
    ap.add_argument("--judge", action="store_true",
                    help="(NOT IMPLEMENTED) Run the LLM judge; stub raises.")
    args = ap.parse_args()

    in_dir = Path(args.input_dir).resolve()
    out_dir = Path(args.output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    if not in_dir.exists():
        print(f"input dir does not exist: {in_dir}", file=sys.stderr)
        sys.exit(2)
    paths = sorted(in_dir.glob("*.json"))
    if not paths:
        print(f"no *.json transcripts in {in_dir}", file=sys.stderr)
        sys.exit(2)

    if not HAS_OPENPYXL:
        print("NOTICE: openpyxl is not installed; falling back to per-section "
              "CSVs in eval_output/<transcript_stem>/", file=sys.stderr)

    if args.judge:
        if not HAS_OPENAI:
            print("--judge requires the openai SDK. Run: pip install openai",
                  file=sys.stderr)
            sys.exit(2)
        if not os.environ.get("OPENAI_API_KEY"):
            print("--judge requires OPENAI_API_KEY in the environment.",
                  file=sys.stderr)
            sys.exit(2)
        print(f"judge enabled; model={OPENAI_MODEL}")

    summary_rows = []
    for p in paths:
        try:
            events, section_rows = evaluate_transcript(p)
        except Exception as e:
            print(f"ERROR evaluating {p.name}: {e}", file=sys.stderr)
            continue
        if args.judge:
            print(f"running judge for {p.name}...")
            populate_judge_verdicts(events, section_rows)
        if HAS_OPENPYXL:
            xlsx_path = out_dir / f"{p.stem}_eval.xlsx"
            write_workbook(xlsx_path, p.name, section_rows)
            print(f"wrote {xlsx_path}")
        else:
            sub = out_dir / p.stem
            write_csv_fallback(sub, section_rows)
            print(f"wrote CSV fallback under {sub}")
        summary_rows.append(summarize(section_rows, p.name))

    summary_csv = out_dir / "summary.csv"
    fields = ["transcript", "sub_modules", "auto_yes", "auto_no",
              "judge_pending", "human_pending"]
    with summary_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in summary_rows:
            w.writerow(row)
    print(f"wrote {summary_csv}")


if __name__ == "__main__":
    main()
