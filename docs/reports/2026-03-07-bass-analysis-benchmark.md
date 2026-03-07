# 2026-03-07 Bass Analysis Benchmark

## Scope

- Songs tested: `Muse - Hysteria`, `Iron Maiden - The Trooper`
- Ground truth: official local `.gp5` bass tabs in `test songs/`
- Tab pipeline held constant: `--quality standard`, BPM hints/subdivision unchanged across runs
- Variable under test: bass-analysis stem configuration only (`baseline`, `refinement`, `full`)

## Commands Run

- `cd backend && uv run python scripts/evaluate_tab_quality.py --song-dir "../test songs" --song "Muse - Hysteria" --quality standard --config baseline --phase benchmark_std_baseline`
- `cd backend && uv run python scripts/evaluate_tab_quality.py --song-dir "../test songs" --song "Muse - Hysteria" --quality standard --config refinement --phase benchmark_std_refinement`
- `cd backend && uv run python scripts/evaluate_tab_quality.py --song-dir "../test songs" --song "Muse - Hysteria" --quality standard --config full --phase benchmark_std_full`
- `cd backend && uv run python scripts/evaluate_tab_quality.py --song-dir "../test songs" --song "Iron Maiden - The Trooper" --quality standard --config baseline --phase benchmark_std_baseline`
- `cd backend && uv run python scripts/evaluate_tab_quality.py --song-dir "../test songs" --song "Iron Maiden - The Trooper" --quality standard --config refinement --phase benchmark_std_refinement`
- `cd backend && uv run python scripts/evaluate_tab_quality.py --song-dir "../test songs" --song "Iron Maiden - The Trooper" --quality standard --config full --phase benchmark_std_full`

## Muse - Hysteria

| Config | F1 | Pitch Acc | Note Diff | Avg Bar Diff | Max Bar Diff | Pitch Mismatch | Onset Mismatch | Octave Errors | Runtime (s) | Selected Model | Ensemble | Guitar Used |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| baseline | 0.1642 | 0.3417 | -1216 | 13.98 | 16 | 79 | 1219 | 12 | 114.10 | raw_bass_stem | 0 | 0 |
| refinement | 0.1910 | 0.3380 | -1191 | 13.69 | 16 | 94 | 1197 | 13 | 114.25 | htdemucs_ft | 0 | 0 |
| full | 0.1910 | 0.3380 | -1191 | 13.69 | 16 | 94 | 1197 | 13 | 216.95 | htdemucs_ft | 1 | 0 |

### Interpretation

- `refinement` vs `baseline`: F1 +0.0268, note diff +25, avg bar diff -0.29, onset mismatches -22, pitch mismatches +15, octave errors +1, runtime +0.16s.
- `full` vs `refinement`: F1 +0.0000, note diff +0, pitch mismatches +0, runtime +102.70s.
- Candidate selection: `htdemucs_ft` won full-mode scoring with scores {"htdemucs": 17.181745056431858, "htdemucs_ft": 17.80515232001625}.
- Guitar-aware subtraction was not exercised; no candidate reported a guitar stem.

## Iron Maiden - The Trooper

| Config | F1 | Pitch Acc | Note Diff | Avg Bar Diff | Max Bar Diff | Pitch Mismatch | Onset Mismatch | Octave Errors | Runtime (s) | Selected Model | Ensemble | Guitar Used |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| baseline | 0.3608 | 0.7546 | -1115 | 6.68 | 11 | 94 | 1236 | 2 | 132.92 | raw_bass_stem | 0 | 0 |
| refinement | 0.3799 | 0.7402 | -1090 | 6.54 | 11 | 106 | 1211 | 4 | 133.97 | htdemucs_ft | 0 | 0 |
| full | 0.3806 | 0.7206 | -1094 | 6.56 | 11 | 114 | 1211 | 2 | 255.74 | htdemucs | 1 | 0 |

### Interpretation

- `refinement` vs `baseline`: F1 +0.0191, note diff +25, avg bar diff -0.15, onset mismatches -25, pitch mismatches +12, octave errors +2, runtime +1.05s.
- `full` vs `refinement`: F1 +0.0007, note diff -4, pitch mismatches +8, runtime +121.77s.
- Candidate selection: `htdemucs` won full-mode scoring with scores {"htdemucs": 14.899198987419048, "htdemucs_ft": 14.696641671586086}.
- Guitar-aware subtraction was not exercised; no candidate reported a guitar stem.

## Cross-Song Answers

- Did the new system improve results: Yes, but only modestly. Single-model refinement improved F1/recall and reduced note-count under-generation on both songs.
- On which song did it help most: `Muse - Hysteria` by F1 gain (`+0.0268` on Hysteria, `+0.0191` on Trooper).
- Did ensemble selection choose different models: Yes. Hysteria full selected `htdemucs_ft`; Trooper full selected `htdemucs`.
- Did guitar-aware subtraction help: Not answerable here. `guitar_assisted_cancellation_available` was `0` in all benchmark runs, so only `other`-stem subtraction actually ran.
- What runtime cost was introduced: refinement added about `+0.16s` on Hysteria and `+1.05s` on Trooper; full ensemble added `+102.86s` and `+122.82s` respectively.
- What errors remain: both songs still massively under-generate notes versus the GP5 references; Hysteria remains recall-limited and Trooper still carries substantial non-octave pitch mismatches despite better onset coverage.

## Failure Modes

- Hysteria remains dominated by missing notes: baseline note diff `-1216`, refinement/full `-1191`.
- Trooper gains more matched notes with refinement (`383` -> `408`) but pitch mismatches also rise (`94` -> `106` -> `114`).
- Ensemble selection is operationally expensive: full-mode analysis build time was `105.34s` on Hysteria and `124.10s` on Trooper.
- Because no benchmark run exposed a guitar stem, the new guitar-aware subtraction path was not validated by these songs and needs a dedicated bleed-heavy sample where Demucs actually emits usable guitar content.

## Recommendation

- Keep single-model refinement as the default experiment branch for now; do not enable ensemble candidate reseparation by default.
- Next engineering step: improve pitch preservation after refinement, especially on Trooper, before spending more runtime on ensemble sweeps. A practical next step is tuning subtraction/gating weights or adding a pitch-preservation guardrail that rejects refinements which worsen transcription pitch mismatches.

## Optional Config D

- Not run. Full mode already added over 100 seconds per song, so extra candidate-model permutations were not runtime-reasonable for this pass.
