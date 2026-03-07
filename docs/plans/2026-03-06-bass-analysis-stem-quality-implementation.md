# Bass Analysis Stem Quality Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a dedicated transcription-focused bass analysis stem path, fix Demucs model resolution so `.env` applies at runtime, and route the refined analysis stem into MIDI/tab generation without changing playback stem behavior.

**Architecture:** Keep Demucs separation for persisted stems unchanged, but add runtime-loaded stem analysis config plus an analysis artifact builder that can refine and score candidate bass stems for transcription suitability. Thread the chosen analysis stem and compact diagnostics through the backend processing flow and MIDI fallback path while preserving existing API contracts and persisted user-facing stems.

**Tech Stack:** FastAPI, Python backend services, ffmpeg, numpy/librosa/scipy, pytest.

---

### Task 1: Create and checkpoint the implementation plan

**Files:**
- Create: `docs/plans/2026-03-06-bass-analysis-stem-quality-implementation.md`

- [x] Step 1: Add the new implementation plan file under `docs/plans/`.
- [x] Step 2: Review the current stem/main/midi/test flow and align task scopes with repo conventions.
- [x] Step 3: Commit the new plan file with the plan path in the commit message.

### Task 2: Add RED tests for runtime model resolution and analysis stem routing

**Files:**
- Modify: `backend/tests/test_stems.py`
- Modify: `backend/tests/test_api.py`
- Modify: `backend/tests/test_tab_pipeline.py`

- [x] Step 1: Add failing tests proving Demucs model selection is resolved at runtime after `.env` loading.
- [x] Step 2: Add failing tests proving the model name is not frozen at import time and invalid env values fall back safely.
- [x] Step 3: Add failing tests proving the main processing flow routes an analysis bass stem into tab generation instead of raw `bass.wav`.
- [x] Step 4: Run targeted tests and confirm RED.
- [x] Step 5: Commit.

### Task 3: Implement runtime Demucs config resolution and typed analysis config

**Files:**
- Modify: `backend/app/stems.py`
- Modify: `backend/tests/test_stems.py`

- [x] Step 1: Add runtime env loading helpers for Demucs model and fallback model selection.
- [x] Step 2: Extend typed stem config parsing with analysis/refinement settings and safe fallback warnings.
- [x] Step 3: Log effective runtime model/config clearly and preserve default behavior when analysis features are disabled.
- [x] Step 4: Run targeted stem tests and confirm GREEN for config behavior.
- [x] Step 5: Commit.

### Task 4: Add deterministic bass analysis refinement and diagnostics

**Files:**
- Modify: `backend/app/stems.py`
- Modify: `backend/tests/test_stems.py`

- [x] Step 1: Add a pure analysis-stem refinement path that produces `bass_analysis.wav` from separated stems while leaving playback stems unchanged.
- [x] Step 2: Implement deterministic preprocessing for the analysis path: mono, resample, high-pass, low-pass, optional bleed subtraction, optional gentle gating.
- [x] Step 3: Add compact serializable diagnostics describing selected model, filters, candidate scores, and refinement actions.
- [x] Step 4: Run targeted stem tests and confirm GREEN for refinement output and diagnostics.
- [x] Step 5: Commit.

### Task 5: Route the analysis stem into tab and MIDI generation

**Files:**
- Modify: `backend/app/main.py`
- Modify: `backend/app/midi.py`
- Modify: `backend/tests/test_api.py`
- Modify: `backend/tests/test_midi.py`

- [x] Step 1: Update the analysis/stems processing flow to create and retain an explicit analysis artifact lifecycle.
- [x] Step 2: Route the refined analysis bass stem into `TabPipeline` and MIDI persistence while keeping persisted playback stems unchanged.
- [x] Step 3: Improve fallback MIDI preprocessing to use the refined analysis path or equivalent bass-focused preprocessing before monophonic estimation.
- [x] Step 4: Run targeted API and MIDI tests and confirm GREEN.
- [x] Step 5: Commit.

### Task 6: Add candidate-model experimentation scaffolding and deterministic scoring

**Files:**
- Modify: `backend/app/stems.py`
- Modify: `backend/tests/test_stems.py`

- [x] Step 1: Add typed parsing for candidate models and ensemble enablement.
- [x] Step 2: Implement deterministic transcription-suitability scoring and best-candidate selection with graceful degradation when alternate models are unavailable.
- [x] Step 3: Add tests covering deterministic candidate parsing/scoring behavior.
- [x] Step 4: Run targeted stem tests and confirm GREEN.
- [x] Step 5: Commit.

### Task 7: Add docs and diagnostics surface updates

**Files:**
- Modify: `README.md`
- Modify: `docs/plans/2026-03-06-bass-analysis-stem-quality-implementation.md`

- [x] Step 1: Document the new env/config knobs for bass analysis stem quality tuning.
- [x] Step 2: Ensure the plan file reflects completed implementation tasks accurately.
- [x] Step 3: Commit.

### Task 8: Verify, reset, and finalize

**Files:**
- Modify: `docs/plans/2026-03-06-bass-analysis-stem-quality-implementation.md`

- [x] Step 1: Run targeted backend tests for stems, MIDI, API, and tab pipeline.
- [x] Step 2: Run broader relevant backend tests.
- [x] Step 3: Run `make reset`.
- [x] Step 4: Re-run critical verification after reset.
- [x] Step 5: Mark all plan steps complete.
- [ ] Step 6: Commit.
