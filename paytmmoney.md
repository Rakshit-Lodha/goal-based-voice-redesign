# Paytm Money · Maya — Affluent UI Redesign

Interview-ready redesign of the Maya voice agent for Paytm Money's Affluent++ DIY segment. Conversation-first (RM, not IVR): the orb is the experience, artifacts are summoned moments.

**Branch:** `redesign/affluent-ui` off `63b8efd Voice Bot V2`
**Target user:** Affluent++, DIY product + DIY KYC, knows what they want
**Stack (unchanged):** React 19 + Vite + FastAPI + Pipecat, mobile-first

---

## Locked decisions

| Decision | Choice |
|---|---|
| Branch base | `63b8efd Voice Bot V2` (clean baseline) |
| Form factor | Mobile-first, centred phone viewport on desktop |
| Visual register | Hybrid — deep navy chrome + warm cream content cards + champagne accent + serif display (Fraunces) |
| Interaction model | Conversation-first; orb always centred; cards summoned, not persistent |
| Stage rail | Removed — replaced by ledger chip top-right |
| Artifact dismissal | Auto-dismiss on next tool call (deterministic, no LLM coupling) |
| Pause mid-sentence | Tap orb to pause Maya's TTS; tap again to resume |
| Artifact source of truth | Backend `core/ui_bus.py` emits `{type:'artifact', kind, data}` events; specific tools call it at confirmed-state moments |
| Demo mode | None — real voice only |
| Dependencies | Zero new runtime deps. CSS-only motion, hand-rolled SVG charts |
| PDF restyling | Out of scope for this branch |

---

## References

### Mockups (build these into React, in this order of fidelity)
- `Design/mockups/conversation.html` — **the source of truth.** Conversation-first model with orb, summoned artifacts, hero takeover, ledger panel
- `Design/mockups/transitions.html` — orb travel + revision peek mechanics
- `Design/mockups/index.html` — earlier 12-screen board (kept for reference; superseded by conversation.html)

### Visual references
- `Design/refs/Wireframe/` — 12 hand-drawn wireframes (the original locked 9-stage flow)
- `Design/refs/Screenshots/` — real Paytm Money home, MF Central consent, Finvu AA OTP screens

### Existing code (keep, do not rewrite)
- `core/finmath.py` — all math, unit-tested
- `core/session.py` — STATE + progress + next_step gating
- `core/ui_bus.py` — RTVI event bus (extend with `emit_artifact`)
- `agent/tools.py` — 12 registered tools (add `emit_artifact` calls in 4 of them)
- `agent/prompts.py` — Maya's system prompt
- `bot.py`, `server.py` — Pipecat + FastAPI plumbing
- `web/src/pcClient.ts`, `pcReact.ts`, `types.ts`, `demoSnapshot.ts`, `format.ts` — Pipecat React plumbing

### Tests (must stay green)
- `tests/test_finmath.py`, `test_session_flow.py`, `test_tool_guards.py`, `test_tool_call_sequence.py`, `test_account_aggregator_flow.py`, `test_portfolio_plan_contract.py`, `test_gold_plan_eval.py`

---

## Architecture invariants

1. **LLM never computes numbers.** All maths through `core/finmath.py`.
2. **LLM never knows about UI.** Artifact events emit from tools (post-mutation), not from prompts.
3. **STATE is single source of truth.** Ledger panel reads `STATE` snapshot directly. No client-side state duplication.
4. **Tool call order is contract.** `test_tool_call_sequence.py` defines the 12-tool gold path; artifact ordering follows it.
5. **Auto-dismiss is deterministic.** Next tool call dismisses prior artifact — no timers, no LLM tags.

---

## Build phases — checklist

Mark each item `[x]` as completed. Commit at the end of each phase with message `phase-N: <summary>`.

### Phase 0 — Branch + housekeeping
- [x] Verify working tree is clean on `main` at `63b8efd`
- [x] Cut branch: `git checkout -b redesign/affluent-ui`
- [x] Fix stale `:7860` reference in `bot.py:4`
- [x] Commit: `phase-0: branch baseline + comment fix` (`b945cda`)

### Phase 1 — Design tokens + phone shell
- [x] Create `web/src/theme/tokens.ts` (colors, type scale, motion durations, easings)
- [x] ~~Create `web/src/theme/fonts.css` (`@font-face` for Fraunces + Inter)~~ — superseded by Google Fonts `<link>` in `index.html` (matches Conventions section)
- [x] Rewrite `web/src/index.css` (reset, CSS vars from tokens, body bg `#161E2E`)
- [x] Create `web/src/components/PhoneFrame.tsx` (390×844 centred viewport, full-bleed on real mobile, navy interior with subtle radial gradient)
- [x] Rewrite `web/src/App.tsx` to mount `PhoneFrame` with placeholder content
- [x] Verify at `localhost:5174`: dark page, phone frame visible, brand mark rendered
- [x] Pin worktree to `:5174` + proxy `:8001` in `web/vite.config.ts` (isolation from main demo)
- [x] Commit: `phase-1: theme tokens + phone shell`

### Phase 2 — Singleton orb
- [x] Create `web/src/components/Orb.tsx` accepting `mood: 'idle' | 'listening' | 'talking' | 'paused'`
- [x] CSS: idle (steel-blue radial), listening (cool blue, fast pulse), talking (champagne, slow pulse), paused (dim, no animation)
- [x] Mount Orb at app root, centred (translate(-50%, -50%))
- [x] Wire to existing Pipecat events via `useMood` hook: `botStartedSpeaking` → talking; `botStoppedSpeaking` → idle; `userStartedSpeaking` → listening; `userStoppedSpeaking` → idle
- [x] Verify: orb breathes; mood swaps when Maya speaks
- [x] Commit: `phase-2: singleton orb wired to pipecat events`

### Phase 3 — Conversation shell (subtitle + mic + pause + brand bar + ledger chip)
- [x] Create `web/src/components/Subtitle.tsx` (single italic Fraunces line under orb, who/what split)
- [x] Create `web/src/components/MicAffordance.tsx` (subtle bottom-centre tap-to-speak; `Tap or just talk` label)
- [x] Wire orb tap → pause/resume Maya TTS via `usePause` (mutes bot `MediaStreamTrack.enabled`)
- [x] Create `web/src/components/BrandBar.tsx` (Paytm Money mark left + ledger chip placeholder right)
- [x] Verify: full empty conversation experience — talk to Maya, see her speak, tap orb to pause, no artifacts yet
- [x] Commit: `phase-3: conversation shell with pause + mic`

### Phase 4 — Backend artifact events
- [x] Extend `core/ui_bus.py` with `emit_artifact(kind: str, data: dict)` helper
- [x] Add `ArtifactKind` enum / Literal type: `risk_reveal`, `family_recap`, `mfc_consent`, `aa_consent`, `income_snapshot`, `ratios`, `inflation_curve`, `sip_split`, `funds_picker`, `plan_hero`
- [x] Wire emits in `agent/tools.py`:
  - [x] `assess_risk_profile` → `risk_reveal`
  - [x] `add_family` → `family_recap`
  - [x] `pull_mf_central` → triggers `mfc_consent` *before* (separate path)
  - [x] `pull_account_aggregator` → triggers `aa_consent` before, `income_snapshot` + `ratios` after
  - [x] `compute_gap_and_sip` → `inflation_curve` (per-goal)
  - [x] `build_goal_portfolio` → `sip_split`
  - [x] `generate_plan_pdf` → `plan_hero`
- [x] Fake-RTVI smoke check: artifact events stream in deterministic order during a tool sequence
- [x] All existing tests still green (31/31)
- [ ] Verify in live browser console mid-conversation — deferred to Phase 6 live walkthrough
- [x] Commit: `phase-4: artifact events on ui_bus`

### Phase 5 — Artifact slot + summoning
- [x] Extend `web/src/types.ts` with `ArtifactEvent` union matching backend
- [x] Create `web/src/state/artifactQueue.ts` (single active artifact, queue of pending; next tool call dismisses current)
- [x] Create `web/src/components/Artifact.tsx` (cream sheet slides up from bottom, dismiss icon)
- [x] Create artifact card components: `RiskRevealCard`, `FamilyRecapCard`, `MfcConsentSheet`, `AaConsentSheet` (white, Finvu-style verbatim copy), `IncomeSnapshotCard`, `RatiosCard`, `InflationCurveCard` (SVG), `SipSplitCard`, `FundsPickerSheet`
- [x] Kind → component registry in `web/src/state/artifactRegistry.tsx`
- [x] On artifact summon: shrink orb to scale 0.55, translate up by ~160px; on dismiss: restore
- [x] Browser smoke check: redesign shell renders at `localhost:5174`; artifact listener logs `[artifact]` events to console
- [x] `npm run lint`, `npm run build`, and `pytest tests/ -v` green
- [ ] Verify full conversation summons real cards at the right moments — deferred to Phase 6 live walkthrough
- [x] Commit: `phase-5: artifact summoning + cards`

### Phase 6 — The hero takeover
- [x] Create `web/src/screens/PlanHero.tsx` (full cream takeover, corner champagne orb ring, 84px Fraunces SIP number, dismiss CTA)
- [x] Triggered by `plan_hero` artifact kind only (special-cased in `App.tsx`; bypasses `Artifact.tsx` bottom-sheet)
- [x] Orb gains `corner` mode — anchors top-right with a champagne ring, mutually exclusive with `summoned`
- [x] Dismiss returns to orb conversation; ledger now shows complete plan
- [ ] Verify live: the moment lands — orb shrinks to corner, ₹X SIP number takes the screen (next live walkthrough)
- [x] Commit: `phase-6: plan hero takeover`

### Phase 7 — Ledger chip + panel
- [x] Replace ledger chip placeholder with live `web/src/components/LedgerChip.tsx` reading STATE snapshot count (via `useStateSnapshot`)
- [x] Create `web/src/components/LedgerPanel.tsx` (slides down from top with scrim; lists every confirmed fact from STATE; each row has `Revise` button)
- [x] Map STATE fields to ledger rows in `web/src/state/ledgerRows.ts`: Risk profile · Family · Portfolio (MF Central) · Cash flow · EPF·NPS·Stocks · Manual assets · Goals (each) · SIP plan
- [ ] Verify live: ledger reflects every Maya-confirmed fact; counter updates as the session unfolds (next live walkthrough)
- [x] Commit: `phase-7: ledger chip + panel`

### Phase 8 — Revise loop
- [x] Wire `Revise <key>` row tap → send synthetic user input via Pipecat (`client.sendText("I want to update my <key>.", { run_immediately: true, audio_response: true })`)
- [x] Maya catches it conversationally and asks the right follow-up (LLM handles the natural-language re-entry)
- [x] On state mutation, if downstream computations are affected, emit `cascade_diff` server message → `CascadeToast`: bottom pill showing "Monthly SIP updated · ₹50,000 ↑ ₹52,000". Auto-dismisses after 3.5s (resolved open question #3). Fires from `compute_gap_and_sip` + `reprioritize` via `_maybe_emit_sip_cascade`; ≥₹500 change threshold dodges rounding noise.
- [ ] Verify live: revise from ledger, Maya picks up the cue in voice, cascade toast fires on the new total (next walkthrough)
- [x] Commit: `phase-8: revise loop with cascade diff toast`

### Phase 9 — Polish
- [x] Motion timing pass — audited all `transition:` and `animation:` declarations; they all go through `--dur-fast` 200ms (micro hovers/focus), `--dur-med` 600ms (sheets/cards), `--dur-slow` 900ms (hero rise). All ease-out `cubic-bezier(0.22, 1, 0.36, 1)` — no bounce at the tail.
- [x] Edge: rapid tool call sequence — artifactQueue's state-event handler now only auto-dismisses the active artifact when the queue has something to promote (`queueRef.current.length > 0`); otherwise it re-anchors to the new tick and lingers. Tools that fire no artifact of their own (e.g. `add_manual_asset` during an investments review) no longer blank the screen.
- [x] Edge: user pauses Maya mid-artifact-summon — `usePause` mutes the bot audio track only; the artifact stays put, the orb tints amber, and the Subtitle reads "Paused · tap orb to resume". Verified by code path; no state mutation on pause.
- [ ] Edge: connection drop / reconnect — Pipecat transport handles reconnect; we don't currently clear the artifact queue on disconnect. Acceptable for the demo (the call is typically only ended after PlanHero); flag if it causes a visible glitch.
- [ ] Visual QA on real mobile (Safari iOS, Chrome Android) — needs the user's device
- [ ] Lighthouse pass — needs the user's browser
- [x] Commit: `phase-9: polish + edge cases`

---

## Conventions

- **Commit per phase.** One commit message per phase, prefixed `phase-N:`.
- **Untouched files.** Do not edit `core/finmath.py` or any test file. If a change feels needed, stop and ask.
  - `agent/prompts.py` and `core/session.py` were given small AA-OTP reinforcements in Phase 4 (Maya must call `pull_account_aggregator` in the same turn she promises the Finvu OTP). Content-only guidance edits — structure unchanged. Future edits to these still warrant a flag.
- **No new dependencies.** Motion is CSS / Web Animations API. Charts are hand-rolled SVG. Fonts come from Google Fonts via `<link>`.
- **Mobile-first widths.** Build at 390px, validate the desktop centring works at 1440px.
- **Demoable after every phase.** Open `localhost:5174`, talk to Maya, confirm the demoable state listed in the phase. If you cannot demonstrate it, the phase isn't done.

## Local run

This branch lives in a parallel **git worktree** so the main demo on `:5173` stays untouched:

```bash
# Main repo (demo, untouched)
~/Desktop/goal-based-voice                  # main @ 63b8efd
  python server.py                          # backend :8000
  cd web && npm run dev                     # frontend :5173

# Redesign worktree (this branch)
~/Desktop/goal-based-voice-redesign         # redesign/affluent-ui
  PORT=8001 python server.py                # backend :8001
  cd web && npm run dev                     # frontend :5174 (strictPort)
```

Open `http://localhost:5174` for the redesign.

---

## Still-open questions (resolve as you build)

1. ~~**Phone frame chrome on desktop**~~ — **resolved Phase 1:** clean rounded rectangle. Full device mockup competes with the orb visually and reads kitsch at the affluent register.
2. **Goal tile icons** — line illustrations (champagne stroke on cream) confirmed; revisit if they read too restrained at real size.
3. ~~**Cascade diff toast persistence**~~ — **resolved Phase 8:** 3.5s auto-dismiss. The toast is informative, not actionable — a sticky pill would compete with the orb mid-conversation. ≥₹500 change threshold filters rounding noise.
4. ~~**Ledger panel gesture**~~ — **resolved Phase 7:** tap chip only. Voice-first means hands are free for taps; a swipe-down anywhere would conflict visually with orb tap-to-pause and create accidental panel reveals mid-conversation.

---

## Definition of done for this branch

- All Phase 0–9 checkboxes ticked.
- Full Maya session from splash → plan_hero works in browser with real voice.
- All Python tests green.
- Conversation feels like an RM, not a wizard, when judged against `Design/mockups/conversation.html`.
