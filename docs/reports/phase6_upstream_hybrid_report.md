# Phase 6 Upstream Hybrid Report

## 1. Metrics Table

| Song | Stage | onset_f1_ms | pitch_accuracy | octave confusion | note_density_correlation |
| --- | --- | ---: | ---: | --- | ---: |
| Hysteria | Phase 5 final | 0.3201 | 0.3178 | 82/0/26/150 | 0.2829 |
| Hysteria | Phase 6 final | 0.5191 | 0.2227 | 106/3/48/319 | 0.2683 |
| Trooper | Phase 5 final | 0.4337 | 0.6574 | 332/0/4/169 | 0.0155 |
| Trooper | Phase 6 final | timeout | timeout | timeout | timeout |

## 2. Source Contribution Summary

### Hysteria

- Notes from BasicPitch: `193`
- Notes from dense-note generator: `333`
- Accepted hybrid additions: `378`
- Rejected dense-note candidates: `105`
- Top rejection reasons: `duplicate_existing_note=31, weak_local_support=74`
- Impact: dense-note additions increased reference-onset coverage (`359` onset matches) but only `21` of those matched both onset and pitch.

### Trooper

- Benchmark status: `timeout`
- Accepted hybrid additions: `N/A`
- Rejected dense-note candidates: `N/A`
- Top rejection reasons: `N/A`
- Impact: unable to measure because the benchmark did not complete after the upstream hybrid generator was enabled.

## 3. Conclusion

- Hybrid upstream generation does **not** materially help in its current form.
- Hysteria gained onset recall but lost pitch accuracy badly versus Phase 5 (`0.3178 -> 0.2227`).
- Trooper could not be benchmarked to completion after enabling the dense-note generator, which makes the current approach operationally unsafe on the canonical dense benchmark.
- The dominant remaining bottleneck is still upstream transcription quality, but this experiment shows that lightweight onset-plus-local-f0 generation is too noisy and too expensive without a stronger pitch model or a much stricter candidate-selection design.
