# 2026-03-07 Best-Known Pipeline Preset Tuning

- [x] Inspect benchmark history and identify best-known configurations
- [x] Define minimal preset strategy
- [x] Add RED tests for preset parsing / mapping
- [x] Implement preset resolver over existing config surface
- [x] Update docs / README / report scripts if needed
- [x] Run focused verification reruns with resource guardrails
- [x] Write recommendation report
- [x] Run relevant tests
- [ ] Run `make reset`
- [ ] Mark plan complete

## Strategy Notes

- `stable_baseline`
  - Target: safest bounded profile for normal runs.
  - Evidence: single-model refinement beat raw baseline in `docs/reports/2026-03-07-bass-analysis-benchmark.md` with negligible runtime increase, while full ensemble bought almost nothing for over 100s extra runtime per song.
  - Mapping direction: standard quality, analysis-stem refinement on, ensemble off, pitch-stability expansion off, onset/raw dense recall paths off.

- `distorted_bass_recall`
  - Target: recall-oriented Hysteria profile that remains bounded.
  - Evidence: Hysteria aggressive runs and earlier Phase 4 history recover substantially more onsets than the standard baseline; the current aggressive probe stayed within resource guardrails but traded pitch heavily for recall.
  - Mapping direction: high-accuracy-aggressive quality pairing, dense-note generator enabled, onset/raw recall extras still off, resource monitor defaults on for benchmark verification.

- `balanced_benchmark`
  - Target: best all-around compromise across Hysteria and Trooper while avoiding the historically unsafe Phase 6 / sparse-boost regressions.
  - Evidence: Phase 5 was the best historical compromise; the current aggressive probe showed the branch has drifted into dense-note-generator-heavy behavior with much worse pitch, so the preset needs to suppress that path and stay off ensemble.
  - Mapping direction: high-accuracy-aggressive quality pairing, dense-note generator disabled, onset/raw recall extras off, ensemble off, benchmark resource monitor defaults on.

- Explicit rejections from history
  - Full ensemble analysis: tiny gains, huge runtime cost.
  - Upstream raw sparse-boost / Phase 6 hybrid: Hysteria-only gains with Trooper timeout or non-completion.
  - Unbounded onset generator path: Hysteria gain but Trooper non-practical.
