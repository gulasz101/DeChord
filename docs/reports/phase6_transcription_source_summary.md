# Phase 6 Transcription Source Summary

## Hysteria

- Notes from `basic_pitch`: `193`
- Notes from `dense_note_generator`: `333`
- Notes from `hybrid_merged`: `45`
- Accepted dense-note candidates: `378`
- Rejected dense-note candidates: `105`
- Accepted dense candidates with reference onset match: `359`
- Accepted dense candidates with reference onset+pitch match: `21`
- Accepted dense candidates with matched onset but wrong pitch: `338`
- Top rejection reasons: `duplicate_existing_note=31, weak_local_support=74`
- Assessment: dense-note additions improved onset coverage materially, but the added notes were overwhelmingly pitch-noisy and reduced final pitch accuracy.

## Trooper

- Status: `benchmark_timeout`
- Command did not finish within a reasonable local benchmark window after the Phase 6 onset-cap tune.
- Assessment: the current dense-note generator path is still too expensive on this benchmark to complete deterministic evaluation reliably.
