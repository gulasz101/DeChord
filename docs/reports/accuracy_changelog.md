# Accuracy Changelog

## Phase 1 (Metrics + Harness)
- Files:
  - `backend/app/services/tab_comparator.py`
  - `backend/app/services/gp5_reference.py`
  - `backend/scripts/evaluate_tab_quality.py`
  - `backend/tests/test_tab_comparator.py`
  - `backend/tests/test_gp5_reference.py`
  - `backend/tests/test_evaluate_tab_quality.py`
- Why:
  - Added canonical full-pipeline evaluator and metrics for onset F1 (ms/grid) and octave confusion.
- Command:
  - `cd backend && uv run python scripts/evaluate_tab_quality.py --song hysteria --quality high_accuracy_aggressive --phase phase1`
- Metrics artifact:
  - `docs/reports/muse__hysteria_after_phase1_metrics.json`

## Phase 2A (Cleanup kwargs reuse + cleanup counters)
- Files:
  - `backend/app/services/note_cleanup.py`
  - `backend/app/services/tab_pipeline.py`
  - `backend/tests/test_note_cleanup.py`
  - `backend/tests/test_tab_pipeline.py`
- Why:
  - Enforced identical BPM-adaptive cleanup params across pass-1/pass-2 and added per-rule cleanup counters.
- Command:
  - `cd backend && uv run python scripts/evaluate_tab_quality.py --song hysteria --quality high_accuracy_aggressive --phase phase2a`
- Metrics artifact:
  - `docs/reports/muse__hysteria_after_phase2a_metrics.json`

## Phase 2B (Production onset recovery + tempo-adaptive params)
- Files:
  - `backend/app/services/onset_recovery.py`
  - `backend/app/services/tab_pipeline.py`
  - `backend/app/main.py`
  - `backend/tests/test_onset_recovery.py`
  - `backend/tests/test_api.py`
  - `backend/tests/test_tab_pipeline.py`
- Why:
  - Added onset recovery service with tempo-adaptive split/tolerance, enabled by default for high-accuracy modes, and exposed additive API controls.
- Command:
  - `cd backend && uv run python scripts/evaluate_tab_quality.py --song hysteria --quality high_accuracy_aggressive --phase phase2b`
- Metrics artifact:
  - `docs/reports/muse__hysteria_after_phase2b_metrics.json`

## Phase 2C (Onset-aware repeated-note merge policy)
- Files:
  - `backend/app/services/note_cleanup.py`
  - `backend/app/services/tab_pipeline.py`
  - `backend/tests/test_note_cleanup.py`
- Why:
  - Prevented same-pitch merges when real onset evidence exists or onset-split tags are present.
- Command:
  - `cd backend && uv run python scripts/evaluate_tab_quality.py --song hysteria --quality high_accuracy_aggressive --phase phase2c`
- Metrics artifact:
  - `docs/reports/muse__hysteria_after_phase2c_metrics.json`

## Metric Snapshot (Phase1/2A/2B/2C)
- `f1_score`: `0.3585`
- `onset_f1_ms`: `0.3585`
- `onset_f1_grid`: `0.3633`
- `pitch_accuracy`: `0.1338`
- `octave_confusion`: exact `40`, `+12`: `47`, `-12`: `6`, other `206`
- `note_density_correlation`: `0.1322`

## Baseline Note
- Pre-change baseline for this branch was recorded from production pipeline run at:
  - `docs/reports/baseline_metrics.json`
  - `docs/reports/baseline_debug.json`
  - `docs/reports/baseline_output.alphatex`
- That baseline was generated on the provided `La Grenade` track (`AGENTS.md` path), while phase artifacts above use the canonical GP5-backed `hysteria` benchmark.
