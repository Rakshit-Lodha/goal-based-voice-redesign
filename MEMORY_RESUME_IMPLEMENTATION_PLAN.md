# Cross-session memory and resume plan

## Goal

Create a hackathon-ready, file-backed memory flow with two intentionally different
entry points:

- `http://localhost:5173/` always starts a fresh planning session.
- `http://localhost:5173/memory` loads the latest meaningful conversation,
  personalizes the entry card, and resumes from the saved planning state.

The implementation must preserve the existing rule that the LLM never becomes the
source of financial numbers. Exact values and planning progress come from a
serialized `SessionState`; the conversation summary is used only for presentation
and conversational continuity.

## Assumptions and scope

- The hackathon demo has one known user: `rakshit`.
- Files are sufficient for the demo; no external memory service or database is
  required.
- A fresh call is still saved and may become the memory used by `/memory`.
- The latest memory means the latest **meaningful** completed checkpoint, not
  necessarily the newest transcript file.
- A greeting-only, connection-failure, or empty call must not replace useful
  memory.
- OTPs, active consent interactions, WebRTC state, artifact queues, and LLM
  message history are call-scoped and must not be restored.
- Previously pulled financial information may be restored with its observation
  timestamp, but previous consent must never silently authorize a new pull.
- The first version supports one backend process and one active demo call. File
  locking and multi-instance deployment are out of scope.

## Success criteria

- [x] Visiting `/` renders the standard entry card and starts with a reset
      `SessionState`, even when saved conversations exist.
- [x] Completing a meaningful fresh call writes a transcript, exact state
      checkpoint, and resume summary.
- [x] Visiting `/memory` reads the latest meaningful checkpoint and renders a
      personalized card before the call starts.
- [x] Starting from `/memory` restores the exact structured state and uses a
      returning-user greeting before continuing the stage machine.
- [x] An empty or failed call does not replace the last meaningful checkpoint.
- [x] Missing, corrupt, pending, or failed summary generation never prevents a
      fresh or resumed call from starting.
- [x] Existing deterministic financial calculations and tool guards continue to
      pass their tests.
- [x] Frontend and backend automated tests cover the behaviours listed in this
      document.
- [ ] The complete two-call hackathon scenario passes the manual acceptance test.

## Tracker maintenance rules

This document is the implementation tracker.

1. An agent must change `[ ]` to `[x]` only after the implementation exists and
   the associated verification has passed.
2. If code exists but verification is failing or has not been run, leave the item
   unchecked and add a short note under **Open issues**.
3. When completing a phase, record the verification command and date in
   **Verification log**.
4. Do not mark a parent phase complete until all required child items are complete.
5. If scope changes, update the decisions and test matrix before implementing the
   changed behaviour.

## Proposed user experience

### Fresh route: `/`

The existing card remains:

> Maya is ready  
> Start your guided wealth plan  
> A private, voice-led conversation. About fifteen minutes.  
> Start planning

Starting the call sends `memory_mode=fresh`. The backend calls `session.reset()`.
The completed call is nevertheless stored as a potential future checkpoint.

### Resume route: `/memory`

The page requests `GET /api/memory/latest?user_id=rakshit`.

When memory is available, the card becomes:

> Maya remembers  
> Welcome back, Rakshit  
> Continue your home plan  
> Last time, you paused to discuss the budget with your spouse.  
> Resume planning

The exact headline and summary come from the saved resume summary. The card must
not expose detailed income, holdings, account identifiers, or other sensitive
financial values.

Starting the call sends `memory_mode=resume`. The backend restores the latest
state and instructs Maya to welcome the user back, mention the unfinished work
briefly, and ask whether they want to continue or change anything.

The card also has a secondary **Start over** action. It starts a fresh call without
deleting or overwriting history until the new call becomes meaningful.

### Resume route without usable memory

If no checkpoint exists, or the latest pointer cannot be recovered, `/memory`
shows:

> No previous plan found  
> Start your guided wealth plan

The call falls back to `memory_mode=fresh`.

### Completed-plan memory

If the latest plan is complete, use:

> Review or update your wealth plan

Maya asks what has changed. It must not immediately follow the existing
`next_step()` result that tells it to close the completed plan again.

## Storage design

### Directory layout

```text
output/
  conversations/
    rakshit/
      latest.json
      20260726T103000000000Z_<conversation-id>/
        transcript.json
        state.json
        summary.json
```

Use a timestamp with microseconds plus a generated conversation ID to avoid
same-second filename collisions.

`latest.json` is a small pointer:

```json
{
  "schema_version": 1,
  "conversation_id": "01J...",
  "checkpoint_directory": "20260726T103000000000Z_01J...",
  "saved_at": "2026-07-26T05:00:00Z"
}
```

Write JSON to a temporary file in the target directory and use `os.replace()` to
publish it atomically. Update `latest.json` only after `state.json` and the
transcript are valid.

### State checkpoint

`state.json` contains:

```json
{
  "schema_version": 1,
  "user_id": "rakshit",
  "conversation_id": "01J...",
  "saved_at": "2026-07-26T05:00:00Z",
  "financial_snapshot_observed_at": "2026-07-26T04:30:00Z",
  "state": {}
}
```

The `state` object is the exact JSON-safe representation of `SessionState`.
Restoration must explicitly rebuild nested `Goal` dataclasses and validate known
fields. Do not apply an arbitrary JSON dictionary directly to `STATE.__dict__`.

Persist:

- name and age;
- risk profile and verbatim risk answers;
- family;
- portfolio, Account Aggregator assets, and additional assets;
- confirmation status tied to the restored snapshot;
- goals, gap results, priorities, and funded/parked state;
- proposed goal portfolios;
- plan path if it still exists;
- corpus allocation and last published SIP;
- the observation timestamp for financial data.

Do not persist or restore:

- OTP request IDs or submitted OTPs;
- an active consent interaction;
- WebRTC, RTVI, UI bus, or transport state;
- active artifact queues and toast timers;
- the current LLM message array;
- transcript/cost recorder globals;
- `is_returning_session` and `resume_confirmed`, which are initialized for each
  new call.

### Meaningful-checkpoint policy

A call is meaningful when at least one of these is true:

- a successful state-changing tool result was recorded;
- the exported state differs from the state loaded at call start;
- the user provided a substantive message and the summary contains an explicit
  open item.

For the first implementation, prefer the deterministic rule: publish the
checkpoint only if a successful state-changing tool result occurred or the
exported persistent state changed. This prevents greetings, “okay”, connection
failures, and accidental taps from replacing useful memory.

## End-of-call summarization

### Decision

Use a post-call summarization step, but do not make it the memory database or the
source of financial truth.

The summarizer is valuable because it can produce:

- a natural one-sentence personalized card;
- a concise recap of the previous conversation;
- explicit decisions and corrections;
- unresolved questions;
- a recommended opening for the next call.

The saved `SessionState` remains authoritative. The summarizer may describe that
state, but it cannot create or modify goals, amounts, consent, confirmations, or
calculation results.

### Summary schema

`summary.json`:

```json
{
  "schema_version": 1,
  "status": "ready",
  "generated_at": "2026-07-26T05:00:02Z",
  "headline": "Continue your home plan",
  "card_summary": "You paused to discuss the home budget with your spouse.",
  "conversation_summary": "Rakshit reviewed...",
  "decisions": [
    "The home goal remains active."
  ],
  "open_items": [
    "Confirm the revised home budget."
  ],
  "recommended_next_start": "Welcome Rakshit back and ask whether the home budget was confirmed.",
  "completed_plan": false
}
```

Allowed `status` values:

- `pending`
- `ready`
- `fallback`
- `failed`

### Summarization sequence

1. Export and atomically save the exact state.
2. Save or copy the completed transcript into the conversation directory.
3. Decide whether the call is meaningful.
4. If meaningful, publish `latest.json`.
5. Write a deterministic fallback summary derived from structured state with
   `status=fallback`.
6. Run the LLM summarizer after disconnect with a short timeout and a strict JSON
   schema.
7. Validate its output and atomically replace the fallback summary with
   `status=ready`.
8. If summarization fails, retain the deterministic fallback. Never invalidate
   the checkpoint.

Publishing the checkpoint before LLM summarization means `/memory` works
immediately after disconnect. It may briefly show the deterministic fallback and
then show the richer summary on refresh.

### Summarizer constraints

The summarizer prompt must:

- treat tool results and the saved state as authoritative;
- distinguish user statements from tool-confirmed facts;
- identify corrections such as “one crore changed to eighty lakhs”;
- never infer a missing amount, date, family member, or consent;
- never state that previous consent can be reused;
- avoid sensitive numbers in `headline` and `card_summary`;
- return only the strict summary schema;
- keep `recommended_next_start` as an instruction, not spoken assistant prose;
- use a configured timeout and deterministic fallback.

For the hackathon, this can use the existing OpenAI credentials and model. A
separate autonomous agent framework is unnecessary; this is one bounded
structured-output LLM call.

## API contracts

### `GET /api/memory/latest`

Request:

```http
GET /api/memory/latest?user_id=rakshit
```

Memory available:

```json
{
  "available": true,
  "user_id": "rakshit",
  "user_name": "Rakshit",
  "conversation_id": "01J...",
  "last_conversation_at": "2026-07-26T05:00:00Z",
  "headline": "Continue your home plan",
  "summary": "You paused to discuss the budget with your spouse.",
  "completed_plan": false,
  "summary_status": "ready"
}
```

No memory:

```json
{
  "available": false
}
```

The endpoint must return display-safe fields only. It must not return the raw
transcript or serialized financial state.

### `POST /api/offer`

The frontend should create the SmallWebRTC endpoint URL with a query parameter:

```text
/api/offer?memory_mode=fresh
/api/offer?memory_mode=resume
```

The backend accepts only `fresh` or `resume` and defaults invalid/missing values
to `fresh`. The `on_connection` closure passes the resolved mode, user ID, and
new conversation ID into `run_bot()`.

Using a query parameter avoids modifying the SmallWebRTC SDP body. Confirm during
implementation that trickle-ICE PATCH requests continue to work with the
configured endpoint.

## Backend implementation tracker

### Phase B1 — Serializable state

- [x] Add a schema-versioned `export_state()` function in `core/session.py`.
- [x] Add a validating `restore_state()` function.
- [x] Rebuild every saved goal as a `Goal` dataclass.
- [x] Add `financial_snapshot_observed_at` to persistent state.
- [x] Add transient returning-call fields or an equivalent call context.
- [x] Ensure `reset()` clears all transient returning-call fields.
- [x] Add state round-trip tests.
- [x] Verify existing session, tool-guard, financial-math, and flow tests.

### Phase B2 — Conversation store

- [x] Add a small file-backed `ConversationStore`.
- [x] Generate collision-safe conversation IDs/directories.
- [x] Save transcript, state, and fallback summary together.
- [x] Use atomic JSON writes.
- [x] Implement meaningful-checkpoint detection.
- [x] Update `latest.json` only for meaningful calls.
- [x] Load the latest valid checkpoint for a user.
- [x] Recover safely from a missing or corrupt pointer/checkpoint.
- [x] Keep the current `output/transcripts` behaviour or update dependent eval
      tooling intentionally.
- [x] Add unit tests using pytest `tmp_path`; tests must never write to the real
      `output/conversations` directory.

### Phase B3 — Resume orchestration

- [x] Change `run_bot()` to accept `memory_mode`, `user_id`, and
      `conversation_id`.
- [x] Capture the persistent state at call start for meaningful-change
      comparison.
- [x] In fresh mode, call `session.reset()` regardless of existing memory.
- [x] In resume mode, load and restore the latest checkpoint.
- [x] Fall back to a fresh session when no valid checkpoint exists.
- [x] Build a returning-user context block from the saved summary and state.
- [x] Add a return gate before the normal stage-machine `next_step()`.
- [x] Handle completed plans with a review/update opening.
- [x] Ensure restored consent does not authorize a provider pull.
- [x] Save a checkpoint in both disconnect and `finally` paths exactly once.
- [x] Preserve transcript and cost metric saving.
- [x] Add orchestration tests for fresh, resume, fallback, and completed-plan
      calls.

### Phase B4 — Memory API

- [x] Add `GET /api/memory/latest`.
- [x] Return only card-safe fields.
- [x] Return `available=false` when no checkpoint exists.
- [x] Validate/sanitize the demo `user_id`.
- [x] Accept `memory_mode` on `POST /api/offer`.
- [x] Default missing or invalid mode to `fresh`.
- [x] Pass the resolved mode into the WebRTC connection callback.
- [x] Verify CORS and the Vite proxy for the new GET endpoint.
- [x] Add FastAPI endpoint tests.

### Phase B5 — Post-call summarizer

- [x] Implement deterministic fallback summary generation from saved state.
- [x] Define and validate the strict LLM summary schema.
- [x] Build summarizer input from transcript events plus authoritative state.
- [x] Add timeout and exception handling.
- [x] Atomically replace the fallback summary after successful validation.
- [x] Retain fallback output when the LLM call fails or returns invalid JSON.
- [x] Prevent summary output from mutating `SessionState`.
- [x] Prevent sensitive amounts from appearing on the entry card.
- [x] Add summarizer unit tests with a fake LLM client.

## Frontend implementation tracker

### Phase F1 — Route mode

- [x] Derive entry mode from `window.location.pathname`.
- [x] Treat exactly `/memory` and `/memory/` as resume routes.
- [x] Treat `/` and unknown paths as fresh unless a proper router is introduced.
- [x] Keep browser refresh working under the Vite development server.
- [x] Configure the production static-file fallback so `/memory` serves
      `index.html`.
- [x] Pass the selected mode through the component tree.
- [x] Build the WebRTC offer endpoint with the selected `memory_mode`.

### Phase F2 — Memory card

- [x] Define TypeScript types for the memory-card API response.
- [x] Fetch `/api/memory/latest?user_id=rakshit` only on the memory route.
- [x] Render a non-jarring loading/skeleton state.
- [x] Render the personalized headline and summary when available.
- [x] Render the completed-plan review copy when applicable.
- [x] Fall back to the fresh card when memory is unavailable.
- [x] Fall back safely when the fetch fails or returns malformed data.
- [x] Add a **Resume planning** primary action.
- [x] Add a **Start over** secondary action that selects fresh mode.
- [x] Keep sensitive financial values out of the memory card.
- [x] Preserve current responsive card layout and accessibility labels.

### Phase F3 — Frontend test foundation

- [x] Add Vitest.
- [x] Add React Testing Library and `@testing-library/jest-dom`.
- [x] Add a DOM test environment and setup file.
- [x] Add `npm test` and, if useful, `npm run test:watch`.
- [x] Mock fetch and the Pipecat client at component boundaries.
- [x] Ensure `npm run build` and `npm run lint` still pass.

## Backend automated test matrix

### State serialization

- [x] **BE-STATE-001:** Exporting a default reset state produces JSON-serializable
      output with the current schema version.
- [x] **BE-STATE-002:** Exporting and restoring a populated state preserves every
      persistent scalar, dictionary, list, and timestamp.
- [x] **BE-STATE-003:** Restored goals are `Goal` instances, not raw dictionaries.
- [x] **BE-STATE-004:** Multiple goals preserve order, priority, funded state, and
      computed fields.
- [x] **BE-STATE-005:** Unknown top-level state fields are rejected or ignored
      according to the documented compatibility policy.
- [x] **BE-STATE-006:** Missing optional fields from an older schema receive safe
      defaults.
- [x] **BE-STATE-007:** Invalid field types fail restoration and trigger fresh-mode
      fallback rather than partially mutating `STATE`.
- [x] **BE-STATE-008:** OTP and call-transient fields are absent from exported
      state.
- [x] **BE-STATE-009:** `reset()` after restore returns the configured KYC demo
      identity and clears restored planning data.

### Conversation store

- [x] **BE-STORE-001:** Saving a meaningful conversation creates transcript,
      state, summary, and latest-pointer files.
- [x] **BE-STORE-002:** Loading latest returns the exact state saved for that
      user.
- [x] **BE-STORE-003:** Two saves within the same second create distinct
      conversation directories.
- [x] **BE-STORE-004:** A greeting-only call does not advance `latest.json`.
- [x] **BE-STORE-005:** A failed connection with no state change does not advance
      `latest.json`.
- [x] **BE-STORE-006:** A state-changing tool call advances `latest.json`.
- [x] **BE-STORE-007:** A newer non-meaningful call leaves the previous meaningful
      checkpoint loadable.
- [x] **BE-STORE-008:** Missing `latest.json` returns no memory without raising.
- [x] **BE-STORE-009:** A pointer to a missing directory returns no memory or
      recovers the previous valid checkpoint according to implementation policy.
- [x] **BE-STORE-010:** Corrupt pointer JSON does not crash the API or call startup.
- [x] **BE-STORE-011:** Corrupt state JSON is never partially restored.
- [ ] **BE-STORE-012:** Atomic replacement leaves either the old or new complete
      JSON file when publication is interrupted.
- [x] **BE-STORE-013:** User identifiers cannot escape the configured conversation
      directory via `..`, slashes, or encoded separators.
- [x] **BE-STORE-014:** All store tests use an isolated temporary directory.

### Memory API

- [x] **BE-API-001:** No checkpoint returns HTTP 200 with
      `{"available": false}`.
- [x] **BE-API-002:** A valid checkpoint returns the expected display-safe card
      fields.
- [x] **BE-API-003:** The response excludes raw transcript, income, expenses,
      holdings, consent context, and full state.
- [x] **BE-API-004:** A fallback summary is returned with
      `summary_status=fallback`.
- [x] **BE-API-005:** A completed plan sets `completed_plan=true`.
- [x] **BE-API-006:** A corrupt checkpoint degrades to `available=false`.
- [x] **BE-API-007:** Invalid user IDs are rejected with a client error or mapped
      to the fixed demo user according to the documented policy.
- [x] **BE-API-008:** CORS permits the configured Vite development origin.

### Offer and call modes

- [x] **BE-CALL-001:** Missing `memory_mode` starts fresh.
- [x] **BE-CALL-002:** `memory_mode=fresh` resets state even when memory exists.
- [x] **BE-CALL-003:** `memory_mode=resume` restores the latest valid checkpoint.
- [x] **BE-CALL-004:** Invalid mode defaults to fresh and cannot trigger arbitrary
      file access.
- [x] **BE-CALL-005:** Resume without a checkpoint starts fresh.
- [x] **BE-CALL-006:** Resume sets the returning-session gate before the first LLM
      run.
- [x] **BE-CALL-007:** The first returning assistant turn welcomes the user and
      asks whether to continue; it does not immediately invoke the next financial
      tool.
- [x] **BE-CALL-008:** After resume confirmation, `next_step()` continues at the
      first genuinely incomplete planning stage.
- [x] **BE-CALL-009:** A completed restored plan enters review/update mode rather
      than the close/goodbye instruction.
- [x] **BE-CALL-010:** Restored provider data does not bypass explicit consent for
      a new pull.
- [x] **BE-CALL-011:** Disconnect and `finally` execution save the checkpoint only
      once.
- [x] **BE-CALL-012:** Existing transcript and metrics files are still saved.
- [x] **BE-CALL-013:** Trickle ICE PATCH continues to work when the POST offer URL
      includes the mode query parameter.

### Summarization

- [x] **BE-SUM-001:** Valid summarizer output is accepted and saved as
      `status=ready`.
- [x] **BE-SUM-002:** Invalid JSON retains the deterministic fallback.
- [x] **BE-SUM-003:** Output missing required fields retains the fallback.
- [x] **BE-SUM-004:** Timeout retains the fallback and does not block checkpoint
      availability.
- [x] **BE-SUM-005:** Provider exception retains the fallback.
- [x] **BE-SUM-006:** Summary generation does not mutate authoritative saved
      state.
- [x] **BE-SUM-007:** A user correction is represented as an update, not as two
      simultaneous current facts.
- [x] **BE-SUM-008:** An unfinished goal appears in `open_items` and informs
      `recommended_next_start`.
- [x] **BE-SUM-009:** A completed plan produces review/update copy.
- [x] **BE-SUM-010:** The card headline and summary do not contain income,
      holdings, account identifiers, or detailed financial amounts.
- [x] **BE-SUM-011:** The summarizer does not claim that old consent remains valid.
- [x] **BE-SUM-012:** An empty transcript is not sent for summarization and does
      not replace latest memory.

### Regression

- [x] **BE-REG-001:** All existing `tests/` pass.
- [x] **BE-REG-002:** Fresh calls retain the current stage order.
- [x] **BE-REG-003:** Tool guard failures still return `progress` and `next_step`.
- [x] **BE-REG-004:** Financial calculations return unchanged known-answer
      results.
- [x] **BE-REG-005:** Live transcript evaluation still accepts newly saved
      transcripts.

## Frontend automated test matrix

### Route behaviour

- [x] **FE-ROUTE-001:** `/` selects fresh mode.
- [x] **FE-ROUTE-002:** `/memory` selects resume mode.
- [x] **FE-ROUTE-003:** `/memory/` selects resume mode.
- [x] **FE-ROUTE-004:** An unknown path safely selects fresh mode.
- [x] **FE-ROUTE-005:** Refreshing `/memory` renders the app instead of a static
      404 in development.

### Fetching memory

- [x] **FE-MEM-001:** `/` does not request `/api/memory/latest`.
- [x] **FE-MEM-002:** `/memory` requests the latest memory once with the demo user
      ID.
- [x] **FE-MEM-003:** A loading state is shown while the request is pending.
- [x] **FE-MEM-004:** `available=true` renders the returned headline and summary.
- [x] **FE-MEM-005:** `available=false` renders the fresh card.
- [x] **FE-MEM-006:** A network error renders the fresh fallback and leaves the
      CTA usable.
- [x] **FE-MEM-007:** Malformed JSON renders the fresh fallback.
- [x] **FE-MEM-008:** A fallback summary remains displayable.
- [x] **FE-MEM-009:** A completed plan renders “Review or update” copy.

### Starting calls

- [x] **FE-CALL-001:** The `/` primary CTA connects using
      `memory_mode=fresh`.
- [x] **FE-CALL-002:** The personalized `/memory` primary CTA connects using
      `memory_mode=resume`.
- [x] **FE-CALL-003:** `/memory` with no available memory connects using fresh
      mode.
- [x] **FE-CALL-004:** The **Start over** action connects using fresh mode.
- [x] **FE-CALL-005:** Repeated CTA taps while connecting produce only one
      connection attempt.
- [x] **FE-CALL-006:** A microphone or backend error restores an actionable CTA and
      displays the existing error message.
- [ ] **FE-CALL-007:** Ending the call disconnects once and allows a later call to
      start.

### Card presentation and accessibility

- [x] **FE-CARD-001:** Fresh-route card retains “Maya is ready” and “Start
      planning.”
- [x] **FE-CARD-002:** Resume card shows “Maya remembers,” user name, headline,
      and concise summary.
- [x] **FE-CARD-003:** Resume CTA has an accessible label describing continuation.
- [x] **FE-CARD-004:** Start-over action is keyboard accessible.
- [ ] **FE-CARD-005:** Long but valid summary text does not overflow the card at
      phone width.
- [ ] **FE-CARD-006:** Loading, fallback, and personalized states do not cause
      destructive layout shift.
- [x] **FE-CARD-007:** API-provided strings render as text and cannot inject HTML.
- [x] **FE-CARD-008:** No detailed sensitive financial values are rendered from
      accidental extra API properties.

### Frontend regression

- [x] **FE-REG-001:** `npm test` passes.
- [x] **FE-REG-002:** `npm run lint` passes.
- [x] **FE-REG-003:** `npm run build` passes.
- [ ] **FE-REG-004:** OTP sheet still works during fresh and resumed calls.
- [ ] **FE-REG-005:** Ledger and artifact cards still receive live snapshots.
- [ ] **FE-REG-006:** Plan hero and end-call controls remain functional.

## End-to-end and manual acceptance tests

- [ ] **E2E-001 — Primary two-call demo**
  1. Open `/`.
  2. Start a call and provide enough information to create a home goal.
  3. Say that the budget must be discussed with the spouse.
  4. End the call.
  5. Open `/memory`.
  6. Verify that the card references the unfinished home-plan discussion.
  7. Resume and verify Maya welcomes Rakshit back before continuing.

- [ ] **E2E-002 — Correction across sessions**
  1. Resume a saved home goal.
  2. Change its target from the previously saved value.
  3. Verify the old goal is updated/versioned rather than duplicated.
  4. Verify dependent gap/SIP results are recalculated by tools.
  5. Verify the next saved summary describes the correction.

- [ ] **E2E-003 — Fresh isolation**
  1. Ensure useful memory exists.
  2. Open `/`.
  3. Verify the standard card appears.
  4. Start the call and verify Maya uses the first-call greeting and risk stage.
  5. Verify no old goal is present in live state.

- [ ] **E2E-004 — Start over from memory**
  1. Open `/memory` with useful memory present.
  2. Select **Start over**.
  3. Verify the new call is fresh.
  4. Verify the previous checkpoint remains on disk until the new call becomes
     meaningful.

- [ ] **E2E-005 — Empty call protection**
  1. Record the current personalized card.
  2. Start and immediately end a fresh call without meaningful input.
  3. Reload `/memory`.
  4. Verify the previous personalized card remains current.

- [ ] **E2E-006 — Summarizer outage**
  1. Disable or mock failure of the summarizer.
  2. Complete a meaningful call.
  3. Open `/memory` immediately.
  4. Verify a deterministic personalized fallback is displayed.
  5. Verify the resumed call starts successfully.

- [ ] **E2E-007 — Stale financial data**
  1. Resume a checkpoint containing previously observed financial data.
  2. Verify Maya identifies it as previous data.
  3. Verify Maya asks before initiating a fresh provider pull.
  4. Verify previous consent is not silently reused.

- [ ] **E2E-008 — Completed plan**
  1. Save a fully completed plan.
  2. Open `/memory`.
  3. Verify the card offers review/update.
  4. Verify Maya asks what changed rather than closing the call.

- [ ] **E2E-009 — Corrupt memory fallback**
  1. In an isolated test directory, corrupt the latest state file.
  2. Open `/memory`.
  3. Verify the UI falls back safely.
  4. Verify starting a fresh call remains possible.

- [ ] **E2E-010 — Restart persistence**
  1. Complete a meaningful call.
  2. Stop and restart the backend.
  3. Open `/memory`.
  4. Verify the personalized card and restored state still work.

## Recommended implementation order

- [x] Complete B1: serialization and restoration.
- [x] Complete B2: file-backed checkpoints and meaningful-save policy.
- [x] Complete B3: fresh/resume call orchestration.
- [x] Complete B4: memory-card API and offer mode.
- [x] Complete F1 and F2: routes and personalized card.
- [x] Complete F3 and the frontend automated tests.
- [x] Complete B5: deterministic summary first, then optional LLM enhancement.
- [ ] Run backend, frontend, regression, and end-to-end suites.
- [ ] Rehearse E2E-001, E2E-002, E2E-005, and E2E-006 before judging.

## Suggested verification commands

```bash
pytest tests/ -v
```

```bash
cd web
npm test
npm run lint
npm run build
```

```bash
python server.py
```

Then manually verify:

```text
http://localhost:5173/
http://localhost:5173/memory
```

## Voice input reliability addendum

- [x] Move Silero VAD from the ignored Pipecat 1.3 transport parameter to
      `LLMUserAggregatorParams`.
- [x] Apply RNNoise before audio reaches STT and VAD.
- [x] Filter only unambiguous non-speech transcript artifacts before the
      transcript recorder and LLM.
- [x] Preserve short replies, ages, amounts, and normal financial-planning
      utterances.
- [x] Add automated tests for the active VAD configuration, RNNoise transport
      configuration, and transcript acceptance/rejection policy.
- [x] Relax speech-start confidence and volume after live noisy-room testing
      showed that valid speech was being missed.
- [x] Reconnect and retry once when the Sarvam STT WebSocket drops during a
      longer call.
- [x] Separate speech detection from barge-in: VAD may capture noisy speech,
      while interrupting Maya requires at least two recognized words.
- [ ] Rehearse a live call with representative hackathon background noise and
      tune the thresholds only if the recording shows false starts or missed
      quiet speech.

## Financial decision simulator addendum

- [x] Add `/simulator` and `/simulator/` as a third call mode.
- [x] Start every simulator call from a deterministic, fully confirmed pre-goal
      profile instead of loading saved memory.
- [x] Prevent simulator calls from publishing or replacing `/memory` checkpoints.
- [x] Ask the user to choose traditional goal planning or the financial decision
      simulator before calling a tool.
- [x] Route traditional planning directly to goals without repeating risk,
      family, consent, or data collection.
- [x] Add deterministic career-break, home-timing, and starting-family
      simulations in `core/finmath.py`.
- [x] Keep simulations hypothetical and leave the confirmed financial snapshot
      unchanged.
- [x] Render a scenario menu and a before-and-after comparison card.
- [x] Add backend and frontend coverage for simulator routing, profile seeding,
      memory isolation, branching, math, and output evaluation.
- [ ] Rehearse each simulator scenario once through the live microphone path.

## Verification log

Add entries in this format:

```text
- YYYY-MM-DD — Phase B1 — `pytest tests/test_session_persistence.py -v` — PASS
```

- 2026-07-26 — Phases B1-B5 — `pytest tests/ -q` — PASS (84 tests)
- 2026-07-26 — Phases F1-F3 — `npm test` — PASS (19 tests)
- 2026-07-26 — Frontend regression — `npm run lint && npm run build` — PASS
- 2026-07-26 — Python syntax — `python -m compileall -q core agent bot.py server.py` — PASS
- 2026-07-26 — Browser smoke test — isolated `/` and `/memory` routes, personalized
  card, fresh card, and Start over transition — PASS
- 2026-07-26 — Voice input reliability — `pytest tests/test_audio_input.py -v`
  — PASS (15 tests)
- 2026-07-26 — Backend regression after voice input changes — `pytest tests/ -q`
  — PASS (99 tests)
- 2026-07-26 — RNNoise 16 kHz smoke test — initialization, resampling, and
  one-second silence filtering — PASS
- 2026-07-26 — Noisy-room VAD and Sarvam reconnect regression —
  `pytest tests/ -q` — PASS (101 tests)
- 2026-07-26 — False barge-in regression with transcription-gated interruption —
  `pytest tests/ -q` — PASS (101 tests)
- 2026-07-26 — Simulator backend and existing regression —
  `pytest tests/ --ignore=tests/test_plan_pdf_language.py -q` — PASS (113 tests);
  the concurrently added PDF-language test requires the not-yet-installed
  `pypdf` package during collection.
- 2026-07-26 — Simulator frontend — `npm test -- --run && npm run lint &&
  npm run build` — PASS (23 tests)
- 2026-07-26 — Emergency backend and existing regression —
  `pytest tests/ --ignore=tests/test_plan_pdf_language.py -q` — PASS (127 tests);
  the unrelated PDF-language test still requires `pypdf` during collection.
- 2026-07-26 — Emergency frontend — `npm test -- --run && npm run lint &&
  npm run build` — PASS (24 tests)
- 2026-07-26 — Emergency Python syntax —
  `python -m compileall -q core agent bot.py server.py` — PASS
- 2026-07-26 — Scenario-aware emergency conversation regression —
  `pytest tests/ --ignore=tests/test_plan_pdf_language.py -q` — PASS (128 tests);
  frontend tests, lint, and production build — PASS
- 2026-07-26 — Runway extension and fund-withdrawal regression —
  `pytest tests/ --ignore=tests/test_plan_pdf_language.py -q` — PASS (129 tests);
  frontend tests, lint, and production build — PASS

## Decisions

- File-backed checkpoints instead of Supermemory or a database.
- Route-controlled demo modes: `/` is fresh and `/memory` is resume.
- Saved structured state is authoritative; transcript prose is not.
- Post-call summarization is a bounded structured-output operation, not an
  autonomous financial agent.
- Deterministic fallback summary is always available before optional LLM
  summarization.
- Empty calls do not replace meaningful memory.
- Starting fresh never requires deleting earlier files.
- The installed SmallWebRTC transport reuses the exact endpoint for POST and
  trickle-ICE PATCH, so the `memory_mode` query parameter is preserved.
- Unsupported checkpoint schema versions are ignored and resume falls back fresh;
  migration is out of scope for the hackathon.
- `/simulator` uses a repeatable demo profile, never restores saved memory, and
  never advances the latest-memory pointer.
- Simulator calculations remain hypothetical until a future explicit
  adopt-scenario action is designed.
- Emergency mode reuses a deterministic completed plan, proposes changes before
  mutating it, requires explicit acceptance, supports undo, and never publishes
  cross-session memory.

## Open issues

- Define the exact freshness period for restored MF Central and Account
  Aggregator data. Until defined, always describe it as previous-session data and
  ask before refreshing.
- Complete the real microphone/OTP two-call rehearsal before judging. Automated
  orchestration and browser tests do not substitute for the live voice path.
- `BE-STORE-012` remains a fault-injection test gap: atomic writes use
  `os.replace()`, but process interruption at each write boundary is not simulated.

## Emergency plan addendum

- [x] Add a prominent Emergency action to `/simulator`.
- [x] Signal `memory_mode=emergency` before the WebRTC call connects.
- [x] Load a completed demo plan with an emergency fund, Pune home, and
      daughter's education.
- [x] Make Maya's first line exactly “What's up, Rakshit? What's the emergency?”
- [x] Add deterministic income-interruption and urgent-cost calculations.
- [x] Show reserve, monthly investment, runway, and per-goal shockwaves.
- [x] Let the user protect a named goal and recalculate the proposal.
- [x] Require explicit acceptance before changing the plan.
- [x] Add reversible undo and keep emergency calls out of `/memory`.
- [x] Add backend and frontend automated coverage.
- [x] Match the first response to the event: support for loss or illness,
      congratulations for a positive transition, and a steady tone for neutral
      decisions.
- [x] Reuse amounts and timelines already stated instead of asking again.
- [x] Lead with a three-part decision framework before narrating calculations.
- [x] Add a no-numbers orientation path for a new child.
- [x] Show current liquid cash and current runway for an income interruption.
- [x] Calculate twelve- and eighteen-month runway targets.
- [x] Recommend exact fund-level withdrawals using weaker holdings first,
      followed by liquid and short-duration debt before core equity.
- [x] Include an exit-load and tax-period execution caveat without inventing tax.
- [ ] Rehearse one income interruption and one urgent cost through the live
      microphone path.
