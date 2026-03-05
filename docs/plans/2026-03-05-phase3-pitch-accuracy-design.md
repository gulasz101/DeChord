# Phase 3 Pitch Accuracy Design

## Scope
Improve bass pitch and octave stability without rewriting the pipeline or replacing BasicPitch.

## Approved Policy
- Fallback transcription path: full Phase 3 treatment.
- BasicPitch path: conservative post-parse octave stabilization only.

## Architecture
### Fallback Path (`backend/app/midi.py`)
- Keep current fallback entrypoint but replace fragile STFT-peak note picking.
- New fallback stages:
1. Framewise `librosa.pyin` pitch + voiced probability extraction.
2. Viterbi-style dynamic-programming smoothing over framewise pitch with heavy octave-jump penalties.
3. Spectral octave verification (`f0` vs `f0/2`) for `f0 > 80Hz`.
4. Onset-segment note construction using median of smoothed framewise pitch.
5. Sequence-level octave stabilization over 1-2s local contour windows.
- Export note events to MIDI as before.
- Emit diagnostics/counters for corrections.

### BasicPitch Path (`backend/app/services/bass_transcriber.py`)
- Keep BasicPitch MIDI generation unchanged.
- After MIDI parsing to `RawNoteEvent`, add conservative ±12 correction pass before cleanup.
- Guardrails:
  - require strong local context,
  - require exact ±12 relation to contour,
  - preserve playable bass range,
  - avoid correction when neighbors confirm large leap.
- Emit `basicpitch_octave_corrections_applied` diagnostics.

### Evaluation Diagnostics (`backend/scripts/evaluate_tab_quality.py`)
- Add `docs/reports/<song>_transcription_audit.json` output.
- Include:
  - `transcription_engine_used`
  - `raw_note_count`
  - `pitch_histogram`
  - `note_duration_histogram`
  - `mean_pitch_confidence`
  - `octave_error_count`
  - `non_octave_pitch_error_count`
  - `fallback_octave_corrections_applied`
  - `basicpitch_octave_corrections_applied`
- Audit error counts computed by onset-matching reference GP5 notes vs pre-cleanup transcription notes.

### Reporting
- Add phase outputs:
  - `hysteria_phase3_baseline_metrics.json`
  - `hysteria_phase3_final_metrics.json`
  - `trooper_phase3_baseline_metrics.json`
  - `trooper_phase3_final_metrics.json`
  - `phase3_pitch_accuracy_report.md`

## Testing Strategy
- TDD on each behavior:
  - fallback smoothing/octave correction helpers;
  - BasicPitch conservative octave correction pass;
  - transcription diagnostics output schema;
  - evaluation audit + phase report generation path behavior.
- Keep tests lightweight with mocks/temp files; no heavy decode in unit tests.

## Risks and Mitigations
- Risk: over-correcting true melodic leaps.
  - Mitigation: strict context guardrails + conservative thresholds on BasicPitch path.
- Risk: fallback compute cost.
  - Mitigation: bounded candidate set, segment-wise DP, vectorized spectral probes.
- Risk: regression in onset metrics.
  - Mitigation: benchmark gate in final report and explicit regression callout.
