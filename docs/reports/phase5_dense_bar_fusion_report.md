# Phase 5 Dense-Bar Fusion Report

## 1. Metrics Table (Phase 4 Final vs Phase 5 Final)

| Song | Stage | onset_f1_ms | pitch_accuracy | octave_confusion (exact/+12/-12/other) | note_density_correlation |
| --- | --- | ---: | ---: | --- | ---: |
| Hysteria | Phase 4 final | 0.3743 | 0.2803 | 88/2/27/197 | 0.2583 |
| Hysteria | Phase 5 final | 0.3201 | 0.3178 | 82/0/26/150 | 0.2829 |
| Trooper | Phase 4 final | 0.4586 | 0.6404 | 349/1/8/187 | 0.0883 |
| Trooper | Phase 5 final | 0.4337 | 0.6574 | 332/0/4/169 | 0.0155 |

## 2. Fusion Diagnostics Summary

### Hysteria
- Accepted rescue notes: `398`
- Rejected rescue notes: `230`
- Top rejection reasons: `duplicate_existing_note=121`, `weak_local_support=83`, `pitch_far_from_anchor=26`
- Avg pitch distance from anchor: accepted `7.965`, rejected `9.898`
- Evidence of filtering: rejected set has higher anchor-distance than accepted set and duplicate collisions are heavily removed.

### Trooper
- Accepted rescue notes: `318`
- Rejected rescue notes: `369`
- Top rejection reasons: `duplicate_existing_note=269`, `pitch_far_from_anchor=93`, `weak_local_support=7`
- Avg pitch distance from anchor: accepted `12.733`, rejected `15.644`
- Evidence of filtering: high-distance and duplicate candidates are filtered, reducing octave/other confusion while retaining most onset gains.

## 3. Conclusion

- Dense-bar fusion quality improved pitch precision versus Phase 4 for both songs.
- Onset gains were mostly preserved (Hysteria still above 0.32, Trooper above 0.42), but both dropped from their Phase 4 peaks.
- Target status:
  - Hysteria: onset target met; pitch target (`>=0.32`) narrowly missed (`0.3178`).
  - Trooper: onset target met; pitch target (`>=0.68`) missed (`0.6574`).
- Dominant remaining error source is still upstream transcription under-generation/noise in dense passages; fusion gating can trade precision/recall, but it cannot fully recover missing true notes without stronger upstream note hypotheses.
