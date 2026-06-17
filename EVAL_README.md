# Maya Transcript Evaluation Framework

Rubric-driven evaluator for Maya / Wealth Expert voice-agent transcripts.
Each conversation section has a named rubric of sub-modules, each either a
deterministic **Tool call** check (runs now, auto-fills Yes/No) or an
**LLM as a judge** check (defined, stubbed, NOT executed — you wire it).

## Run

```bash
python eval_framework.py --input-dir output/transcripts --output-dir eval_output
```

Outputs:

- `eval_output/<transcript_stem>_eval.xlsx` — one workbook per transcript, one
  sheet per rubric section plus a `Summary` sheet.
- `eval_output/summary.csv` — aggregate row per transcript.
- CSV fallback under `eval_output/<transcript_stem>/` if `openpyxl` is missing.

Pure stdlib + `openpyxl`. No network calls in the runnable path.

## Section sheets

Each sheet has the same 9 columns:

| Column | Meaning |
|---|---|
| `sub_module` | rubric item name (e.g. "Identifying Answer") |
| `type` | `Tool call` or `LLM as a judge` |
| `verdict` | `Yes` / `No` — auto for Tool call, blank for judge until wired |
| `explanation` | auto detail for Tool call; blank for judge until wired |
| `human_verdict` | manual Yes/No |
| `human_notes` | manual freeform |
| `agreement` | Excel formula: `match` / `mismatch` / `(pending)` |
| `event_range` | event indices this sub-module's slice covers |
| `transcript_excerpt` | the actual text the grader reads — surgical per sub-module |

## Rubric registry

Order of sheets in each workbook:

1. **risk_profile** (4): Identifying Answer · Accurate Tool Call · Explanation of Risk Profile + Broader Implication · Compliance
2. **family** (3): Identifying Family Composition · Accurate Tool Call · Acknowledgement & Plan Impact
3. **mf_central** (3): Explanation · Rebuttal (if asked) · Consent
4. **portfolio_review** (3): Overview of MF · Explaining + Next Steps · Tool Call
5. **aa** (3): Consent · Rebuttal · Explanation
6. **investments** (2): Pulling All Investments (Tool Call) · Updation / Addition (Optional)
7. **goals_planning** (4): Introduction · Tool Calls · Updation or Not · Explanation of Goal + Calc
8. **final_plan** (3): Final PDF (Tool Call) · Explanation of Portfolio · Answering Questions

`mf_central` and `portfolio_review` both ride `pull_mf_central` — the first
evaluates the interaction (consent, rebuttal, explanation of what MFC is);
the second evaluates the content (how well the holdings are explained).
`aa` and `investments` split `pull_account_aggregator` the same way.

## Section auto-detection

Section boundaries are derived from the first occurrence of each tool's
canonical trigger, not from hard-coded event indices. Each sub-module's
`slice_fn` operates on the detected tool-section range and can reach beyond
it when needed (e.g. consent turns that live in the prior tool-section).

## Adding / editing rubrics

All rubric configuration lives at the top of `eval_framework.py`:

1. `SECTION_TOOLS` — tool → section mapping for auto-detection.
2. `RUBRICS` — ordered map of section name → list of sub-module dicts.
   Each sub-module dict has `name`, `type`, `slice_fn`, and either `check_fn`
   (Tool call) or `judge_prompt` (LLM as a judge).
3. `RUBRIC_TO_TOOL_SECTION` — maps rubric sections that share a tool-section
   (e.g. `portfolio_review` → `mf_central`).
4. `JUDGE_PROMPTS` — strict-JSON-demanding prompt templates per judge dimension.

To add a new section, append entries to `SECTION_TOOLS`, `RUBRICS`,
`RUBRIC_SECTIONS`, and `JUDGE_PROMPTS`. New deterministic checks go as
`check_<thing>(events) -> (verdict, explanation)` functions; new slice fns
go as `slice_<thing>(events, section_range) -> (lo, hi)`.

## Running the LLM judge

Judge calls go to OpenAI (default model `gpt-5.5`, set in `OPENAI_MODEL` env
var). Gated behind `--judge`; the deterministic path is unchanged when the
flag is absent.

```bash
export OPENAI_API_KEY=sk-...
# Optional model override:
export OPENAI_MODEL=gpt-5.5

python eval_framework.py \
    --input-dir output/transcripts \
    --output-dir eval_output \
    --judge
```

When `--judge` is on, for every `LLM as a judge` row the framework:

1. Renders the prompt from `JUDGE_PROMPTS[prompt_key]` with the row's
   `transcript_excerpt` plus the relevant tool-args / tool-result blob from
   `grounding_for(prompt_key, events)`.
2. Calls OpenAI Chat Completions with `response_format={"type": "json_object"}`.
3. Parses the strict JSON `{"verdict": "Yes" | "No", "explanation": "<=40 words"}`
   and writes both into the row.

On failure (network, invalid JSON, unexpected verdict), the row's `verdict`
stays blank and `explanation` carries the diagnostic — the eval does not crash.

**Model name caveat** — `gpt-5.5` is used verbatim. If your account exposes the
model under a different id, set `OPENAI_MODEL` to that id; no code edits needed.

Costs scale with rubric size × transcripts. Sample workload: 18 judge items ×
14 transcripts ≈ 250 calls. Each prompt is ~1–4k input tokens depending on
the slice and grounding blob.

## Editing the judge

- Prompts live in `JUDGE_PROMPTS` at the top of `eval_framework.py`. Each
  template must contain `{slice}` and may use `{tool_args}` and/or
  `{tool_result}` — extra placeholders not passed are ignored safely.
- Grounding logic — what tool args/results get passed to each prompt — is in
  `grounding_for(prompt_key, events)`. Add a branch when you add a new prompt.
- The strict JSON contract is enforced by `run_judge`: anything other than
  `{"verdict": "Yes" | "No", "explanation": str}` is treated as an error.
