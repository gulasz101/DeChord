# Product Completion Program Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Finish the remaining major product gaps through vertical, test-backed user journeys so DeChord becomes progressively more complete without falling back into partial rewrites.

**Architecture:** Use one master roadmap with six ordered vertical slices: processing, song detail, player, notes/rehearsal, collaboration, and hardening. Each slice must be implemented with TDD, verified through the real shell, and re-checked after `make reset`. Reuse existing plans where possible, but treat this document as the top-level execution and sequencing source of truth.

**Tech Stack:** FastAPI, Python 3.13+, React 19, Vite, TypeScript, Vitest, Testing Library, pytest, portless, LibSQL.

---

## XML Tracking

<phase id="product-completion-program" status="in_progress">
  <task>[x] Task 1: Create the master gap matrix and baseline verification record.</task>
  <task>[x] Task 2: Plan the processing-journey slice in detail.</task>
  <task>[x] Task 3: Implement and verify the processing-journey slice.</task>
  <task>[x] Task 4: Plan the song-detail-completeness slice in detail.</task>
  <task>[x] Task 5: Implement and verify the song-detail-completeness slice.</task>
  <task>[x] Task 6: Plan the real-player slice in detail.</task>
  <task>[ ] Task 7: Implement and verify the real-player slice.</task>
  <task>[ ] Task 8: Plan the notes-and-rehearsal slice in detail.</task>
  <task>[ ] Task 9: Implement and verify the notes-and-rehearsal slice.</task>
  <task>[ ] Task 10: Plan the collaboration slice in detail.</task>
  <task>[ ] Task 11: Implement and verify the collaboration slice.</task>
  <task>[ ] Task 12: Plan the hardening-and-finish slice in detail.</task>
  <task>[ ] Task 13: Implement and verify the hardening-and-finish slice.</task>
  <task>[ ] Task 14: Run full reset-based verification, update the plan records, and prepare handoff.</task>
</phase>

## Program Rules

- Use TDD for every slice: write failing tests first, confirm they fail, implement the minimum change, then rerun tests.
- Do not merge unrelated improvements into the active slice. Record follow-ups here instead.
- Any change touching upload, stems, tabs, playback, or sync must include player-aware tests or verification.
- Use `test songs/Clara Luciani - La grenade.mp3` as the default real upload fixture when a slice needs manual workflow validation.
- Existing child plans can be reused, but only if they are explicitly linked back into this master plan.

## Slice Tracking Ledger

Use this section as the durable landing zone for each slice's linked docs, status notes, verification notes, and eventual commit links.

### Slice 1: Processing Journey

- Status: Complete and verification-backed.
- Design doc: `docs/plans/2026-03-10-processing-journey-design.md`
- Implementation doc: `docs/plans/2026-03-10-processing-journey-implementation.md` (includes XML `<phase>` / `<task>` tracking for execution)
- Verification notes: On 2026-03-11, `npm --prefix frontend test -- --run src/lib/__tests__/api.processing-journey.test.ts src/redesign/pages/__tests__/ProcessingJourneyPage.test.tsx src/__tests__/App.integration.test.tsx` passed before reset (3 files, 16 tests), `make reset` completed successfully, and the same focused test command passed again after reset (3 files, 16 tests). Fresh backend regression checks then passed: `uv run --group dev pytest tests/test_stems.py -k "wrapped_missing_demucs_dependency or raises_when_demucs_fails_without_fallback_opt_in or falls_back_when_demucs_runner_fails or wraps_missing_dependency_error" -q` (4 passed) and `uv run --group dev pytest tests/test_quantization.py -q` (3 passed). After `make reset` and `make up`, the runtime served frontend at `http://127.0.0.1:4655` and backend at `http://127.0.0.1:4458`; a real upload of `test songs/Clara Luciani - La grenade.mp3` entered the processing journey, job `6fd381a5cb65` progressed through `analyzing_chords` -> `splitting_stems` -> `transcribing_bass_midi` -> `complete`, and final polling reported `status=complete`, `stems_status=complete`, `midi_status=complete`, `tab_status=complete`. The frontend then auto-opened song detail showing `Clara Luciani - La grenade`, status `ready`, `91` chords, and a persisted stems list with `Generate Stems` and `Generate Bass Tab`. Supporting local commits: `e8e6e5b` and `c592c82`.
- Commit links: local commits `dda100f` (processing journey API contract tests), `a9b018c` (processing journey route surface), `6935ddc` (route-level upload/polling/song-detail wiring), `e8e6e5b` (Demucs missing-runtime fallback), and `c592c82` (quantization tail infinite-loop fix). Pushed links not recorded yet.

### Slice 2: Song Detail Completeness

- Status: Complete and verification-backed.
- Design doc: `docs/plans/2026-03-10-song-detail-completeness-design.md`
- Implementation doc: `docs/plans/2026-03-10-song-detail-completeness-implementation.md`
- Verification notes: On 2026-03-11, focused verification passed before reset with `npm --prefix frontend test -- --run src/lib/__tests__/api.song-detail-assets.test.ts src/redesign/pages/__tests__/SongDetailPage.test.tsx src/__tests__/App.integration.test.tsx` (3 files passed, 22 tests passed) and `uv run --project backend pytest backend/tests/test_api.py -k "upload_song_stem_persists_user_asset_and_returns_provenance or upload_song_stem_same_filename_creates_distinct_storage_and_versions or song_tabs_metadata_includes_source_provenance_fields or song_tabs_provenance_stays_tied_to_generated_source_after_later_replacement or regenerate_song_stems_preserves_active_user_upload_for_same_key or regenerate_song_stems_prunes_obsolete_system_rows_but_keeps_user_rows or generate_tab_from_demucs_stems_persists_transient_uploaded_provenance_for_existing_song or regenerate_song_tabs_uses_selected_stem_and_persists_new_tab or tabs_metadata_endpoint_returns_latest_tab" -q` (9 passed, 31 deselected, warnings limited to the existing FastAPI `on_event` deprecations). `make reset` then passed, `make up` passed, and the runtime after the final restart served frontend at `http://127.0.0.1:4553` and backend at `http://127.0.0.1:4836`. After reset, the same focused frontend command passed again with 22 tests passed and the same focused backend command passed again with 9 passed, 31 deselected, and the same warnings only. Manual verification with `test songs/Clara Luciani - La grenade.mp3` used upload job `814babe1d554`, observed processing `analyzing_chords -> splitting_stems -> transcribing_bass_midi -> complete`, and finished with backend `status=complete`, `stems_status=complete`, `midi_status=complete`, `tab_status=complete`. On the verified `Clara Luciani - La grenade` song detail page, the real `Generate Stems` action was opened and confirmed, the inline panel showed `Stems regenerated.`, the active system stem rows refreshed in place, and the visible version labels for drums/other/vocals changed from `v5686` to `v758847` while the uploaded user bass stem remained active and unchanged with display name `Clara Luciani - La grenade.mp3`, source `User`, and uploader `Wojtek`. This provides explicit manual evidence that regenerate-stems refreshes system stems while preserving the active user override for the same key. The frontend auto-opened song detail for `Clara Luciani - La grenade`, initially showed system stems plus current bass tab provenance `Generated from Bass.` / `Provenance: System`, refreshed the bass stem row after replacement upload to display name `Clara Luciani - La grenade.mp3`, source `User`, uploader `Wojtek`, preserved the current bass tab provenance on the last generated tab until regeneration, and after regenerating bass tab from the uploaded bass stem showed `Generated from Clara Luciani - La grenade.mp3.`, `Provenance: User`, and updated timestamp `2026-03-11 14:29:46`.
- Commit links: local commits `a111de1`, `fb76619`, `e787403`, `4df07b9`, and `df06c0a`. Pushed links not recorded yet.

### Slice 3: Real Player

- Status: Planned and ready for implementation.
- Design doc: `docs/plans/2026-03-10-real-player-design.md`
- Implementation doc: `docs/plans/2026-03-10-real-player-implementation.md` (includes XML `<phase>` / `<task>` tracking for execution and an explicit player quality gate)
- Verification notes: Not recorded yet.
- Commit links: Not recorded yet.

### Slice 4: Notes and Rehearsal

- Status: Planned, not started.
- Design doc: `docs/plans/2026-03-10-notes-rehearsal-design.md` (to create)
- Implementation doc: `docs/plans/2026-03-10-notes-rehearsal-implementation.md` (to create)
- Verification notes: Not recorded yet.
- Commit links: Not recorded yet.

### Slice 5: Collaboration

- Status: Planned, not started.
- Design doc: `docs/plans/2026-03-10-collaboration-design.md` (to create)
- Implementation doc: `docs/plans/2026-03-10-collaboration-implementation.md` (to create)
- Verification notes: Not recorded yet.
- Commit links: Not recorded yet.

### Slice 6: Hardening and Finish

- Status: Planned, not started.
- Design doc: `docs/plans/2026-03-10-hardening-finish-design.md` (to create)
- Implementation doc: `docs/plans/2026-03-10-hardening-finish-implementation.md` (to create)
- Verification notes: Not recorded yet.
- Commit links: Not recorded yet.

## Task 1: Create Master Gap Matrix and Baseline

**Files:**
- Modify: `docs/plans/2026-03-10-product-completion-program-implementation.md`
- Create: `docs/plans/2026-03-10-product-completion-gap-matrix.md`
- Inspect: `docs/plans/2026-03-10-real-frontend-no-mocks-implementation.md`
- Inspect: `docs/plans/2026-03-10-opus53-song-detail-generation-design.md`
- Inspect: `frontend/src/App.tsx`
- Inspect: `frontend/src/redesign/pages/PlayerPage.tsx`
- Inspect: `backend/app/main.py`

**Step 1: Write the gap-matrix document**

Capture, at minimum:
- each major product surface
- current real status
- current mock/local-only status
- missing backend pieces
- missing frontend wiring
- planned slice assignment

**Step 2: Record baseline verification commands**

List the current targeted checks that will be used during the program, such as:

```bash
npm --prefix frontend test -- --run src/__tests__/App.integration.test.tsx
npm --prefix frontend test -- --run src/redesign/pages/__tests__/SongDetailPage.test.tsx src/components/__tests__/TabViewerPanel.test.tsx src/components/__tests__/TransportBarSpeed.test.tsx
uv run --project backend pytest backend/tests/test_api.py -q
```

**Step 3: Run the baseline checks and record status**

Run the exact commands you listed and note pass/fail plus any obvious missing coverage.

### Task 1 Baseline Verification Record

**Commands**

```bash
uv run --project backend pytest backend/tests/test_api.py -q
npm --prefix frontend test -- --run src/__tests__/App.integration.test.tsx
```

**Current status as of 2026-03-10**

- `uv run --project backend pytest backend/tests/test_api.py -q` is a known pre-existing red baseline: 32 tests pass and 1 test fails.
- The current pre-existing backend failure is `backend/tests/test_api.py::test_list_bands_projects_and_project_songs`.
- `npm --prefix frontend test -- --run src/__tests__/App.integration.test.tsx` is green: 10 tests pass.
- Current baseline coverage is enough to anchor the program, but it does not yet protect honest processing state transitions, real player playback, note mutation flows, or collaboration truth.

**Baseline interpretation**

- The frontend app shell has a stable no-mocks integration baseline for band/project/song navigation and creation flows.
- The backend API suite already exposes one known hierarchy/listing defect before product-completion slices start; that failure should be treated as inherited baseline debt until a slice explicitly addresses it.
- The new master gap matrix in `docs/plans/2026-03-10-product-completion-gap-matrix.md` is the source-of-truth audit for what remains incomplete across the real product surfaces.

**Step 4: Commit**

```bash
git add docs/plans/2026-03-10-product-completion-program-implementation.md docs/plans/2026-03-10-product-completion-gap-matrix.md
git commit -m "docs: add product completion gap matrix baseline (docs/plans/2026-03-10-product-completion-program-implementation.md task: Create the master gap matrix and baseline verification record) | opencode | gpt-5.1-codex-max"
```

## Task 2: Plan Processing Journey Slice

**Files:**
- Create: `docs/plans/2026-03-10-processing-journey-design.md`
- Create: `docs/plans/2026-03-10-processing-journey-implementation.md`
- Inspect: `frontend/src/lib/api.ts`
- Inspect: `frontend/src/App.tsx`
- Inspect: `frontend/src/redesign/pages/SongLibraryPage.tsx`
- Inspect: `backend/app/main.py`

**Step 1: Write the design doc**

Define the exact user promise:
- after upload, the user sees honest queued/processing/complete/error state
- the song transitions visibly into library/detail state
- the UI does not rely on silent refresh as the only feedback

**Step 2: Write the implementation plan**

Include bite-sized TDD tasks for:
- frontend polling/status integration
- backend status edge cases if needed
- app-shell refresh behavior
- error handling
- tests and manual verification using `test songs/Clara Luciani - La grenade.mp3`

**Step 3: Update this master plan with links**

Add references to the new child plans under the processing slice.

**Step 4: Commit**

```bash
git add docs/plans/2026-03-10-processing-journey-design.md docs/plans/2026-03-10-processing-journey-implementation.md docs/plans/2026-03-10-product-completion-program-implementation.md
git commit -m "docs: plan processing journey slice (docs/plans/2026-03-10-product-completion-program-implementation.md task: Plan the processing-journey slice in detail) | opencode | gpt-5.1-codex-max"
```

## Task 3: Implement and Verify Processing Journey Slice

**Files:**
- Follow: `docs/plans/2026-03-10-processing-journey-implementation.md`
- Modify: `docs/plans/2026-03-10-product-completion-program-implementation.md`

**Step 1: Execute the child implementation plan with strict TDD**

Use the child plan as the execution record for the actual code changes.

**Step 2: Run focused verification**

Run the targeted frontend/backend tests defined in the child plan.

**Step 3: Run reset-based verification**

Run:

```bash
make reset
```

Then rerun the slice verification and, if relevant, manually verify upload flow with `test songs/Clara Luciani - La grenade.mp3`.

**Step 4: Update status in this master plan**

Mark the slice complete and record links to child plan commits.

## Task 4: Plan Song Detail Completeness Slice

**Files:**
- Create: `docs/plans/2026-03-10-song-detail-completeness-design.md`
- Create: `docs/plans/2026-03-10-song-detail-completeness-implementation.md`
- Inspect: `docs/plans/2026-03-10-opus53-song-detail-generation-design.md`
- Inspect: `frontend/src/redesign/pages/SongDetailPage.tsx`
- Inspect: `frontend/src/App.tsx`
- Inspect: `backend/app/main.py`

**Step 1: Write the design doc**

Clarify the full song-detail promise:
- no dead primary buttons
- upload stem is real
- stem and tab asset surfaces reflect backend truth
- user sees actionable generation success/failure states

**Step 2: Write the implementation plan**

Break down TDD tasks for:
- upload-stem flow
- tab metadata exposure/rendering
- state refresh behavior
- route-level integration tests

**Step 3: Link the slice plans from this master plan**

**Step 4: Commit**

```bash
git add docs/plans/2026-03-10-song-detail-completeness-design.md docs/plans/2026-03-10-song-detail-completeness-implementation.md docs/plans/2026-03-10-product-completion-program-implementation.md
git commit -m "docs: plan song detail completeness slice (docs/plans/2026-03-10-product-completion-program-implementation.md task: Plan the song-detail-completeness slice in detail) | opencode | gpt-5.1-codex-max"
```

## Task 5: Implement and Verify Song Detail Completeness Slice

**Files:**
- Follow: `docs/plans/2026-03-10-song-detail-completeness-implementation.md`
- Modify: `docs/plans/2026-03-10-product-completion-program-implementation.md`

**Step 1: Execute the child implementation plan with TDD**

**Step 2: Run focused verification**

At minimum include relevant song-detail and API tests.

**Step 3: Run `make reset` and verify again**

**Step 4: Update this master plan with completion status and commit links**

## Task 6: Plan Real Player Slice

**Files:**
- Create: `docs/plans/2026-03-10-real-player-design.md`
- Create: `docs/plans/2026-03-10-real-player-implementation.md`
- Inspect: `frontend/src/redesign/pages/PlayerPage.tsx`
- Inspect: `frontend/src/hooks/useAudioPlayer.ts`
- Inspect: `frontend/src/lib/playbackSources.ts`
- Inspect: `frontend/src/components/TabViewerPanel.tsx`
- Inspect: `backend/app/main.py`

**Step 1: Write the design doc**

Define the real player promise:
- real audio source
- real tab asset source
- transport and sync correctness
- stem-aware playback behavior
- preference persistence

**Step 2: Write the implementation plan**

Break down TDD tasks for:
- player state wiring
- transport integration
- real asset URLs
- playback-prefs save/restore
- player-specific component and integration coverage

**Step 3: Explicitly define the player quality gate**

List the exact tests and manual checks required before the slice can close.

**Step 4: Commit**

```bash
git add docs/plans/2026-03-10-real-player-design.md docs/plans/2026-03-10-real-player-implementation.md docs/plans/2026-03-10-product-completion-program-implementation.md
git commit -m "docs: plan real player slice (docs/plans/2026-03-10-product-completion-program-implementation.md task: Plan the real-player slice in detail) | opencode | gpt-5.1-codex-max"
```

## Task 7: Implement and Verify Real Player Slice

**Files:**
- Follow: `docs/plans/2026-03-10-real-player-implementation.md`
- Modify: `docs/plans/2026-03-10-product-completion-program-implementation.md`

**Step 1: Execute the child implementation plan with TDD**

**Step 2: Run the player quality gate**

At minimum run the focused player tests defined in the child plan.

**Step 3: Run `make reset` and repeat player verification**

If manual verification is required, use `test songs/Clara Luciani - La grenade.mp3`.

**Step 4: Update this master plan with completion status and commit links**

## Task 8: Plan Notes and Rehearsal Slice

**Files:**
- Create: `docs/plans/2026-03-10-notes-rehearsal-design.md`
- Create: `docs/plans/2026-03-10-notes-rehearsal-implementation.md`
- Inspect: `frontend/src/redesign/pages/SongDetailPage.tsx`
- Inspect: `frontend/src/redesign/pages/PlayerPage.tsx`
- Inspect: `frontend/src/lib/api.ts`
- Inspect: `backend/app/main.py`

**Step 1: Write the design doc**

Define the rehearsal-note promise:
- users can create, edit, delete, and resolve comments
- comments connect to time or chord context
- the player and detail views stay consistent

**Step 2: Write the implementation plan**

Include TDD tasks for API usage, UI entry points, and interaction tests.

**Step 3: Link the child plans from this master plan**

**Step 4: Commit**

```bash
git add docs/plans/2026-03-10-notes-rehearsal-design.md docs/plans/2026-03-10-notes-rehearsal-implementation.md docs/plans/2026-03-10-product-completion-program-implementation.md
git commit -m "docs: plan notes and rehearsal slice (docs/plans/2026-03-10-product-completion-program-implementation.md task: Plan the notes-and-rehearsal slice in detail) | opencode | gpt-5.1-codex-max"
```

## Task 9: Implement and Verify Notes and Rehearsal Slice

**Files:**
- Follow: `docs/plans/2026-03-10-notes-rehearsal-implementation.md`
- Modify: `docs/plans/2026-03-10-product-completion-program-implementation.md`

**Step 1: Execute the child implementation plan with TDD**

**Step 2: Run focused verification**

Include both route-level and component-level tests for note interactions.

**Step 3: Run `make reset` and verify again**

**Step 4: Update this master plan with completion status and commit links**

## Task 10: Plan Collaboration Slice

**Files:**
- Create: `docs/plans/2026-03-10-collaboration-design.md`
- Create: `docs/plans/2026-03-10-collaboration-implementation.md`
- Inspect: `frontend/src/redesign/lib/types.ts`
- Inspect: `frontend/src/redesign/pages/ProjectHomePage.tsx`
- Inspect: `frontend/src/App.tsx`
- Inspect: `backend/app/db_schema.sql`
- Inspect: `backend/app/main.py`

**Step 1: Write the design doc**

Define the collaboration promise:
- member list truth
- activity visibility
- unread count strategy
- presence strategy
- honest handling of anything still deferred

**Step 2: Write the implementation plan**

Break down TDD tasks for schema/API/UI work with explicit non-goals to avoid overscoping.

**Step 3: Link the child plans from this master plan**

**Step 4: Commit**

```bash
git add docs/plans/2026-03-10-collaboration-design.md docs/plans/2026-03-10-collaboration-implementation.md docs/plans/2026-03-10-product-completion-program-implementation.md
git commit -m "docs: plan collaboration slice (docs/plans/2026-03-10-product-completion-program-implementation.md task: Plan the collaboration slice in detail) | opencode | gpt-5.1-codex-max"
```

## Task 11: Implement and Verify Collaboration Slice

**Files:**
- Follow: `docs/plans/2026-03-10-collaboration-implementation.md`
- Modify: `docs/plans/2026-03-10-product-completion-program-implementation.md`

**Step 1: Execute the child implementation plan with TDD**

**Step 2: Run focused verification**

**Step 3: Run `make reset` and verify again**

**Step 4: Update this master plan with completion status and commit links**

## Task 12: Plan Hardening and Finish Slice

**Files:**
- Create: `docs/plans/2026-03-10-hardening-finish-design.md`
- Create: `docs/plans/2026-03-10-hardening-finish-implementation.md`
- Inspect: `backend/app/main.py`
- Inspect: `frontend/src/App.tsx`
- Inspect: `backend/tests/`
- Inspect: `frontend/src/__tests__/`

**Step 1: Write the design doc**

Define finish-level behavior for:
- job persistence/retry/cancellation direction
- reset-safe startup
- release-readiness checks
- remaining known product honesty gaps

**Step 2: Write the implementation plan**

Break down TDD tasks for the smallest hardening work that meaningfully improves finish quality.

**Step 3: Link the child plans from this master plan**

**Step 4: Commit**

```bash
git add docs/plans/2026-03-10-hardening-finish-design.md docs/plans/2026-03-10-hardening-finish-implementation.md docs/plans/2026-03-10-product-completion-program-implementation.md
git commit -m "docs: plan hardening and finish slice (docs/plans/2026-03-10-product-completion-program-implementation.md task: Plan the hardening-and-finish slice in detail) | opencode | gpt-5.1-codex-max"
```

## Task 13: Implement and Verify Hardening and Finish Slice

**Files:**
- Follow: `docs/plans/2026-03-10-hardening-finish-implementation.md`
- Modify: `docs/plans/2026-03-10-product-completion-program-implementation.md`

**Step 1: Execute the child implementation plan with TDD**

**Step 2: Run focused verification**

**Step 3: Run `make reset` and verify again**

**Step 4: Update this master plan with completion status and commit links**

## Task 14: Final Verification and Handoff

**Files:**
- Modify: `docs/plans/2026-03-10-product-completion-program-implementation.md`
- Modify: child plans as needed with completion links

**Step 1: Run full reset-based verification**

Run:

```bash
make reset
```

Then run the final full command set defined by the completed slices.

**Step 2: Record final status**

Update this master plan with:
- completed slice list
- remaining deferred work
- verification evidence
- commit links if work has been pushed

**Step 3: Prepare handoff summary**

Summarize:
- what is now truly finished
- what remains
- what the next best slice is if work continues

**Step 4: Commit**

```bash
git add docs/plans/2026-03-10-product-completion-program-implementation.md docs/plans/*.md
git commit -m "docs: finalize product completion program status (docs/plans/2026-03-10-product-completion-program-implementation.md task: Run full reset-based verification, update the plan records, and prepare handoff) | opencode | gpt-5.1-codex-max"
```

## Notes

- This plan is intentionally roadmap-first. Each implementation slice should create its own design and implementation pair before code changes begin.
- If a child slice is already sufficiently planned in an existing document, update that document to align with this master program rather than rewriting it unnecessarily.
- Keep tasks small, test-backed, and vertically integrated.
