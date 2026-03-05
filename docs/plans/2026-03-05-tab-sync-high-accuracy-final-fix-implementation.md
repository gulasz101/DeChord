# Tab Sync + High Accuracy Final Fix Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement aggressive suspect-silence recovery, beat-grid metrical correction, and robust sync anchoring so tabs remain aligned to full track duration.

**Architecture:** Extend `TabPipeline` and alphaTex export helpers to correct rhythm-grid metrical mismatches against canonical BPM, add `high_accuracy_aggressive` local-RMS/onset suspect detection, and enforce end-of-track sync coverage by extending bars when needed. Wire new quality mode through backend API and frontend upload settings.

**Tech Stack:** Python (FastAPI, pytest), TypeScript/React (Vitest), librosa optional runtime.

---

### Task 1: Add failing backend tests for beat-grid correction and aggressive suspect silence

**Files:**
- Modify: `backend/tests/test_tab_pipeline.py`

- [ ] Step 1: Add failing test for double-time beat grid correction versus `song_bpm`/`bpm_hint` and assert corrected BPM + last sync proximity to audio duration.
- [ ] Step 2: Add failing test where `high_accuracy_aggressive` triggers on onset peaks in low-RMS empty bar and adds notes while `high_accuracy` does not.
- [ ] Step 3: Run targeted backend tests and confirm RED.
- [ ] Step 4: Commit with message referencing this plan path.

### Task 2: Implement backend pipeline logic for correction + aggressive mode + diagnostics

**Files:**
- Modify: `backend/app/services/tab_pipeline.py`
- Modify: `backend/app/services/alphatex_exporter.py`
- Modify: `backend/app/services/rhythm_grid.py` (only if helper extraction is cleaner)

- [ ] Step 1: Expand quality literals to include `high_accuracy_aggressive` in pipeline.
- [ ] Step 2: Add beat-grid correction helpers (raw beat BPM estimate, compare with song BPM, apply double/half-time transformation, capture diagnostics).
- [ ] Step 3: Add bar-extension logic to align final bar start within ~one bar of audio duration.
- [ ] Step 4: Add aggressive suspect-silence detection with local median RMS and onset peaks; run high-sensitivity re-pass and merge.
- [ ] Step 5: Recompute cleanup/quantization after second pass and include required diagnostics fields.
- [ ] Step 6: Ensure alphaTex uses canonical song BPM and sync points include periodic + last bar point.
- [ ] Step 7: Run targeted backend tests and confirm GREEN.
- [ ] Step 8: Commit with message referencing this plan path.

### Task 3: Extend backend API and API tests for new quality literal

**Files:**
- Modify: `backend/app/main.py`
- Modify: `backend/tests/test_api.py`

- [ ] Step 1: Add failing API test that `tabGenerationQuality=high_accuracy_aggressive` is accepted and forwarded.
- [ ] Step 2: Update API form literals/typing and forwarding for analyze + tab-from-stems endpoints.
- [ ] Step 3: Keep job metadata persistence of selected mode and verify default remains `standard`.
- [ ] Step 4: Run targeted API tests and confirm GREEN.
- [ ] Step 5: Commit with message referencing this plan path.

### Task 4: Extend frontend advanced settings and payload tests for third mode

**Files:**
- Modify: `frontend/src/lib/types.ts`
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/components/DropZone.tsx`
- Modify: `frontend/src/components/SongLibraryPanel.tsx`
- Modify: `frontend/src/lib/__tests__/api.stems-status.test.ts`
- Modify: `frontend/src/components/__tests__/DropZoneUploadMode.test.tsx`

- [ ] Step 1: Add failing frontend tests for rendering + payload forwarding of `high_accuracy_aggressive`.
- [ ] Step 2: Extend `TabGenerationQuality` type and API upload payload handling.
- [ ] Step 3: Add aggressive option in advanced UI while keeping helper copy intact.
- [ ] Step 4: Run targeted frontend tests and confirm GREEN.
- [ ] Step 5: Commit with message referencing this plan path.

### Task 5: Verification, reset workflow, and La grenade validation run

**Files:**
- Modify: `docs/plans/2026-03-05-tab-sync-high-accuracy-final-fix-implementation.md`
- Modify: `REAL_TRACK_QUALITY_REPORT.md` (or create run-scoped report)

- [ ] Step 1: Run backend + frontend relevant test suites.
- [ ] Step 2: Run `make reset` before final verification/handoff.
- [ ] Step 3: Re-run critical tests post-reset.
- [ ] Step 4: Run La grenade pipeline in `standard` and `high_accuracy_aggressive`, capture diagnostics and alphaTex sync excerpt.
- [ ] Step 5: Mark completed steps as `[x]` in this plan.
- [ ] Step 6: Commit with message referencing this plan path.
