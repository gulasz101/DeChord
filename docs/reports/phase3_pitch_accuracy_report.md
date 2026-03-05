# Phase 3 Pitch Accuracy Report

Quality mode used for this report: `standard`

## Hysteria

| metric | baseline | final |
|---|---:|---:|
| onset_f1 | 0.3272 | 0.1461 |
| pitch_accuracy | 0.1161 | 0.3774 |
| octave_confusion | {"+12": 44, "-12": 6, "exact": 31, "other": 186} | {"+12": 0, "-12": 12, "exact": 40, "other": 54} |
| note_density_corr | 0.1138 | 0.1746 |

## Trooper

| metric | baseline | final |
|---|---:|---:|
| onset_f1 | 0.3886 | 0.3508 |
| pitch_accuracy | 0.0069 | 0.7561 |
| octave_confusion | {"+12": 185, "-12": 0, "exact": 3, "other": 247} | {"+12": 0, "-12": 1, "exact": 279, "other": 89} |
| note_density_corr | -0.0904 | 0.1353 |

## Transcription Diagnostics

- Hysteria engine: `basic_pitch`; octave errors: 6; non-octave errors: 167
- Trooper engine: `basic_pitch`; octave errors: 4; non-octave errors: 347
