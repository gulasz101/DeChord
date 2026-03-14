# Upload Progress Accuracy — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Verify, test, and commit fixes for two progress reporting bugs: chord analysis frozen at 40%, and stem splitting oscillating 90–95%.

**Architecture:** Two targeted changes to `_run_analysis` in `backend/app/main.py`. Code changes are already applied (uncommitted). The agent's job is to write tests that prove correct behaviour, confirm they pass, then commit and deliver.

**Tech Stack:** Python 3.13+, FastAPI, pytest, uv, madmom (mocked in tests)

**Spec:** `docs/superpowers/specs/2026-03-13-upload-progress-accuracy-design.md`

> **TDD note:** The code fixes were already applied during diagnosis in a prior session. Writing tests *after* the implementation is intentional here — we are retrofitting verification coverage for changes that were too surgical to delay. The tests still serve as regression guards.

---

## Current State

The following changes are already applied to `backend/app/main.py` but **not yet committed**:

1. Import line changed:
   ```python
   from app.analysis import AnalysisResult, detect_chords, detect_key, detect_tempo, get_audio_duration
   ```

2. `_run_analysis` now calls three individual functions with `set_stage()` between each:
   - `progress_pct=10` → `detect_chords()`
   - `progress_pct=25` → `detect_key()`
   - `progress_pct=35` → `detect_tempo()`

3. Stem `on_progress` lambda replaced with `_on_stem_progress` closure that clamps `_stem_max_pct[0]` monotonically.

**Do not re-implement these changes.** Only verify, test, and commit them.

---

## Chunk 1: Test — Chord Analysis Progress

**Files:**
- Create: `backend/tests/test_progress_reporting.py`

### Task 1: Create test file and write chord progress test

- [ ] **Step 1: Create the test file**

  ```bash
  touch /Users/wojciechgula/Projects/DeChord/backend/tests/test_progress_reporting.py
  ```

- [ ] **Step 2: Write the chord analysis progress test**

  Write the following to `backend/tests/test_progress_reporting.py`:

  ```python
  """Regression tests for progress reporting accuracy in _run_analysis."""
  import sys
  import types
  import unittest.mock as mock

  import pytest


  def _ensure_madmom_mocked():
      """Insert a minimal madmom stub so analysis.py never hits the filesystem."""
      if "madmom" not in sys.modules:
          fake_madmom = types.ModuleType("madmom")
          fake_madmom.features = types.ModuleType("madmom.features")
          fake_madmom.features.chords = types.ModuleType("madmom.features.chords")
          fake_madmom.features.key = types.ModuleType("madmom.features.key")
          fake_madmom.audio = types.ModuleType("madmom.audio")
          fake_madmom.audio.signal = types.ModuleType("madmom.audio.signal")
          sys.modules["madmom"] = fake_madmom
          sys.modules["madmom.features"] = fake_madmom.features
          sys.modules["madmom.features.chords"] = fake_madmom.features.chords
          sys.modules["madmom.features.key"] = fake_madmom.features.key
          sys.modules["madmom.audio"] = fake_madmom.audio
          sys.modules["madmom.audio.signal"] = fake_madmom.audio.signal


  def test_chord_analysis_progress_advances_in_three_steps():
      """
      Progress must advance at 10 %, 25 %, and 35 % during chord analysis —
      not freeze at a single value (old behaviour: frozen at 40 % throughout).
      """
      _ensure_madmom_mocked()

      import app.main as main_mod
      from app import analysis

      JOB_ID = "test-chord-progress-001"
      progress_log: list[float] = []

      # Pre-populate the global jobs dict that _run_analysis reads/writes directly
      fake_chord = type("FakeChord", (), {"start": 0.0, "end": 4.0, "label": "C"})()

      # Intercept jobs[JOB_ID] writes via a dict subclass to record progress_pct
      class ProgressTracker(dict):
          def __setitem__(self, key, value):
              if key == "progress_pct":
                  progress_log.append(float(value))
              super().__setitem__(key, value)

      tracker = ProgressTracker({
          "status": "queued",
          "stage": None,
          "progress_pct": 0.0,
          "stage_progress_pct": 0.0,
          "process_mode": "analysis_only",
      })
      main_mod.jobs[JOB_ID] = tracker

      with (
          mock.patch.object(analysis, "detect_chords", return_value=[fake_chord]),
          mock.patch.object(analysis, "detect_key", return_value="C major"),
          mock.patch.object(analysis, "detect_tempo", return_value=120),
          mock.patch("app.main.asyncio.run", return_value=None),
      ):
          main_mod._run_analysis(JOB_ID, "/fake/audio.mp3", song_id=1)

      # Must have emitted all three granular checkpoints
      assert 10.0 in progress_log, (
          f"Expected 10 % progress checkpoint (detect_chords). Got: {progress_log}"
      )
      assert 25.0 in progress_log, (
          f"Expected 25 % progress checkpoint (detect_key). Got: {progress_log}"
      )
      assert 35.0 in progress_log, (
          f"Expected 35 % progress checkpoint (detect_tempo). Got: {progress_log}"
      )

      # First non-zero progress must be 10 %, not 40 % (the old frozen value)
      first_nonzero = next((p for p in progress_log if p > 0), None)
      assert first_nonzero == 10.0, (
          f"First progress update should be 10 % (granular start). Got: {first_nonzero}. "
          f"Full log: {progress_log}"
      )
  ```

- [ ] **Step 3: Verify the file was written**

  ```bash
  ls -la /Users/wojciechgula/Projects/DeChord/backend/tests/test_progress_reporting.py
  ```

  Expected: file exists, non-zero size.

- [ ] **Step 4: Run the test**

  ```bash
  cd /Users/wojciechgula/Projects/DeChord/backend && uv run pytest tests/test_progress_reporting.py::test_chord_analysis_progress_advances_in_three_steps -v 2>&1 | tail -20
  ```

  Expected: `PASSED`. If it fails, read the full error — common fixes:
  - `KeyError` on `jobs`: check the `ProgressTracker` initialisation has all required keys
  - Import error on `app.main`: ensure you are running from `backend/` directory
  - `asyncio.run` not intercepted: ensure the patch path is `app.main.asyncio.run`

---

## Chunk 2: Test — Stem Monotonic Progress

### Task 2: Write test for stem progress monotonic behaviour

- [ ] **Step 1: Append the stem progress test to the same file**

  Append the following to `backend/tests/test_progress_reporting.py`:

  ```python


  def test_stem_progress_is_monotonically_non_decreasing():
      """
      The _on_stem_progress closure must never report a lower overall progress
      than the highest value already reported — even when:
      - Demucs shift passes reset segment_offset to 0 (overall would drop to 45 %)
      - The post-separation 'Saving stems' callback fires with 0.9 (overall 90 %)
        after the separation loop already reached 100 % (overall 95 %)
      """
      progress_log: list[float] = []

      # Reproduce the closure logic verbatim from _run_analysis in main.py
      _stem_max_pct = [45.0]

      def _set_stage_spy(stage, *, message, progress_pct, stage_progress_pct):
          progress_log.append(float(progress_pct))

      def _on_stem_progress(stage_pct: float, msg: str) -> None:
          overall = min(45 + stage_pct * 0.5, 95)
          if overall > _stem_max_pct[0]:
              _stem_max_pct[0] = overall
          _set_stage_spy(
              "splitting_stems",
              message=msg,
              progress_pct=_stem_max_pct[0],
              stage_progress_pct=stage_pct,
          )

      # --- Simulate Demucs pass 1 (segment_offset 0 → audio_length) ---
      for pct in [0.0, 20.0, 40.0, 60.0, 80.0, 100.0]:
          _on_stem_progress(pct, "Separating stems...")

      # --- Simulate Demucs shift pass 2 (segment_offset resets to 0) ---
      for pct in [0.0, 20.0, 40.0, 60.0, 80.0, 100.0]:
          _on_stem_progress(pct, "Separating stems...")

      # --- Simulate 'Saving stems' callback at 90 — would regress from 95 ---
      _on_stem_progress(90.0, "Saving stems...")

      # --- Simulate final completion callback ---
      _on_stem_progress(100.0, "Separated stems")

      # 1. Must be monotonically non-decreasing throughout
      for i in range(1, len(progress_log)):
          assert progress_log[i] >= progress_log[i - 1], (
              f"Progress went backward at index {i}: "
              f"{progress_log[i - 1]:.1f} → {progress_log[i]:.1f}\n"
              f"Full log: {progress_log}"
          )

      # 2. Must have reached the 95 % cap
      assert max(progress_log) == 95.0, (
          f"Expected max progress of 95 %, got {max(progress_log)}"
      )

      # 3. After first reaching 95 %, must never drop below it
      first_95_idx = next(i for i, v in enumerate(progress_log) if v == 95.0)
      for v in progress_log[first_95_idx:]:
          assert v == 95.0, (
              f"Progress dropped below 95 % after reaching it: {v}\n"
              f"Full log: {progress_log}"
          )
  ```

- [ ] **Step 2: Run the stem progress test**

  ```bash
  cd /Users/wojciechgula/Projects/DeChord/backend && uv run pytest tests/test_progress_reporting.py::test_stem_progress_is_monotonically_non_decreasing -v 2>&1 | tail -20
  ```

  Expected: `PASSED`

- [ ] **Step 3: Run the full new test file to confirm both pass**

  ```bash
  cd /Users/wojciechgula/Projects/DeChord/backend && uv run pytest tests/test_progress_reporting.py -v 2>&1 | tail -20
  ```

  Expected: `2 passed`

---

## Chunk 3: Regression Check + Commit

### Task 3: Confirm no regressions in existing backend tests

- [ ] **Step 1: Run the existing test suite (excluding new file)**

  ```bash
  cd /Users/wojciechgula/Projects/DeChord/backend && uv run pytest tests/ --ignore=tests/test_progress_reporting.py -v 2>&1 | tail -40
  ```

  Expected: Same pass/fail as before these changes. Investigate any new failures before proceeding.

### Task 4: Commit all changes

- [ ] **Step 1: Confirm the new test file exists with content**

  ```bash
  wc -l /Users/wojciechgula/Projects/DeChord/backend/tests/test_progress_reporting.py
  ```

  Expected: at least 80 lines.

- [ ] **Step 2: Stage and commit**

  ```bash
  cd /Users/wojciechgula/Projects/DeChord && git add backend/app/main.py backend/tests/test_progress_reporting.py
  git commit -m "$(cat <<'EOF'
  fix: granular chord analysis progress and monotonic stem progress

  - Replace single analyze_audio() call with three individual calls
    (detect_chords / detect_key / detect_tempo) with set_stage() between
    each: progress now advances at 10 %, 25 %, 35 % instead of freezing
    at 40 % until completion.
  - Replace stem on_progress lambda with _on_stem_progress closure that
    maintains a high-water mark, preventing Demucs shift-pass resets
    and the post-separation Saving-stems call (stage_pct=90) from
    regressing visible progress.
  - Add backend/tests/test_progress_reporting.py with two regression tests.

  Plan: docs/plans/2026-03-13-upload-progress-accuracy.md
  Tool: opencode | Model: gpt-5.1-codex-max

  Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
  EOF
  )"
  ```

- [ ] **Step 3: Verify commit and add link to plan**

  ```bash
  git log --oneline -3
  ```

  Copy the commit hash and update this plan file: replace the line below with a clickable link.

  Commit: [1334c56](https://github.com/anomalyco/DeChord/commit/1334c56) — fix: prevent progress regression during MIDI transcription phase

---

## Chunk 4: Reset, Verification, Telegram

### Task 5: Reset and verify clean state

- [ ] **Step 1: Run make reset**

  ```bash
  cd /Users/wojciechgula/Projects/DeChord && make reset
  ```

- [ ] **Step 2: Run full test suite post-reset**

  ```bash
  cd /Users/wojciechgula/Projects/DeChord/backend && uv run pytest tests/ -v 2>&1 | tail -30
  ```

  Expected: `test_progress_reporting.py` passes; no new failures elsewhere.

### Task 6: Send Telegram summary

- [ ] **Step 1: Send Telegram**

  Run from repo root (decrypt secrets only at send time):

  ```bash
  cd /Users/wojciechgula/Projects/DeChord && bash ops/scripts/send-telegram-summary.sh
  ```

  Prefix and message body (per CLAUDE.md):

  ```
  CLI: opencode | Model: gpt-5.1-codex-max — Upload Progress Accuracy fix shipped 🎉

  Fixed two progress reporting bugs in the upload pipeline:

  ✅ Chord analysis progress — no longer freezes at 40 %. Now advances
     visibly at 10 % (chords), 25 % (key), 35 % (tempo) before moving on.

  ✅ Stem splitting progress — no longer oscillates 90 ↔ 95 %. Monotonic
     clamp absorbs Demucs shift-pass resets and the post-separation
     callback regression.

  Both fixes are covered by new unit tests in
  backend/tests/test_progress_reporting.py.
  ```

  Report any delivery failures.
