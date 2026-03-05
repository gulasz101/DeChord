# Tab Quality Improvement — Agent Handoff Document

**Date:** 2026-03-05
**Status:** Partially implemented, needs continuation
**Previous agent session:** Completed 10 of 13 planned tasks, got stuck on evaluation due to memory issues

---

## 1. WHAT WE ARE BUILDING

The DeChord app generates bass guitar tablature from audio files. The current pipeline:

```
MP3 → Demucs (stem separation) → bass.wav + drums.wav
  → MIDI transcription (librosa pyin) → note cleanup → quantization → fingering (DP) → AlphaTeX export
```

The goal is to **improve the quality of generated bass tabs** so they match professional transcriptions. We have two reference songs with Guitar Pro 5 (GP5) files as ground truth:

| Song | BPM | GP5 Reference | Stems Cached? |
|------|-----|---------------|---------------|
| Muse - Hysteria | 94 | `test songs/Muse - Hysteria.gp5` | YES (bass.wav + drums.wav) |
| Iron Maiden - The Trooper | 162 | `test songs/Iron Maiden - The Trooper.gp5` (encoding=latin1) | NO |

## 2. WHAT WAS ACCOMPLISHED (10 tasks done)

### Comparison Harness (Tasks 1-5) — ALL DONE
- **`backend/app/services/gp5_reference.py`** — Parses GP5 files, extracts bass track into `ReferenceNote` dataclass
- **`backend/app/services/tab_comparator.py`** — Compares reference vs generated notes, computes F1/precision/recall/pitch/fingering accuracy
- **`backend/app/services/tab_report.py`** — Generates Markdown comparison reports
- **`backend/scripts/evaluate_tab_quality.py`** — Full evaluation script (uses demucs.api for stems)
- **`backend/scripts/quick_eval.py`** — Lightweight eval that avoids madmom (see problems below)
- **`TabPipelineResult`** now exposes `fingered_notes` field for direct comparison

### Pipeline Improvements (Tasks 6-10) — ALL DONE
- **Task 6: Librosa transcription** — Replaced crude STFT fallback in `backend/app/midi.py` with `librosa.pyin()` + `librosa.onset.onset_detect()` for much better pitch and timing detection
- **Task 7: Onset recovery** — Created `backend/app/services/onset_recovery.py` — splits long notes at detected onset times to recover repeated same-pitch notes
- **Task 9: BPM-adaptive cleanup** — Added `cleanup_params_for_bpm()` to `backend/app/services/note_cleanup.py`
- **Task 10: AlphaTeX improvements** — Added dotted note support (`4d`, `8d`, etc.) and gap-filling rests to `backend/app/services/alphatex_exporter.py`

### Baseline Metrics (measured BEFORE librosa pyin improvement was applied)

These were measured using the OLD STFT transcription, so they represent the baseline to beat:

| Song | F1 | Precision | Recall | Pitch Acc | Fingering Acc | Ref Notes | Gen Notes |
|------|-----|-----------|--------|-----------|---------------|-----------|-----------|
| Hysteria | 48.18% | 82.31% | 34.06% | 8.99% | 3.95% | 1339 | 554 |
| Trooper | 30.11% | 52.37% | 21.12% | 2.34% | 0.00% | 1619 | 653 |

**These metrics are terrible.** Especially pitch accuracy (9% and 2%). The new librosa pyin transcription should dramatically improve these but was never measured because of the problems below.

## 3. WHAT WENT WRONG — CRITICAL ISSUES TO AVOID

### Problem 1: madmom eats 12GB+ RAM and hangs forever

The `TabPipeline` imports `rhythm_grid.py` which imports `madmom` at function level. When `madmom.features.downbeats.RNNDownBeatProcessor` is called, it loads ~12GB of neural network models into RAM. On this machine, this causes the process to either:
- Run for 30+ minutes and then get OOM-killed (exit code 137)
- Appear to hang while madmom processes

**SOLUTION: You MUST bypass madmom for evaluation.** Use the `quick_eval.py` script approach:
- Import pipeline stages individually (NOT `TabPipeline` which triggers madmom import chain)
- Use `librosa.beat.beat_track()` for rhythm extraction instead of madmom
- Call `_estimate_monophonic_notes_from_wav()` directly from `app.midi` instead of going through `BasicPitchTranscriber` → `transcribe_bass_stem_to_midi`

The `quick_eval.py` script at `backend/scripts/quick_eval.py` was written to do this but it ALSO hit the memory issue because `BasicPitchTranscriber` internally calls `app.midi.transcribe_bass_stem_to_midi` which runs `_transcribe_with_frequency_fallback` → ffmpeg → `_estimate_monophonic_notes_from_wav`. The ffmpeg subprocess + wav conversion adds overhead.

**THE CORRECT APPROACH for evaluation:**
```python
# DO NOT import TabPipeline or anything from rhythm_grid
# DO NOT use BasicPitchTranscriber (it calls transcribe_bass_stem_to_midi which adds ffmpeg overhead)

# Instead, call the transcription function directly:
from app.midi import _estimate_monophonic_notes_from_wav
events = _estimate_monophonic_notes_from_wav(Path('bass.wav'))
# events is list of (start_sec, end_sec, midi_note) tuples

# Convert to RawNoteEvent manually:
from app.services.bass_transcriber import RawNoteEvent
raw_notes = [RawNoteEvent(pitch_midi=e[2], start_sec=e[0], end_sec=e[1], confidence=1.0) for e in events]

# Then use cleanup, quantization, fingering directly (these are lightweight)
# For rhythm, use librosa directly:
import librosa
y, sr = librosa.load('drums.wav', sr=None, mono=True)
_tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
beats = [float(t) for t in librosa.frames_to_time(beat_frames, sr=sr)]
```

**Memory benchmarks:**
- `librosa.pyin()` with `hop_length=1024` on 226s audio: **678MB, 6 seconds**
- `librosa.pyin()` with default `hop_length=512`: **much more, 30+ seconds**
- madmom RNNDownBeatProcessor: **12GB+, 30+ minutes**
- All pipeline module imports (without madmom): **38MB**

### Problem 2: BasicPitch cannot be installed

BasicPitch requires TensorFlow which doesn't support Python 3.14. The `pyproject.toml` guards it with `python_version < '3.14'`. The frequency fallback path is what runs instead. We already replaced it with librosa pyin (Task 6), so this is no longer a blocker — just don't try to install BasicPitch.

### Problem 3: Demucs stem separation is slow but works

Demucs runs fine via `demucs.api` in the Python 3.14 main venv. It takes ~2 minutes per song on MPS (Apple Silicon GPU). Stems for Hysteria are already cached at `backend/stems/test_songs/Muse__Hysteria/`. The Trooper stems still need to be generated.

**To generate Trooper stems**, you can run:
```python
import demucs.api
separator = demucs.api.Separator(model="htdemucs_ft", device="mps")
origin, separated = separator.separate_audio_file("test songs/Iron Maiden - The Trooper.mp3")
# Then save separated["bass"] and separated["drums"] as WAV files
```

### Problem 4: The Trooper GP5 needs encoding='latin1'

```python
parse_gp5_bass_track(Path("test songs/Iron Maiden - The Trooper.gp5"), encoding="latin1")
```

## 4. CURRENT STATE OF FILES

### Pipeline service modules (all in `backend/app/services/`):
| File | Status | Description |
|------|--------|-------------|
| `tab_pipeline.py` | Working but uses madmom | Orchestrates full pipeline. Has `fingered_notes` field. |
| `bass_transcriber.py` | Working | `BasicPitchTranscriber` wraps `app.midi` |
| `rhythm_grid.py` | Working but madmom-heavy | Beat/downbeat extraction |
| `note_cleanup.py` | Improved | Has `cleanup_params_for_bpm()` and octave correction |
| `quantization.py` | Working | Snaps notes to bar grid, 16th subdivision |
| `fingering.py` | Working | DP solver for string/fret assignment |
| `alphatex_exporter.py` | Improved | Dotted notes + gap-filling rests |
| `onset_recovery.py` | NEW, not integrated | Splits long notes at onset times |
| `gp5_reference.py` | NEW | Parses GP5 bass tracks |
| `tab_comparator.py` | NEW | Comparison metrics |
| `tab_report.py` | NEW | Markdown report generator |

### Key file: `backend/app/midi.py`
- `_estimate_monophonic_notes_from_wav()` — NOW uses librosa pyin+onset (was STFT)
- `_transcribe_with_frequency_fallback()` — Converts to WAV via ffmpeg, calls above
- `transcribe_bass_stem_to_midi()` — Entry point, tries BasicPitch first, falls back to above
- Has `hop_length=1024` already set for pyin

### Test files (all in `backend/tests/`):
All 105 tests pass. Key test files for this work:
- `test_gp5_reference.py` (3 tests)
- `test_tab_comparator.py` (6 tests)
- `test_tab_report.py` (2 tests)
- `test_onset_recovery.py` (5 tests — but module not yet integrated into pipeline)
- `test_midi.py` (8 tests including new librosa transcription tests)
- `test_note_cleanup.py` (8 tests including BPM-adaptive)
- `test_alphatex_exporter.py` (5 tests including dotted notes)

### Cached stems:
- `backend/stems/test_songs/Muse__Hysteria/bass.wav` (19MB, 226.6s)
- `backend/stems/test_songs/Muse__Hysteria/drums.wav` (19MB, 226.6s)
- Iron Maiden - The Trooper: NOT YET CACHED

### Reference data from GP5:
- Hysteria: 1339 reference notes, 87 bars, tempo=94, 4/4, all 16th notes, bass track at index 3
- Trooper: 1619 reference notes, 176 bars, tempo=162, 4/4, mix of 8th and 16th notes, track index 0 (only track)

## 5. REMAINING TASKS

### Task A: Run Post-Improvement Evaluation on Hysteria (CRITICAL FIRST STEP)

**Goal:** Measure how much the librosa pyin transcription improved quality vs the baseline.

**IMPORTANT: Avoid madmom.** Do NOT import `TabPipeline` or `rhythm_grid`. Use the direct approach.

**Files:** Create `backend/scripts/eval_no_madmom.py`

**Algorithm:**
1. Load bass.wav from cached stems
2. Call `_estimate_monophonic_notes_from_wav(bass_wav)` directly — this uses the new librosa pyin
3. Convert returned tuples to `RawNoteEvent` objects
4. Run `cleanup_note_events()` with `apply_octave_correction=True`
5. Load drums.wav, run `librosa.beat.beat_track()` for beats
6. Build `Bar` and `BarGrid` objects manually (see `quick_eval.py` for example)
7. Run `quantize_note_events()`
8. Run `optimize_fingering_with_debug()`
9. Parse GP5 reference with `parse_gp5_bass_track()`
10. Compare with `compare_tabs()`
11. Generate report with `generate_comparison_report()`
12. Print results and save to `docs/reports/`

**Expected:** Should run in under 30 seconds. Memory should stay under 1GB.

**Success criteria:** Pitch accuracy should be significantly higher than 9% baseline. If not, the pyin parameters need tuning.

### Task B: Generate Trooper Stems

**Goal:** Run Demucs on Iron Maiden - The Trooper to get bass.wav and drums.wav.

**Algorithm:**
```python
import demucs.api
import scipy.io.wavfile as wavfile
import numpy as np

separator = demucs.api.Separator(model="htdemucs_ft", device="mps")
origin, separated = separator.separate_audio_file("test songs/Iron Maiden - The Trooper.mp3")

for stem_name in ["bass", "drums"]:
    tensor = separated[stem_name]
    if tensor.dim() == 2:
        audio = tensor.cpu().numpy()
    else:
        audio = tensor.squeeze(0).cpu().numpy()
    if audio.ndim == 2 and audio.shape[0] <= 4:
        audio = audio.mean(axis=0)
    int16 = (audio * 32767).clip(-32768, 32767).astype(np.int16)
    output_dir = Path("backend/stems/test_songs/Iron_Maiden__The_Trooper")
    output_dir.mkdir(parents=True, exist_ok=True)
    wavfile.write(str(output_dir / f"{stem_name}.wav"), separator.samplerate, int16)
```

**Expected:** ~2-3 minutes on MPS. Save to `backend/stems/test_songs/Iron_Maiden__The_Trooper/`

### Task C: Run Post-Improvement Evaluation on Trooper

Same as Task A but for The Trooper. Remember `encoding="latin1"` for GP5 parsing.

### Task D: Integrate Onset Recovery into Pipeline (Plan Task 8)

**Goal:** The `onset_recovery.py` module exists but is not wired into the pipeline.

**Files to modify:** `backend/app/services/tab_pipeline.py`

**Changes:**
1. Add `onset_recovery: bool = False` parameter to `TabPipeline.run()`
2. After transcription and before cleanup, if `onset_recovery=True`:
   - Detect onsets on bass stem using `librosa.onset.onset_detect()`
   - Call `recover_missing_onsets(raw_notes, onset_times)` from `onset_recovery.py`
3. Add `onset_recovery_applied` to debug_info
4. Add test in `test_tab_pipeline.py`

**Also:** Update `quick_eval.py` / `eval_no_madmom.py` to use onset recovery.

### Task E: Integrate BPM-Adaptive Cleanup into Pipeline

**Goal:** The `cleanup_params_for_bpm()` function exists but the pipeline doesn't use it.

**Changes to `tab_pipeline.py`:**
- In `run()`, after tempo is determined, call `cleanup_params_for_bpm(tempo_used)`
- Pass those params to `self._cleanup_fn()` instead of defaults

**Also:** Update eval script to use it.

### Task F: Iterative Quality Tuning

Based on Task A/C results, identify the worst-performing areas and tune:

1. **If pitch accuracy is still low:** Tune pyin parameters (fmin, fmax, hop_length), try smaller hop for more accuracy (but watch memory)
2. **If note density (recall) is low:** Lower cleanup thresholds, use onset recovery to split merged notes
3. **If timing is off:** Adjust quantization grid, try different subdivision values
4. **If fingering doesn't match:** Tune DP transition costs in `fingering.py`

For each tuning:
- Change parameters
- Re-run eval script
- Compare metrics before/after
- Commit when improved

### Task G: Update Plan File and Final Verification

1. Update `docs/plans/2026-03-05-tab-quality-improvement-implementation.md` with completion checkboxes
2. Run `make reset`
3. Run `uv run pytest tests/ -v` — all 105+ tests must pass
4. Run final evaluation on both songs
5. Commit final metrics

## 6. KEY ARCHITECTURAL DECISIONS

- **AlphaTeX format** is the primary tab output (not GP5)
- **Standard bass tuning:** E1=28, A1=33, D2=38, G2=43 (MIDI values)
- **Quantization grid:** 16th note subdivision (configurable)
- **Fingering:** Dynamic programming with transition cost function
- **Sync points:** Every 8 bars in AlphaTeX for playback sync
- **All data classes are frozen** (immutable)
- **Pipeline is injectable** — all functions can be overridden via constructor

## 7. TEST COMMAND

```bash
cd /Users/wojciechgula/Projects/DeChord/backend && uv run pytest tests/ -v
```

All 105 tests should pass. Run this before and after any changes.

## 8. GIT CONVENTIONS

- Every commit must reference the plan file path
- Format: `type(scope): description (docs/plans/2026-03-05-tab-quality-improvement-implementation.md)`
- Task completion tracked with `[x]` checkboxes in plan file
