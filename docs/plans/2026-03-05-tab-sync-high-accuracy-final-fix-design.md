# Tab Sync + High Accuracy Final Fix Design

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:writing-plans to create an implementation plan from this design.

**Goal:** Eliminate alphaTab end-of-track drift and improve note recall in quiet sections by adding metrical-level beat-grid correction plus an aggressive suspect-silence pass.

**Scope:**
- Extend quality modes to include `high_accuracy_aggressive`.
- Correct drum-derived beat grids when they are at half-time/double-time relative to canonical song BPM.
- Keep alphaTex tempo canonical (`song_bpm`) while anchoring sync points to corrected absolute bar-start offsets.
- Expose tab quality setting in advanced upload settings and propagate through API/job metadata.
- Add backend/frontend tests plus real-track validation diagnostics.

**Non-Goals:**
- No changes to chord progression pipeline.
- No fingering DP weight changes.
- No frontend playback time-position hacks.

## Problem Analysis

1. **Drift root cause:** bar construction depends on rhythm-extracted beat/downbeat arrays that may represent wrong metrical level. When bar count is too low/high, alphaTab runs out of bars before audio ends even if chord timeline remains correct.
2. **Missing notes root cause:** empty bars can be false negatives in low-amplitude passages where a single global RMS threshold misses local context.

## Proposed Architecture

1. **Quality Mode Expansion**
- Add `tab_generation_quality_mode: Literal["standard", "high_accuracy", "high_accuracy_aggressive"]`.
- `standard`: unchanged one-pass flow.
- `high_accuracy`: existing global-median RMS suspect pass.
- `high_accuracy_aggressive`: suspect on `(notes_per_bar == 0) AND (rms-trigger OR onset-trigger)` where:
  - `rms-trigger`: `bar_rms >= local_median_rms(±8 bars) * 0.9`
  - `onset-trigger`: `onset_peaks >= 2` (from onset-strength peak count)
- Re-transcribe suspect windows `[start-0.2s, end+0.2s]`, merge, then cleanup+quantize.

2. **Beat Grid Metrical Correction**
- Compute `beat_bpm_raw = 60 / median(diff(beats))`.
- Compare to canonical `song_bpm` (`bpm_hint` / analysis tempo) with 15% tolerance.
- Correction rules:
  - near `2x`: downsample beats/downbeats by factor 2 (`double_time`).
  - near `0.5x`: insert beat midpoints and infer downbeats (`half_time`).
  - otherwise none.
- Build bars from corrected beats/downbeats only.

3. **Sync Anchoring**
- Export `\tempo` as canonical song BPM.
- Emit sync points from corrected bars every N bars + final bar.
- If final bar starts too early (`audio_duration_sec - last_bar_start > bar_duration`), append empty bars by inferred bar duration until last start is within one bar from audio end.
- Record `tab_last_sync_ms`, `audio_duration_sec`, `total_bars` and validate diff bound.

4. **API/UI Integration**
- Extend frontend type + radio options for third mode.
- Always send selected `tabGenerationQuality` to API.
- Extend backend form literals for both `/api/analyze` and `/api/tab/from-demucs-stems`.
- Persist selected quality in job metadata; pass to pipeline unchanged.

## Testing Strategy

1. Unit test for metrical correction (`double_time` beats corrected to song BPM and end sync near audio duration).
2. Unit test for aggressive suspect-silence where onsets trigger re-pass despite low RMS, while `high_accuracy` does not.
3. API tests for new literal mode acceptance/forwarding.
4. Frontend tests for payload + advanced settings rendering.
5. Real-track validation run (`Clara Luciani - La grenade`) capturing required diagnostics and alphaTex excerpt.

## Risks and Mitigations

- **Onset dependency availability (`librosa`)**: provide safe fallback to zero peaks + diagnostics field if unavailable.
- **Over-triggering aggressive mode**: keep thresholds conservative and localized; include per-bar diagnostics for tuning.
- **Bar extension side effects**: append only when gap exceeds one inferred bar; avoid altering existing bar boundaries.
