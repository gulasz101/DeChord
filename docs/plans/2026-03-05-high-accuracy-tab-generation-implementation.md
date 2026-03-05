# High Accuracy Tab Generation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add an optional high-accuracy tab generation mode that re-analyzes suspect silent bars and expose it in upload advanced settings while keeping default behavior unchanged.

**Architecture:** Extend upload API and job metadata to carry `tabGenerationQuality`, plumb it into `TabPipeline.run` as `tab_generation_quality_mode`, and implement a second-pass suspect-silence analysis in the pipeline using per-bar RMS plus per-bar note counts. Update frontend upload UI/API payload and add targeted backend/frontend tests. Keep quantization/fingering/chord/BPM logic unchanged outside this gating mode.

**Tech Stack:** FastAPI, Python services (`tab_pipeline`), pytest, React/TypeScript, Vitest.

---

### Task 1: Add failing backend tests for quality mode + suspect silence behavior

**Files:**
- Modify: `backend/tests/test_tab_pipeline.py`

- [x] Step 1: Add failing test for suspect silence trigger in `high_accuracy` mode (detect + second pass + notes added).
- [x] Step 2: Add failing test for no false trigger when bar RMS is low.
- [x] Step 3: Run targeted tests and confirm RED.
- [x] Step 4: Commit.

### Task 2: Implement pipeline quality mode and suspect-silence reanalysis

**Files:**
- Modify: `backend/app/services/tab_pipeline.py`
- Modify: `backend/app/services/bass_transcriber.py`

- [x] Step 1: Add `tab_generation_quality_mode: Literal["standard", "high_accuracy"] = "standard"` to pipeline run API.
- [x] Step 2: Implement suspect silence detection (`notes_per_bar == 0` and `bar_rms >= median_bar_rms * 0.9`) after first quantization.
- [x] Step 3: Re-run transcription on per-bar windows (`start-0.2s`, `end+0.2s`), merge notes, re-run cleanup+quantization.
- [x] Step 4: Add diagnostics (`suspect_silence_bars_count`, `suspect_bars`, `notes_added_second_pass`, `notes_per_bar_before_high_accuracy`, `notes_per_bar_after_high_accuracy`) into debug output when mode is high accuracy.
- [x] Step 5: Run targeted tests and confirm GREEN.
- [x] Step 6: Commit.

### Task 3: Add upload API field and persist quality mode in job metadata

**Files:**
- Modify: `backend/app/main.py`
- Modify: `backend/tests/test_api.py`

- [x] Step 1: Add failing API test: upload without quality mode defaults to `standard` in pipeline call.
- [x] Step 2: Add failing API test: upload with `tabGenerationQuality=high_accuracy` forwards mode to pipeline.
- [x] Step 3: Implement optional form field parsing/default and pass mode to `tab_pipeline.run`.
- [x] Step 4: Ensure mode is persisted in in-memory job metadata.
- [x] Step 5: Run targeted API tests and confirm GREEN.
- [x] Step 6: Commit.

### Task 4: Add frontend advanced upload setting and API payload

**Files:**
- Modify: `frontend/src/lib/types.ts`
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/components/SongLibraryPanel.tsx`
- Modify: `frontend/src/components/DropZone.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/lib/__tests__/api.stems-status.test.ts`
- Modify: `frontend/src/components/__tests__/DropZoneUploadMode.test.tsx`

- [x] Step 1: Add failing frontend tests for new field payload and advanced text rendering.
- [x] Step 2: Implement `Tab accuracy` advanced radio options and helper text (exact copy).
- [x] Step 3: Wire selected mode through app and upload API payload (`tabGenerationQuality`).
- [x] Step 4: Run targeted frontend tests and confirm GREEN.
- [x] Step 5: Commit.

### Task 5: Verification, reset workflow, Clara Luciani run, and report updates

**Files:**
- Modify: `docs/plans/2026-03-05-high-accuracy-tab-generation-implementation.md`
- Optional report outputs only if generated in this run.

- [ ] Step 1: Run backend and frontend targeted/full relevant tests.
- [ ] Step 2: Run `make reset` before final verification/handoff.
- [ ] Step 3: Re-run critical tests post-reset.
- [ ] Step 4: Run pipeline on Clara Luciani track and capture requested before/after metrics.
- [ ] Step 5: Mark all completed checkboxes `[x]`.
- [ ] Step 6: Commit.
