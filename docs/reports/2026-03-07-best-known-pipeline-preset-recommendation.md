# 2026-03-07 Best-Known Pipeline Preset Recommendation

## Scope

- Branch: `codex/stems-demucs-env-config`
- Benchmark songs:
  - `./test songs/Muse - Hysteria.mp3`
  - `./test songs/Muse - Hysteria.gp5`
  - `./test songs/Iron Maiden - The Trooper.mp3`
  - `./test songs/Iron Maiden - The Trooper.gp5`
- Goal: codify the best stable operating profiles that were already demonstrated in repo history, not invent a new architecture or new heuristic family.

## Benchmark History Reviewed

The recommendation below is based on the current code/config surfaces plus these prior reports and artifacts:

- `docs/reports/2026-03-07-bass-analysis-benchmark.md`
- `docs/reports/2026-03-07-pitch-stability-benchmark.md`
- `docs/reports/2026-03-07-note-admission-tightening-benchmark.md`
- `docs/reports/2026-03-07-onset-note-generator-benchmark.md`
- `docs/reports/2026-03-07-onset-region-pitch-estimation-benchmark.md`
- `docs/reports/2026-03-07-upstream-raw-note-recall-benchmark.md`
- `docs/reports/phase4_onset_recovery_report.md`
- `docs/reports/phase5_dense_bar_fusion_report.md`
- `docs/reports/phase6_upstream_hybrid_report.md`

## Historical Best-Known Results And Tradeoffs

### Muse - Hysteria

| configuration | F1 | recall | pitch accuracy | practical status | assessment |
| --- | ---: | ---: | ---: | --- | --- |
| `onset_upstream_enabled` | `0.5399` | `0.3786` | `0.1775` | completed on Hysteria only | highest historical Hysteria F1, but too pitch-noisy and not practical on Trooper |
| `phase6_hysteria_final` | `0.5191` | `0.3555` | `0.2227` | Trooper timed out | still operationally unsafe despite strong Hysteria recall |
| `phase5_hysteria_final` | `0.3201` | `0.1927` | `0.3178` | completed | best historical compromise before current branch drift |
| `benchmark_std_refinement` | `0.1910` | `0.1060` | `0.3380` | completed | safest current baseline evidence |

Conclusion:

- The best Hysteria F1/recall ever seen in repo history came from onset-heavy and Phase 6 style paths.
- Those paths are not suitable as defaults because the paired Trooper runs did not complete practically.
- The last clearly practical Hysteria compromise in history was the Phase 5 profile, which kept materially better pitch than the onset-heavy variants.

### Iron Maiden - The Trooper

| configuration | F1 | recall | pitch accuracy | practical status | assessment |
| --- | ---: | ---: | ---: | --- | --- |
| `phase4_trooper_final` | `0.4586` | `0.3366` | `0.6404` | completed | best historical pure F1 on Trooper |
| `phase5_trooper_final` | `0.4337` | `0.3119` | `0.6574` | completed | best historical practical compromise because pitch improved while recall stayed strong |
| `benchmark_std_refinement` | `0.3799` | `0.2520` | `0.7402` | completed | safest high-pitch baseline |
| `benchmark_std_full` | marginal gain over refinement | marginal gain | worse runtime | completed | rejected because ensemble cost exceeded 100s extra per song |

Conclusion:

- Trooper does not justify onset-heavy or sparse-boost defaults.
- Phase 5 remains the best practical historical target shape: slightly less F1 than Phase 4, but better pitch.
- Single-model refinement is the safest baseline; full ensemble remains a bad default because the gain is small and the runtime cost is extreme.

## Configurations Explicitly Rejected

- Full analysis-stem ensemble as a default.
  - Evidence: `docs/reports/2026-03-07-bass-analysis-benchmark.md` showed only small gains while adding about `+102.86s` on Hysteria and `+122.82s` on Trooper.
- Upstream raw sparse-boost as a default.
  - Evidence: `docs/reports/2026-03-07-upstream-raw-note-recall-benchmark.md` showed Hysteria gains, but Trooper sparse-boost runs were too slow to finish practically.
- Onset-note-generator as a default.
  - Evidence: `docs/reports/2026-03-07-onset-note-generator-benchmark.md` showed Hysteria gains but Trooper did not complete practically.
- Phase 6 style dense-note-generator defaulting.
  - Evidence: `docs/reports/phase6_upstream_hybrid_report.md` showed Hysteria onset gains with materially worse pitch and a Trooper timeout.

## Features That Held Up Versus Features That Did Not

Consistently useful:

- Single-model analysis-stem refinement as the safe baseline path.
- Conservative note admission instead of the earlier permissive dense-candidate acceptance.
- Pitch stability when paired with a bounded aggressive profile instead of free-running dense generation.
- Aggressive second-pass dense-bar recovery only when the dedicated dense-note-generator branch stays disabled.

Consistently harmful or unsafe as defaults:

- Full ensemble reseparation.
- Raw sparse-region recall boost.
- Upstream onset generation.
- Dense-note-generator defaulting in general-use profiles.

## Preset Recommendation

No single preset is best for both songs.

- `distorted_bass_recall` is the best current practical preset for Hysteria-like distorted bass material on this branch.
- `balanced_benchmark` is the recommended general-use preset because it avoids the known unsafe paths while still keeping much more Trooper performance than the safe baseline.
- `stable_baseline` is the safest fallback when pitch stability and bounded behavior matter more than recall.

## Exact Preset Mapping

### `stable_baseline`

Purpose:

- safest current baseline
- bounded runtime
- no pathologically expensive behavior

Intended pairing:

- quality mode: `standard`
- benchmark harness config: `refinement`

Low-level mapping:

- `DECHORD_PITCH_STABILITY_ENABLE=0`
- `DECHORD_NOTE_ADMISSION_ENABLE=1`
- `DECHORD_RAW_NOTE_RECALL_ENABLE=0`
- `DECHORD_RAW_NOTE_SPARSE_REGION_BOOST_ENABLE=0`
- `DECHORD_ONSET_NOTE_GENERATOR_ENABLE=0`
- `DECHORD_DENSE_NOTE_GENERATOR_ENABLE=0`
- `DECHORD_DENSE_CANDIDATE_MIN_DURATION_MS=120`
- `DECHORD_DENSE_UNSTABLE_CONTEXT_PENALTY=1.0`
- `DECHORD_DENSE_OCTAVE_NEIGHBOR_PENALTY=1.0`
- analysis-stem refinement enabled
- model ensemble disabled
- auto-enable ensemble-by-quality disabled
- benchmark guardrails: resource monitor on, `12000 MB`, `4` child processes, `2.0s` polling

### `balanced_benchmark`

Purpose:

- best all-around compromise across Hysteria and Trooper
- avoids the historically rejected dense-generator drift
- current recommended preset for general use

Intended pairing:

- quality mode: `high_accuracy_aggressive`
- benchmark harness config: `baseline`

Low-level mapping:

- `DECHORD_PITCH_STABILITY_ENABLE=1`
- `DECHORD_NOTE_ADMISSION_ENABLE=1`
- `DECHORD_RAW_NOTE_RECALL_ENABLE=0`
- `DECHORD_RAW_NOTE_SPARSE_REGION_BOOST_ENABLE=0`
- `DECHORD_ONSET_NOTE_GENERATOR_ENABLE=0`
- `DECHORD_DENSE_NOTE_GENERATOR_ENABLE=0`
- `DECHORD_DENSE_CANDIDATE_MIN_DURATION_MS=120`
- `DECHORD_DENSE_UNSTABLE_CONTEXT_PENALTY=1.0`
- `DECHORD_DENSE_OCTAVE_NEIGHBOR_PENALTY=1.0`
- analysis-stem refinement disabled
- model ensemble disabled
- auto-enable ensemble-by-quality disabled
- benchmark guardrails: resource monitor on, `12000 MB`, `4` child processes, `2.0s` polling

Rationale:

- This keeps the aggressive pass and dense-bar fusion behavior that still helps coverage.
- It explicitly suppresses the dedicated dense-note-generator branch that now drifts toward the historically rejected Phase 6 behavior on the current branch.

### `distorted_bass_recall`

Purpose:

- best current practical Hysteria-oriented recall setting
- allowed to trade pitch for recall
- still bounded by the benchmark guardrails

Intended pairing:

- quality mode: `high_accuracy_aggressive`
- benchmark harness config: `baseline`

Low-level mapping:

- `DECHORD_PITCH_STABILITY_ENABLE=1`
- `DECHORD_NOTE_ADMISSION_ENABLE=1`
- `DECHORD_RAW_NOTE_RECALL_ENABLE=0`
- `DECHORD_RAW_NOTE_SPARSE_REGION_BOOST_ENABLE=0`
- `DECHORD_ONSET_NOTE_GENERATOR_ENABLE=0`
- `DECHORD_DENSE_NOTE_GENERATOR_ENABLE=1`
- `DECHORD_DENSE_CANDIDATE_MIN_DURATION_MS=55`
- `DECHORD_DENSE_UNSTABLE_CONTEXT_PENALTY=0.20`
- `DECHORD_DENSE_OCTAVE_NEIGHBOR_PENALTY=0.25`
- analysis-stem refinement disabled
- model ensemble disabled
- auto-enable ensemble-by-quality disabled
- benchmark guardrails: resource monitor on, `12000 MB`, `4` child processes, `2.0s` polling

## Focused Verification Reruns

Commands used:

```bash
cd /Users/wojciechgula/Projects/DeChord/backend
DECHORD_PIPELINE_PRESET=balanced_benchmark uv run python scripts/evaluate_tab_quality.py --song-dir "../test songs" --song "Muse - Hysteria" --quality high_accuracy_aggressive --config baseline --phase preset_verify_balanced_hysteria_final --trace-pipeline --resource-monitor --max-memory-mb 12000 --max-child-procs 4
DECHORD_PIPELINE_PRESET=balanced_benchmark uv run python scripts/evaluate_tab_quality.py --song-dir "../test songs" --song "Iron Maiden - The Trooper" --quality high_accuracy_aggressive --config baseline --phase preset_verify_balanced_trooper_final --trace-pipeline --resource-monitor --max-memory-mb 12000 --max-child-procs 4
DECHORD_PIPELINE_PRESET=distorted_bass_recall uv run python scripts/evaluate_tab_quality.py --song-dir "../test songs" --song "Muse - Hysteria" --quality high_accuracy_aggressive --config baseline --phase preset_verify_distorted_hysteria_final --trace-pipeline --resource-monitor --max-memory-mb 12000 --max-child-procs 4
DECHORD_PIPELINE_PRESET=stable_baseline uv run python scripts/evaluate_tab_quality.py --song-dir "../test songs" --song "Iron Maiden - The Trooper" --quality standard --config refinement --phase preset_verify_stable_trooper_final --trace-pipeline --resource-monitor --max-memory-mb 12000 --max-child-procs 4
```

### Verification Results

| preset | song | F1 | recall | pitch accuracy | total runtime | peak RSS | guardrail status | notes |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| `balanced_benchmark` | `Muse - Hysteria` | `0.1861` | `0.1031` | `0.2391` | `129.64s` | `3174.19 MB` | no threshold exceeded | dense-note-generator stayed off; dense-bar fusion accepted `201/634` |
| `balanced_benchmark` | `Iron Maiden - The Trooper` | `0.3948` | `0.2804` | `0.6542` | `152.72s` | `4478.47 MB` | no threshold exceeded | dense-note-generator stayed off; dense-bar fusion accepted `255/719` |
| `distorted_bass_recall` | `Muse - Hysteria` | `0.3742` | `0.2323` | `0.1125` | `156.30s` | `3479.52 MB` | no threshold exceeded | dense-note-generator dominated accepted notes: source counts `basic_pitch=95`, `dense_note_generator=219`, `hybrid_merged=40` |
| `stable_baseline` | `Iron Maiden - The Trooper` | `0.2110` | `0.1229` | `0.7487` | `125.74s` | `3761.14 MB` | no threshold exceeded | safest pitch-stable fallback, but recall is much lower |

Interpretation:

- `distorted_bass_recall` is the only current branch preset that recovers Hysteria to a meaningfully higher recall level without crossing the benchmark guardrails.
- `balanced_benchmark` holds Trooper near the historical Phase 5 shape while keeping the dedicated dense-note-generator branch off.
- `stable_baseline` remains the safest preset, but the recall drop is large enough that it should not be the general recommendation.

## Final Recommendation

- Recommended preset for general use: `balanced_benchmark`
- Recommended preset for distorted bass experiments: `distorted_bass_recall`
- Recommended preset for safest bounded fallback: `stable_baseline`

Why `balanced_benchmark` is the general recommendation:

- It avoids every configuration family that already proved unsafe or clearly worse in repo history.
- It preserves materially more Trooper quality than the safe baseline.
- It keeps the current branch away from the dense-note-generator drift that caused the Hysteria aggressive default to collapse pitch.

## Single Most Important Remaining Limitation

The repository still does not have one bounded preset that simultaneously reaches historical Hysteria recall and historical Trooper pitch quality.

In practice:

- the bounded Hysteria-oriented preset still collapses pitch too far
- the balanced preset stays safe and practical, but it does not recover Hysteria to the older Phase 4 or onset-heavy recall levels

That tradeoff remains the main unresolved limitation.
