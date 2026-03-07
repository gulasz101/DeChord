# 2026-03-07 Note Admission Tightening Benchmark

## What Changed

- Added typed env-backed note-admission controls in `backend/app/midi.py`:
  - `DECHORD_NOTE_ADMISSION_ENABLE`
  - `DECHORD_NOTE_MIN_DURATION_MS`
  - `DECHORD_NOTE_LOW_CONFIDENCE_THRESHOLD`
  - `DECHORD_NOTE_OCTAVE_INTRUSION_MAX_DURATION_MS`
  - `DECHORD_NOTE_MERGE_GAP_MS`
  - `DECHORD_DENSE_CANDIDATE_MIN_DURATION_MS`
  - `DECHORD_DENSE_UNSTABLE_CONTEXT_PENALTY`
  - `DECHORD_DENSE_OCTAVE_NEIGHBOR_PENALTY`
- Tightened Basic Pitch note-event cleanup in `backend/app/services/bass_transcriber.py`:
  - reject isolated short low-confidence notes
  - suppress short bracketed intrusions, including octave slips
  - merge same-pitch fragments conservatively while preserving likely repeated plucks
- Tightened dense-note recovery in `backend/app/services/dense_note_generator.py` and `backend/app/services/tab_pipeline.py`:
  - reject weak very-short dense candidates
  - reject octave-neighbor conflicts near already accepted notes
  - penalize unstable local pitch context

## Compared Configurations

- `refinement` with pitch stability on and the new note-admission layer disabled to approximate the prior benchmarked behavior
- `refinement` with pitch stability on and conservative note-admission enabled
- `full` with pitch stability on and conservative note-admission enabled

## Commands Run

- `cd /Users/wojciechgula/Projects/DeChord/backend && DECHORD_PITCH_STABILITY_ENABLE=1 DECHORD_NOTE_ADMISSION_ENABLE=0 DECHORD_DENSE_CANDIDATE_MIN_DURATION_MS=1 DECHORD_DENSE_UNSTABLE_CONTEXT_PENALTY=0 DECHORD_DENSE_OCTAVE_NEIGHBOR_PENALTY=0 uv run python scripts/evaluate_tab_quality.py --song-dir "../test songs" --song "Muse - Hysteria" --quality standard --config refinement --phase note_admission_baseline_refinement`
- `cd /Users/wojciechgula/Projects/DeChord/backend && DECHORD_PITCH_STABILITY_ENABLE=1 DECHORD_NOTE_ADMISSION_ENABLE=1 uv run python scripts/evaluate_tab_quality.py --song-dir "../test songs" --song "Muse - Hysteria" --quality standard --config refinement --phase note_admission_conservative_refinement`
- `cd /Users/wojciechgula/Projects/DeChord/backend && DECHORD_PITCH_STABILITY_ENABLE=1 DECHORD_NOTE_ADMISSION_ENABLE=1 uv run python scripts/evaluate_tab_quality.py --song-dir "../test songs" --song "Muse - Hysteria" --quality standard --config full --phase note_admission_conservative_full`
- `cd /Users/wojciechgula/Projects/DeChord/backend && DECHORD_PITCH_STABILITY_ENABLE=1 DECHORD_NOTE_ADMISSION_ENABLE=0 DECHORD_DENSE_CANDIDATE_MIN_DURATION_MS=1 DECHORD_DENSE_UNSTABLE_CONTEXT_PENALTY=0 DECHORD_DENSE_OCTAVE_NEIGHBOR_PENALTY=0 uv run python scripts/evaluate_tab_quality.py --song-dir "../test songs" --song "Iron Maiden - The Trooper" --quality standard --config refinement --phase note_admission_baseline_refinement`
- `cd /Users/wojciechgula/Projects/DeChord/backend && DECHORD_PITCH_STABILITY_ENABLE=1 DECHORD_NOTE_ADMISSION_ENABLE=1 uv run python scripts/evaluate_tab_quality.py --song-dir "../test songs" --song "Iron Maiden - The Trooper" --quality standard --config refinement --phase note_admission_conservative_refinement`
- `cd /Users/wojciechgula/Projects/DeChord/backend && DECHORD_PITCH_STABILITY_ENABLE=1 DECHORD_NOTE_ADMISSION_ENABLE=1 uv run python scripts/evaluate_tab_quality.py --song-dir "../test songs" --song "Iron Maiden - The Trooper" --quality standard --config full --phase note_admission_conservative_full`

## Top-Line Results

### Muse - Hysteria

| Config | F1 | Precision | Recall | Pitch Acc | Pitch Mismatch | Octave Errors | Generated Notes | Note Diff | Runtime (s) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline refinement | 0.0635 | 0.9565 | 0.0329 | 0.2500 | 33 | 7 | 46 | -1293 | 119.01 |
| conservative refinement | 0.0635 | 0.9565 | 0.0329 | 0.2500 | 33 | 7 | 46 | -1293 | 117.94 |
| conservative full | 0.0635 | 0.9565 | 0.0329 | 0.2500 | 33 | 7 | 46 | -1293 | 225.91 |

### Iron Maiden - The Trooper

| Config | F1 | Precision | Recall | Pitch Acc | Pitch Mismatch | Octave Errors | Generated Notes | Note Diff | Runtime (s) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline refinement | 0.2838 | 0.6490 | 0.1816 | 0.6633 | 99 | 10 | 453 | -1166 | 136.65 |
| conservative refinement | 0.2838 | 0.6490 | 0.1816 | 0.6633 | 99 | 10 | 453 | -1166 | 136.63 |
| conservative full | 0.2779 | 0.6269 | 0.1785 | 0.6228 | 109 | 26 | 461 | -1158 | 261.39 |

## Interpretation

- Precision did not improve at the song-level benchmark on either song in `refinement`.
- Recall also did not regress in `refinement`; the before/after metrics were effectively identical.
- Octave errors did not improve in `refinement`.
- `full` remained worse than `refinement` on `The Trooper` and bought nothing on `Hysteria`.

## Remaining Error Modes

- The targeted cleanup rules are working in unit and integration tests, but they are not yet moving the final benchmark outputs. That suggests the current song-level error budget is dominated by upstream note generation or later-stage cleanup/quantization interactions rather than the specific short-note cases covered here.
- `Hysteria` remains overwhelmingly recall-limited.
- `The Trooper` still carries the same pitch-mismatch and octave-slip profile in `refinement`, and `full` still overgenerates.

## Recommended Next Tuning Step

- Instrument the real benchmark path to count how many notes are removed by the new Basic Pitch admission gate and how many dense candidates are rejected before cleanup. If those counts stay low on the benchmark songs, the next tuning pass should move one stage earlier, closer to raw Basic Pitch event generation or the cleanup/quantization handoff, rather than further tightening these same conservative rules.
