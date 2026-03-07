# Hysteria Phase 4 Stage Attribution

## Stage Metrics

| stage | note_count | onset_precision | onset_recall | onset_f1 | pitch_accuracy | repeated_note_bars | avg_notes_per_dense_bar |
|---|---:|---:|---:|---:|---:|---:|---:|
| raw_transcriber_output | 182 | 0.1978 | 0.0269 | 0.0473 | 0.2941 | 38 | 2.45 |
| post_phase3_octave_stabilization | 182 | 0.1978 | 0.0269 | 0.0473 | 0.3000 | 38 | 2.45 |
| post_onset_recovery | 185 | 0.2000 | 0.0276 | 0.0486 | 0.3023 | 38 | 2.49 |
| post_cleanup | 309 | 0.2686 | 0.0620 | 0.1007 | 0.2422 | 72 | 3.58 |
| post_quantization | 339 | 0.9174 | 0.2323 | 0.3707 | 0.2540 | 73 | 3.93 |
| post_fingering_final | 339 | 0.9174 | 0.2323 | 0.3707 | 0.2540 | 73 | 3.93 |

## Phase 4B Conclusion

- Transcription engine: `basic_pitch`.
- Missing notes in raw BasicPitch output: 1303 (raw onset recall 0.0269).
- Missing notes in final output: 1028 (final onset recall 0.2323).
- Largest recall drop stage: `raw_transcriber_output` -> `post_phase3_octave_stabilization` (delta 0.0000).
- Missing-note concentration (final): repeated-same-pitch 22.96%, short-note 99.71%, dense-bar 65.47%.
