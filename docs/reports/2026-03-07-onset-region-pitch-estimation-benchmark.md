# 2026-03-07 Onset Region Pitch Estimation Benchmark

## What Changed

- Kept the onset-driven rhythm source and real `TabPipeline` integration path.
- Strengthened `backend/app/services/onset_note_generator.py` pitch selection with:
  - whole-region bass candidate scoring
  - short frame-consensus voting inside each onset region
  - explicit lower-octave comparison during both frame voting and final candidate choice
  - bounded candidate evaluation (`<= 6` merged candidates per region, compact frame windows only)
- Added benchmark guardrails in `backend/scripts/evaluate_tab_quality.py` and `backend/app/services/resource_monitor.py`:
  - serial execution by construction
  - process-tree RSS sampling via `ps`
  - child-process counting
  - clean abort path with structured `resource_monitor` metadata in metrics and pipeline trace output

## Octave Suppression

The estimator now scores each onset region in two ways:

1. Whole-region spectral/autocorrelation support
2. Frame-level pitch consensus across the same region

If the strongest candidate looks like an octave-up harmonic, the estimator compares it against the lower octave using:

- fundamental and low-band support
- autocorrelation support
- frame-consensus support ratio
- configured octave penalty bonus

It prefers the lower octave only when the lower bass fundamental has compatible support. It does not blindly shift every note down.

## Resource Monitoring

- Enabled by `--resource-monitor`
- Tuned here with `--max-memory-mb 12000 --max-child-procs 4`
- Trace fields now include:
  - `enabled`
  - `max_memory_mb`
  - `max_child_processes`
  - `peak_rss_mb`
  - `peak_child_process_count`
  - `thresholds_exceeded`
  - `aborted_for_safety`
  - `serial_execution`

No run in this report exceeded the configured limits.

## Compared Configurations

- `baseline_guarded_*`
  - onset generator disabled
  - resource monitor enabled
- `onset_region_pitch_guarded_*`
  - onset generator enabled with the improved regional pitch estimator
  - resource monitor enabled
- Historical reference from [2026-03-07-onset-note-generator-benchmark.md](/Users/wojciechgula/Projects/DeChord/docs/reports/2026-03-07-onset-note-generator-benchmark.md)
  - earlier onset-enabled path before this regional pitch work
  - useful mainly for Hysteria and for the prior Trooper non-completion outcome

## Exact Commands Run

```bash
cd /Users/wojciechgula/Projects/DeChord/backend
uv run pytest tests/test_onset_note_generator.py tests/test_bass_transcriber.py tests/test_midi.py tests/test_pipeline_trace.py tests/test_tab_pipeline.py tests/test_resource_monitor.py tests/test_evaluate_tab_quality.py -q

uv run python scripts/evaluate_tab_quality.py --song-dir "../test songs" --song "Muse - Hysteria" --quality standard --config baseline --phase baseline_guarded_hysteria --trace-pipeline --resource-monitor --max-memory-mb 12000 --max-child-procs 4

env DECHORD_ONSET_NOTE_GENERATOR_ENABLE=1 DECHORD_ONSET_NOTE_GENERATOR_MODE=fallback DECHORD_ONSET_MIN_SPACING_MS=70 DECHORD_ONSET_STRENGTH_THRESHOLD=0.35 DECHORD_ONSET_REGION_MAX_DURATION_MS=220 DECHORD_ONSET_REGION_MIN_DURATION_MS=40 DECHORD_ONSET_DENSITY_NOTES_PER_SEC_THRESHOLD=4.5 DECHORD_ONSET_REGION_PITCH_ENABLE=1 DECHORD_ONSET_REGION_PITCH_METHOD=bass_harmonic_weighted DECHORD_ONSET_REGION_OCTAVE_SUPPRESSION_ENABLE=1 DECHORD_ONSET_REGION_OCTAVE_PENALTY=0.40 DECHORD_ONSET_REGION_MIN_CONFIDENCE=0.18 DECHORD_ONSET_REGION_LOWBAND_SUPPORT_WEIGHT=0.60 DECHORD_ONSET_REGION_HARMONIC_PENALTY_WEIGHT=0.35 DECHORD_ONSET_REGION_PITCH_FLOOR_MIDI=24 DECHORD_ONSET_REGION_PITCH_CEILING_MIDI=64 uv run python scripts/evaluate_tab_quality.py --song-dir "../test songs" --song "Muse - Hysteria" --quality standard --config baseline --phase onset_region_pitch_guarded_hysteria --trace-pipeline --resource-monitor --max-memory-mb 12000 --max-child-procs 4

uv run python scripts/evaluate_tab_quality.py --song-dir "../test songs" --song "Iron Maiden - The Trooper" --quality standard --config baseline --phase baseline_guarded_trooper --trace-pipeline --resource-monitor --max-memory-mb 12000 --max-child-procs 4

env DECHORD_ONSET_NOTE_GENERATOR_ENABLE=1 DECHORD_ONSET_NOTE_GENERATOR_MODE=fallback DECHORD_ONSET_MIN_SPACING_MS=70 DECHORD_ONSET_STRENGTH_THRESHOLD=0.35 DECHORD_ONSET_REGION_MAX_DURATION_MS=220 DECHORD_ONSET_REGION_MIN_DURATION_MS=40 DECHORD_ONSET_DENSITY_NOTES_PER_SEC_THRESHOLD=4.5 DECHORD_ONSET_REGION_PITCH_ENABLE=1 DECHORD_ONSET_REGION_PITCH_METHOD=bass_harmonic_weighted DECHORD_ONSET_REGION_OCTAVE_SUPPRESSION_ENABLE=1 DECHORD_ONSET_REGION_OCTAVE_PENALTY=0.40 DECHORD_ONSET_REGION_MIN_CONFIDENCE=0.18 DECHORD_ONSET_REGION_LOWBAND_SUPPORT_WEIGHT=0.60 DECHORD_ONSET_REGION_HARMONIC_PENALTY_WEIGHT=0.35 DECHORD_ONSET_REGION_PITCH_FLOOR_MIDI=24 DECHORD_ONSET_REGION_PITCH_CEILING_MIDI=64 uv run python scripts/evaluate_tab_quality.py --song-dir "../test songs" --song "Iron Maiden - The Trooper" --quality standard --config baseline --phase onset_region_pitch_guarded_trooper --trace-pipeline --resource-monitor --max-memory-mb 12000 --max-child-procs 4
```

## Top-Line Metrics

### Muse - Hysteria

| Config | F1 | Precision | Recall | Pitch Acc | Octave Errors | Generated Notes | Tab Runtime |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline_guarded | 0.0565 | 0.9512 | 0.0291 | 0.3077 | 4 | 41 | 23.68s |
| earlier onset-enabled | 0.5399 | 0.9406 | 0.3786 | 0.1775 | 39 | 539 | 82.75s |
| onset_region_pitch_guarded | 0.2251 | 0.9101 | 0.1285 | 0.1395 | 18 | 189 | 42.05s |

### Iron Maiden - The Trooper

| Config | F1 | Precision | Recall | Pitch Acc | Octave Errors | Generated Notes | Tab Runtime |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline_guarded | 0.2488 | 0.6192 | 0.1557 | 0.5992 | 23 | 407 | 27.47s |
| earlier onset-enabled | not completed practically | not completed practically | not completed practically | not completed practically | not completed practically | not completed practically | not completed practically |
| onset_region_pitch_guarded | 0.4389 | 0.6532 | 0.3305 | 0.4991 | 32 | 819 | 95.49s |

## Stage-Trace Comparison

### Muse - Hysteria

| Config | Onset Candidates | Final Pipeline Notes | Octave Suppressed | Pitch Corrected | Avg Region Confidence |
| --- | ---: | ---: | ---: | ---: | ---: |
| baseline_guarded | 0 | 41 | 0 | 0 | n/a |
| onset_region_pitch_guarded | 189 | 221 | 69 | 69 | 0.8556 |

Interpretation:

- The new onset path is materially more selective than the earlier 539-note onset burst.
- Octave suppression fires often enough to matter (`69` regions), but the final pitch accuracy is still weak.
- The high average region confidence does not match the benchmark accuracy well; confidence is still over-optimistic.

### Iron Maiden - The Trooper

| Config | Onset Candidates | Final Pipeline Notes | Octave Suppressed | Pitch Corrected | Avg Region Confidence |
| --- | ---: | ---: | ---: | ---: | ---: |
| baseline_guarded | 0 | 407 | 0 | 0 | n/a |
| onset_region_pitch_guarded | 621 | 821 | 83 | 83 | 0.8769 |

Interpretation:

- The new onset path completed on Trooper, unlike the earlier onset-enabled attempt.
- It roughly doubled the final pipeline note count and more than doubled recall.
- Pitch reliability is still not good enough: octave errors rose and pitch accuracy fell versus baseline.

## Resource Monitor Outcomes

| Run | Peak RSS | Peak Child Procs | Threshold Exceeded | Aborted |
| --- | ---: | ---: | --- | --- |
| Hysteria baseline_guarded | 3344.95 MB | 2 | no | no |
| Hysteria onset_region_pitch_guarded | 3471.47 MB | 2 | no | no |
| Trooper baseline_guarded | 3535.31 MB | 2 | no | no |
| Trooper onset_region_pitch_guarded | 3885.31 MB | 2 | no | no |

The guardrail plumbing worked and stayed cheap. These runs remained far below the configured 12 GB / 4-child limits.

## Answers

- Was recall preserved?
  - Versus baseline: yes on both songs.
  - Versus the earlier Hysteria onset-heavy run: no, recall dropped from `0.3786` to `0.1285`, but the note flood and octave-error spike were reduced.
- Did pitch accuracy improve?
  - Not yet in top-line benchmark terms. It is still worse than baseline on both songs.
- Did octave errors improve?
  - Yes versus the earlier Hysteria onset-heavy run (`39 -> 18`).
  - No versus the guarded baselines (`4 -> 18` on Hysteria, `23 -> 32` on Trooper).
- Did runtime stay acceptable?
  - Better than the earlier onset-heavy direction.
  - Trooper is now benchmarkable and completed, but `95.49s` of tab-pipeline time is still expensive.
- Were any runs aborted for safety?
  - No.

## Conclusion

This still looks like the right architectural direction, but only partially. The regional pitch estimator plus octave suppression made the onset path far more bounded and got Trooper through a full guarded benchmark, which is a real improvement over the prior non-completing onset attempt. The remaining issue is selectivity: the onset path still admits too many wrong pitches while reporting very high internal confidence.

## Next Recommended Tuning Step

Add a stricter acceptance gate on top of the regional estimator, keyed to frame-consensus strength and lower-fundamental support, so weak-but-confident onset regions are rejected before they reach cleanup/quantization.
