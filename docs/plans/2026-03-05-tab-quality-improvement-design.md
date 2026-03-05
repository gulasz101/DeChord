# Tab Quality Improvement Design — GP5 Comparison Harness + Pipeline Tuning

**Date:** 2026-03-05
**Status:** Approved for implementation planning
**Scope:** Systematic improvement of bass tab generation quality using GP5 reference tabs from The Trooper (Iron Maiden) and Hysteria (Muse) as ground truth.

---

## Goal

Improve the bass tab generation pipeline so output closely matches professional transcriptions in pitch accuracy, rhythmic precision, note density, and fingering quality. Build a permanent comparison harness for quantitative quality measurement.

## Test Songs

| Song | BPM | Style | GP5 Reference |
|------|-----|-------|---------------|
| Iron Maiden - The Trooper | ~160 | Fast galloping 8ths/16ths | `test songs/Iron Maiden - The Trooper.gp5` |
| Muse - Hysteria | ~94 | Dense 16th-note bass riff | `test songs/Muse - Hysteria.gp5` |

## Approved Decisions

- Focus exclusively on The Trooper and Hysteria (both have GP5 reference bass tabs).
- Run Demucs stem separation as part of the test workflow.
- Quality target: full match on pitch + rhythm + fingering.
- Build visual diff output alongside quantitative metrics.
- Improve transcription quality (BasicPitch tuning) in addition to downstream pipeline stages.

---

## Section 1: Comparison Harness Architecture

### GP5 Reference Parser (`backend/app/services/gp5_reference.py`)

- Uses `pyguitarpro` to parse GP5 files.
- Extracts the bass track (finds track with bass tuning E1/A1/D2/G2 or 4-string instrument).
- Converts each measure to a list of reference notes:
  - `(bar_index, beat_position, duration_beats, pitch_midi, string, fret)`
- Returns a `ReferenceTab` dataclass compatible with `FingeredNote` for comparison.
- Handles tied notes, rests, dead notes, and time signature changes.

### Comparison Metrics Module (`backend/app/services/tab_comparator.py`)

Aligns generated notes with reference notes by bar and timing. Computes:

- **Pitch accuracy**: % of generated notes matching reference pitch (within ±1 semitone tolerance).
- **Note density accuracy**: per-bar note count correlation (Pearson R).
- **Timing accuracy**: mean absolute onset offset between matched notes (in beats).
- **Fingering similarity**: % of string/fret matches for pitch-matched notes.
- **F1 score**: precision × recall for note detection.
- **Per-bar breakdown**: all metrics computed per bar for drill-down.

### Visual Diff Report

A Markdown report per song showing:

- Summary metrics table at the top.
- Per-bar comparison table: reference notes | generated notes | pitch match | timing diff | fingering match.
- Sections color-coded via Markdown emphasis: matched, close, missing, extra.
- Aggregate quality score.

### Test Runner Script (`backend/scripts/evaluate_tab_quality.py`)

- Runs Demucs on test MP3s (caches separated stems after first run).
- Runs the full TabPipeline on separated stems.
- Compares generated output against GP5 reference.
- Outputs quality report to `docs/reports/`.

---

## Section 2: Transcription Improvements

### BasicPitch Parameter Tuning

- `predict()` accepts `onset_threshold`, `frame_threshold`, `minimum_note_length`, `minimum_frequency`.
- Lower thresholds to increase recall (capture more notes); cleanup handles false positives.
- Set `minimum_frequency` to bass range (~30 Hz).
- Expose these as parameters through the pipeline.

### Confidence-Weighted Multi-Pass

- First pass: standard thresholds for high-confidence notes.
- Second pass: lower thresholds targeting bars where note density is below expected (extends existing `high_accuracy_aggressive` mode).

### Onset Detection Enhancement

- Use `librosa.onset.onset_detect()` on bass stem to find note attack times independently.
- Cross-reference with BasicPitch output to recover missed note onsets.
- Particularly useful for repeated same-pitch notes (which BasicPitch tends to merge).

### Post-Transcription Pitch Correction

- Use detected key/chords from main analysis to validate transcribed pitches.
- Flag notes outside harmonic context for potential octave/semitone correction.

---

## Section 3: Pipeline Stage Improvements

### Note Cleanup Tuning

- Calibrate `min_duration_sec` against reference note durations (The Trooper 16ths at 160 BPM = ~94ms).
- Enable `apply_octave_correction=True` by default.
- Tune `merge_gap_sec` based on actual note gaps in reference tabs.
- Add adaptive thresholds based on detected BPM.

### Quantization Improvements

- Add dotted note support: dotted-8th (0.75 beats), dotted-quarter (1.5 beats), etc.
- Add tied note support for notes crossing bar boundaries.
- Improve beat position accuracy with finer grid alignment.
- Better handling of notes that fall between grid points.

### AlphaTeX Export Improvements

- Add dotted duration tokens (`8d`, `4d`, `2d`).
- Add tied note output across bar boundaries.
- Better rest handling: fill gaps between notes with appropriate rest durations (not just `r.1` for empty bars).
- Support for ghost notes and dead notes.

### Fingering Optimization

- Validate DP solver output against reference fingerings from GP5.
- Tune `_transition_cost` weights using reference movement patterns.
- Add position preference (prefer lower positions for simpler passages).
- Consider hand position memory (prefer staying in a position across multiple notes).

---

## Section 4: Reference-Guided Parameter Calibration

- For each test song, extract ground truth parameters: actual note durations, gap sizes, density per bar.
- Use these to set optimal cleanup/quantization thresholds.
- Potentially make thresholds adaptive based on detected BPM and genre.
- Track parameter sensitivity: how much each parameter change affects quality metrics.

---

## Testing Strategy

- GP5 parsing: unit tests with known GP5 content.
- Comparator: unit tests with synthetic reference/generated pairs.
- Pipeline integration: end-to-end tests comparing against GP5 reference.
- Regression: quality metrics must not decrease after each improvement.
- All development follows TDD (test first, fail, implement, pass).

## Rollout

1. Build comparison harness first (GP5 parser, comparator, visual diff).
2. Establish baseline metrics by running current pipeline against reference.
3. Improve transcription quality (BasicPitch tuning).
4. Improve cleanup/quantization/export stages.
5. Fine-tune fingering.
6. Each improvement iteration: measure, compare, verify quality gain.

---

## Brainstorming Checklist

- [x] Explore project context and current pipeline.
- [x] Gather quality expectations and test scope from user.
- [x] Compare approaches (A: pipeline tuning, B: reference-guided, C: replace transcription).
- [x] Present architecture, pipeline improvements, transcription improvements, and calibration design.
- [x] Record approved design in `docs/plans`.
