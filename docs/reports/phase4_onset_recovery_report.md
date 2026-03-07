# Phase 4 Onset Recovery Report

## Metrics (Phase 3 Final -> Phase 4 Final)

| Song | onset_f1 (ms) | pitch_accuracy | octave_confusion (exact/+12/-12/other) | note_density_correlation |
|---|---|---|---|---|
| Muse - Hysteria | 0.1461 -> 0.3743 | 0.3774 -> 0.2803 | 40/0/12/54 -> 88/2/27/197 | 0.1746 -> 0.2583 |
| Iron Maiden - The Trooper | 0.3508 -> 0.4586 | 0.7561 -> 0.6404 | 279/0/1/89 -> 349/1/8/187 | 0.1353 -> 0.0883 |

## Attribution Summary

Stage-wise attribution in `hysteria_phase4_stage_attribution.json` shows the dominant loss starts in raw BasicPitch output (`raw_transcriber_output` recall 0.0269) and not in octave stabilization (`raw` -> `post_phase3_octave_stabilization` recall delta 0.0000).

Hysteria missing-note concentration remains heavily short-note and dense-bar dominated:
- Missing in raw: 1303 notes, dense-bar share 65.31%, short-note share 99.77%
- Missing in final: 1028 notes, dense-bar share 65.47%, short-note share 99.71%

Worst-bar deficits (`hysteria_phase4_worst_bars.md`) are concentrated in dense repeated passages (e.g., bars 80-85 all at 16-note deficits).

## Chosen Fix (Minimal Intervention)

Implemented one narrow, bar-local change in `TabPipeline` aggressive mode:
- Extend existing second-pass retranscription trigger from only empty bars to dense-sparse bars (`onset_peaks >= 6` with very low generated note count).
- Keep this behavior scoped to `high_accuracy_aggressive` only.
- For dense-sparse bars, anchor second-pass note pitches to local dominant first-pass pitch track to reduce pitch drift.

This preserves the existing pipeline structure and diagnostics, and does not loosen global cleanup thresholds.

## Outcome

- Hysteria onset recall target was recovered materially (`onset_f1_ms` 0.1461 -> 0.3743, above 0.22).
- Pitch preservation goal was only partially met: Hysteria pitch accuracy remains below the requested `>= 0.30` target (final `0.2803`).
- Trooper kept strong pitch performance overall (`0.6404`) while onset increased (`0.4586`).

## Remaining Dominant Error Source

Primary remaining error source is still upstream transcription quality for short dense passages (raw BasicPitch note under-generation and incorrect dense-bar pitch content), not downstream octave stabilization.
