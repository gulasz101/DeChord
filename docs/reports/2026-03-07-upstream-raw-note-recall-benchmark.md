# 2026-03-07 Upstream Raw Note Recall Benchmark

## What Changed

- Added typed env-backed upstream raw-recall config in `backend/app/midi.py`:
  - `DECHORD_RAW_NOTE_RECALL_ENABLE`
  - `DECHORD_RAW_NOTE_MIN_CONFIDENCE`
  - `DECHORD_RAW_NOTE_MIN_DURATION_MS`
  - `DECHORD_RAW_NOTE_ALLOW_WEAK_BASS_CANDIDATES`
  - `DECHORD_RAW_NOTE_SPARSE_REGION_BOOST_ENABLE`
  - `DECHORD_DENSE_CANDIDATE_SPARSE_REGION_THRESHOLD_MS`
  - `DECHORD_DENSE_CANDIDATE_SUPPORT_RELAXATION`
- Changed the real Basic Pitch path to use `transcribe_bass_stem_to_midi_detailed(...)`, preserve serialized `basic_pitch_note_events`, and apply a bass-focused raw-candidate filter before the existing stabilization/admission stages.
- Added candidate-flow trace metrics for:
  - Basic Pitch raw pre-filter vs post-filter counts
  - dense candidates proposed vs accepted
  - dense candidate rejection histograms
- Activated dense-note recovery in the standard real path through sparse-region detection, instead of leaving it restricted to the high-accuracy branch.

## Compared Configurations

- `baseline`
  - `DECHORD_RAW_NOTE_RECALL_ENABLE=0`
  - `DECHORD_RAW_NOTE_SPARSE_REGION_BOOST_ENABLE=0`
- `enabled-bounded`
  - `DECHORD_RAW_NOTE_RECALL_ENABLE=1`
  - `DECHORD_RAW_NOTE_MIN_CONFIDENCE=0.15`
  - `DECHORD_RAW_NOTE_MIN_DURATION_MS=35`
  - `DECHORD_RAW_NOTE_ALLOW_WEAK_BASS_CANDIDATES=1`
  - `DECHORD_RAW_NOTE_SPARSE_REGION_BOOST_ENABLE=1`
  - `DECHORD_DENSE_CANDIDATE_SPARSE_REGION_THRESHOLD_MS=300`
  - `DECHORD_DENSE_CANDIDATE_SUPPORT_RELAXATION=0.10`
- `recall-only`
  - same as above, but `DECHORD_RAW_NOTE_SPARSE_REGION_BOOST_ENABLE=0`

## Exact Commands Run

- `cd /Users/wojciechgula/Projects/DeChord/backend && uv run pytest tests/test_bass_transcriber.py tests/test_dense_note_generator.py tests/test_pipeline_trace.py tests/test_tab_pipeline.py tests/test_midi.py`
- `cd /Users/wojciechgula/Projects/DeChord/backend && uv run python scripts/evaluate_tab_quality.py --song-dir "../test songs" --song "Muse - Hysteria" --quality standard --config baseline --phase upstream_raw_baseline --trace-pipeline`
- `cd /Users/wojciechgula/Projects/DeChord/backend && DECHORD_RAW_NOTE_RECALL_ENABLE=1 DECHORD_RAW_NOTE_MIN_CONFIDENCE=0.15 DECHORD_RAW_NOTE_MIN_DURATION_MS=35 DECHORD_RAW_NOTE_ALLOW_WEAK_BASS_CANDIDATES=1 DECHORD_RAW_NOTE_SPARSE_REGION_BOOST_ENABLE=1 DECHORD_DENSE_CANDIDATE_SPARSE_REGION_THRESHOLD_MS=180 DECHORD_DENSE_CANDIDATE_SUPPORT_RELAXATION=0.20 uv run python scripts/evaluate_tab_quality.py --song-dir "../test songs" --song "Muse - Hysteria" --quality standard --config baseline --phase upstream_raw_enabled --trace-pipeline`
- `cd /Users/wojciechgula/Projects/DeChord/backend && DECHORD_RAW_NOTE_RECALL_ENABLE=1 DECHORD_RAW_NOTE_MIN_CONFIDENCE=0.15 DECHORD_RAW_NOTE_MIN_DURATION_MS=35 DECHORD_RAW_NOTE_ALLOW_WEAK_BASS_CANDIDATES=1 DECHORD_RAW_NOTE_SPARSE_REGION_BOOST_ENABLE=1 DECHORD_DENSE_CANDIDATE_SPARSE_REGION_THRESHOLD_MS=300 DECHORD_DENSE_CANDIDATE_SUPPORT_RELAXATION=0.10 uv run python scripts/evaluate_tab_quality.py --song-dir "../test songs" --song "Muse - Hysteria" --quality standard --config baseline --phase upstream_raw_enabled_bounded --trace-pipeline`
- `cd /Users/wojciechgula/Projects/DeChord/backend && uv run python scripts/evaluate_tab_quality.py --song-dir "../test songs" --song "Iron Maiden - The Trooper" --quality standard --config baseline --phase upstream_raw_baseline --trace-pipeline`
- `cd /Users/wojciechgula/Projects/DeChord/backend && DECHORD_RAW_NOTE_RECALL_ENABLE=1 DECHORD_RAW_NOTE_MIN_CONFIDENCE=0.15 DECHORD_RAW_NOTE_MIN_DURATION_MS=35 DECHORD_RAW_NOTE_ALLOW_WEAK_BASS_CANDIDATES=1 DECHORD_RAW_NOTE_SPARSE_REGION_BOOST_ENABLE=1 DECHORD_DENSE_CANDIDATE_SPARSE_REGION_THRESHOLD_MS=180 DECHORD_DENSE_CANDIDATE_SUPPORT_RELAXATION=0.20 uv run python scripts/evaluate_tab_quality.py --song-dir "../test songs" --song "Iron Maiden - The Trooper" --quality standard --config baseline --phase upstream_raw_enabled --trace-pipeline`
  - did not complete in practical time; run was terminated after prolonged CPU-bound execution
- `cd /Users/wojciechgula/Projects/DeChord/backend && DECHORD_RAW_NOTE_RECALL_ENABLE=1 DECHORD_RAW_NOTE_MIN_CONFIDENCE=0.15 DECHORD_RAW_NOTE_MIN_DURATION_MS=35 DECHORD_RAW_NOTE_ALLOW_WEAK_BASS_CANDIDATES=1 DECHORD_RAW_NOTE_SPARSE_REGION_BOOST_ENABLE=1 DECHORD_DENSE_CANDIDATE_SPARSE_REGION_THRESHOLD_MS=300 DECHORD_DENSE_CANDIDATE_SUPPORT_RELAXATION=0.10 uv run python scripts/evaluate_tab_quality.py --song-dir "../test songs" --song "Iron Maiden - The Trooper" --quality standard --config baseline --phase upstream_raw_enabled_bounded --trace-pipeline`
  - also did not complete in practical time; one restart was required after an interrupted stem output directory caused a `drums.wav` write failure
- `cd /Users/wojciechgula/Projects/DeChord/backend && DECHORD_RAW_NOTE_RECALL_ENABLE=1 DECHORD_RAW_NOTE_MIN_CONFIDENCE=0.15 DECHORD_RAW_NOTE_MIN_DURATION_MS=35 DECHORD_RAW_NOTE_ALLOW_WEAK_BASS_CANDIDATES=1 DECHORD_RAW_NOTE_SPARSE_REGION_BOOST_ENABLE=0 uv run python scripts/evaluate_tab_quality.py --song-dir "../test songs" --song "Iron Maiden - The Trooper" --quality standard --config baseline --phase upstream_raw_recall_only --trace-pipeline`

## Stage-Trace Comparison

### Muse - Hysteria

| Config | Basic Pitch raw | Pitch stabilized | Admission filtered | Dense candidates | Dense accepted | Final notes |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 92 | 92 | 92 | 0 | 0 | 41 |
| enabled-bounded | 92 | 92 | 92 | 283 | 279 | 264 |

Interpretation:

- `basic_pitch_raw` did not improve. The new note-event preservation path did not increase raw stage count on this real song.
- Dense-note recovery was no longer inert in the benchmarked standard path. It proposed `283` candidates and accepted `279`.
- The final note count moved much closer to reference: `41 -> 264`, still short of `1339`.

### Iron Maiden - The Trooper

| Config | Basic Pitch raw | Pitch stabilized | Admission filtered | Dense candidates | Dense accepted | Final notes |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 337 | 337 | 337 | 0 | 0 | 407 |
| recall-only | 337 | 337 | 337 | 0 | 0 | 407 |

Interpretation:

- `basic_pitch_raw` again did not improve on the real song.
- Dense-note recovery remained `0` in the completed `recall-only` run because sparse-region boost was disabled there.
- The full sparse-boost configuration was reached and exercised during development, but both Trooper sparse-boost benchmark attempts were too slow to finish, so there is not yet a completed Trooper dense-recovery metric to claim.

## Top-Line Metrics

### Muse - Hysteria

| Config | F1 | Precision | Recall | Pitch Acc | Octave Errors | Generated Notes | Note Diff |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 0.0565 | 0.9512 | 0.0291 | 0.3077 | 4 | 41 | -1298 |
| enabled-bounded | 0.3157 | 0.9583 | 0.1889 | 0.1225 | 20 | 264 | -1075 |

Tradeoff:

- Hysteria improved heavily on recall and final note count.
- Precision stayed high, but pitch accuracy collapsed and octave errors rose materially.
- This is a real recall gain, but it is coming from dense insertion rather than an improved `basic_pitch_raw` stage.

### Iron Maiden - The Trooper

| Config | F1 | Precision | Recall | Pitch Acc | Octave Errors | Generated Notes | Note Diff |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 0.2488 | 0.6192 | 0.1557 | 0.5992 | 23 | 407 | -1212 |
| recall-only | 0.2488 | 0.6192 | 0.1557 | 0.5992 | 23 | 407 | -1212 |

Tradeoff:

- The completed Trooper comparison showed no measurable improvement.
- The aggressive dense-boost modes that should have changed this song introduced a runtime blow-up instead of a finished benchmark artifact.

## Answers To The Key Questions

- Did `basic_pitch_raw` increase meaningfully?
  - No. It stayed flat on both completed real-song benchmark comparisons.
- Did `dense accepted` become non-zero?
  - Yes for `Muse - Hysteria` in the standard benchmark path: `279`.
  - No completed Trooper run achieved non-zero dense acceptance because the sparse-boost variants were not practical to finish.
- Did final note count move meaningfully toward reference?
  - Yes for Hysteria: `41 -> 264`.
  - No for Trooper in the completed run set.
- What precision/recall tradeoff was introduced?
  - Hysteria gained substantial recall with much worse pitch accuracy and more octave errors.
  - Trooper currently shows either no gain (`recall-only`) or an impractical runtime cost (`sparse boost`).

## Recommendation

The next step is not more cleanup tuning. The next step is to make the sparse-region dense pass bounded and selective enough to finish on Trooper, while separately debugging why preserved Basic Pitch note events are not increasing `basic_pitch_raw` on either real benchmark song. Until that is fixed, the implementation improves candidate generation through dense recovery on some material, but it does not yet solve the dominant upstream `basic_pitch_raw` bottleneck identified in the stage analysis.
