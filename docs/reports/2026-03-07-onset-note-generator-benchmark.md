# 2026-03-07 Onset Note Generator Benchmark

## What Was Implemented

- Added `backend/app/services/onset_note_generator.py` with a deterministic bass-focused onset pipeline:
  - onset detection
  - onset-region construction
  - one pitch estimate per region
  - onset note candidate emission
- Added typed env-backed config in `backend/app/midi.py`:
  - `DECHORD_ONSET_NOTE_GENERATOR_ENABLE`
  - `DECHORD_ONSET_NOTE_GENERATOR_MODE`
  - `DECHORD_ONSET_MIN_SPACING_MS`
  - `DECHORD_ONSET_STRENGTH_THRESHOLD`
  - `DECHORD_ONSET_REGION_MAX_DURATION_MS`
  - `DECHORD_ONSET_REGION_MIN_DURATION_MS`
  - `DECHORD_ONSET_DENSITY_NOTES_PER_SEC_THRESHOLD`
- Integrated onset-generated candidates into the real `TabPipeline` before cleanup/quantization.
- Extended pipeline tracing with an `onset_candidates` stage and explicit proposed/accepted/rejected counts.

## Integration Design

- Mode used in the real benchmark run: `fallback`
- Behavior:
  - run onset detection on the analysis bass
  - generate onset note candidates
  - if upstream note density is below the configured threshold, merge those candidates into the pre-cleanup note stream
  - reuse the existing cleanup, quantization, fingering, and export stages unchanged

This keeps the current downstream stack intact and changes only the upstream note-candidate supply.

## Compared Configurations

- `baseline`
  - onset generator disabled
- `onset-enabled`
  - `DECHORD_ONSET_NOTE_GENERATOR_ENABLE=1`
  - `DECHORD_ONSET_NOTE_GENERATOR_MODE=fallback`
  - `DECHORD_ONSET_MIN_SPACING_MS=70`
  - `DECHORD_ONSET_STRENGTH_THRESHOLD=0.35`
  - `DECHORD_ONSET_REGION_MAX_DURATION_MS=220`
  - `DECHORD_ONSET_REGION_MIN_DURATION_MS=40`
  - `DECHORD_ONSET_DENSITY_NOTES_PER_SEC_THRESHOLD=4.5`

## Exact Commands Run

- `cd /Users/wojciechgula/Projects/DeChord/backend && uv run pytest tests/test_onset_note_generator.py tests/test_midi.py tests/test_pipeline_trace.py tests/test_tab_pipeline.py`
- `cd /Users/wojciechgula/Projects/DeChord/backend && uv run python scripts/evaluate_tab_quality.py --song-dir "../test songs" --song "Muse - Hysteria" --quality standard --config baseline --phase onset_upstream_baseline --trace-pipeline`
- `cd /Users/wojciechgula/Projects/DeChord/backend && DECHORD_ONSET_NOTE_GENERATOR_ENABLE=1 DECHORD_ONSET_NOTE_GENERATOR_MODE=fallback DECHORD_ONSET_MIN_SPACING_MS=70 DECHORD_ONSET_STRENGTH_THRESHOLD=0.35 DECHORD_ONSET_REGION_MAX_DURATION_MS=220 DECHORD_ONSET_REGION_MIN_DURATION_MS=40 DECHORD_ONSET_DENSITY_NOTES_PER_SEC_THRESHOLD=4.5 uv run python scripts/evaluate_tab_quality.py --song-dir "../test songs" --song "Muse - Hysteria" --quality standard --config baseline --phase onset_upstream_enabled --trace-pipeline`
- `cd /Users/wojciechgula/Projects/DeChord/backend && uv run python scripts/evaluate_tab_quality.py --song-dir "../test songs" --song "Iron Maiden - The Trooper" --quality standard --config baseline --phase onset_upstream_baseline --trace-pipeline`
- `cd /Users/wojciechgula/Projects/DeChord/backend && DECHORD_ONSET_NOTE_GENERATOR_ENABLE=1 DECHORD_ONSET_NOTE_GENERATOR_MODE=fallback DECHORD_ONSET_MIN_SPACING_MS=70 DECHORD_ONSET_STRENGTH_THRESHOLD=0.35 DECHORD_ONSET_REGION_MAX_DURATION_MS=220 DECHORD_ONSET_REGION_MIN_DURATION_MS=40 DECHORD_ONSET_DENSITY_NOTES_PER_SEC_THRESHOLD=4.5 uv run python scripts/evaluate_tab_quality.py --song-dir "../test songs" --song "Iron Maiden - The Trooper" --quality standard --config baseline --phase onset_upstream_enabled --trace-pipeline`
  - terminated after runtime grew far beyond the baseline run and no finished artifact was produced

## Stage-Trace Comparison

### Muse - Hysteria

| Config | Basic Pitch raw | Admission filtered | Onset candidates | Dense accepted | Final notes |
| --- | ---: | ---: | ---: | ---: | ---: |
| baseline | 92 | 92 | 0 | 0 | 41 |
| onset-enabled | 92 | 92 | 604 | 0 | 539 |

Interpretation:

- `basic_pitch_raw` remained flat at `92`.
- The onset stage inserted `604` candidates and materially changed the final count.
- `raw_note_source_summary` in the enabled run was:
  - `basic_pitch`: `92`
  - `onset_note_generator`: `604`
- The gain came from the new onset stage, not from Basic Pitch or dense-note recovery.

### Iron Maiden - The Trooper

| Config | Basic Pitch raw | Admission filtered | Onset candidates | Dense accepted | Final notes |
| --- | ---: | ---: | ---: | ---: | ---: |
| baseline | 337 | 337 | 0 | 0 | 407 |
| onset-enabled | not completed | not completed | not completed | not completed | not completed |

Interpretation:

- The completed baseline trace confirms the upstream shortage is still present without onset candidates.
- The onset-enabled run did not finish in practical time, so there is no defensible Trooper improvement claim yet.

## Top-Line Metrics

### Muse - Hysteria

| Config | F1 | Precision | Recall | Pitch Acc | Octave Errors | Generated Notes | Tab Pipeline Runtime |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 0.0565 | 0.9512 | 0.0291 | 0.3077 | 4 | 41 | 23.70s |
| onset-enabled | 0.5399 | 0.9406 | 0.3786 | 0.1775 | 39 | 539 | 82.75s |

Summary:

- Note-count recall improved substantially.
- Precision stayed high enough to remain usable.
- Pitch accuracy degraded hard and octave errors rose sharply.
- Runtime increased by roughly 3.5x inside `tab_pipeline`.

### Iron Maiden - The Trooper

| Config | F1 | Precision | Recall | Pitch Acc | Octave Errors | Generated Notes | Tab Pipeline Runtime |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 0.2488 | 0.6192 | 0.1557 | 0.5992 | 23 | 407 | 27.11s |
| onset-enabled | not completed | not completed | not completed | not completed | not completed | not completed | exceeded baseline runtime by a large margin before termination |

## Answers To The Key Questions

- Did final note count increase substantially?
  - Yes on `Muse - Hysteria`: `41 -> 539`.
  - No completed claim is available for `Iron Maiden - The Trooper`.
- Did Hysteria improve without relying only on dense sparse-boost?
  - Yes. `dense_accepted` stayed `0`; the increase came from `onset_candidates`.
- Did Basic Pitch remain sparse?
  - Yes. `basic_pitch_raw` stayed `92` on Hysteria baseline and enabled.
- What happened to F1 / precision / recall / octave errors?
  - Hysteria F1 and recall improved strongly, precision stayed high, but octave errors rose from `4` to `39` and pitch accuracy dropped from `0.3077` to `0.1775`.
- Was runtime reasonable?
  - Hysteria was slower but still completed.
  - Trooper onset-enabled was not reasonable in the tested configuration.

## Conclusion

This is directionally the right architectural move. The benchmarked Hysteria run shows the pipeline is no longer fully starved by Basic Pitch once an onset-based upstream generator is inserted before cleanup. The main remaining problem is selectivity: the current onset region/pitch pass improves count recall but still admits too many octave-wrong notes and can become too slow on denser material like Trooper.

## Next Recommended Tuning Step

The next step should be a tighter retention gate on onset candidates before merge:

- cap candidate generation per second or per bar
- reject weak low-support candidates earlier
- add a stronger lower-fundamental vs octave-harmonic check
- short-circuit onset generation on passages whose upstream density is already adequate
