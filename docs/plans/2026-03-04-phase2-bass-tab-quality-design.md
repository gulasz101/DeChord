# Phase 2 Bass Tab Quality Upgrade Design

**Date:** 2026-03-04  
**Status:** Approved for implementation planning  
**Scope:** Backend tab generation quality improvements with drums-driven rhythm grid, AlphaTex output, and dedicated stems-to-tab endpoint.

---

## Goal

Improve bass tab generation quality so output is rhythmically aligned, musically readable, playable on bass, and synchronized reliably with app audio.

## Approved Decisions

- Switch tab artifact format to `alphatex` as primary output for new generation.
- Keep `song_midis` persistence for future features and debugging.
- Add dedicated endpoint `POST /api/tab/from-demucs-stems` (single responsibility).
- Use `\sync` points every 8 bars by default (plus first and last bar).
- No backward compatibility effort for legacy `gp5` data in local development.

## Architecture

Add modular services in `backend/app/services/`:

- `rhythm_grid.py`
  - Extract beats/downbeats from drums stem.
  - Build bar grid from downbeats, fallback to grouped beats.
  - Reconcile BPM hint with derived BPM.

- `bass_transcriber.py`
  - `BassTranscriber` interface.
  - `BasicPitchTranscriber` implementation wrapping existing MIDI path.
  - Return raw note events plus MIDI bytes for persistence.

- `note_cleanup.py`
  - Monophony enforcement.
  - Noise filtering by duration/confidence.
  - Merge near-adjacent repeated notes.
  - Optional octave-jump correction.

- `quantization.py`
  - Quantize note timing to drums-derived bar grid.
  - Default subdivision: 1/16.
  - Split cross-bar notes.

- `fingering.py`
  - Candidate `(string, fret)` generation for E1/A1/D2/G2.
  - Dynamic programming solver for playable path optimization.

- `alphatex_exporter.py`
  - Emit AlphaTex score with tempo, time signature, tuning, measures, notes.
  - Emit `\sync` entries based on bar starts (bar 0, every 8 bars, last bar).

- `tab_pipeline.py`
  - Compose all services end-to-end.

## Data Flow

1. Input stems: `bass.wav` and `drums.wav`.
2. Rhythm extraction from drums (authoritative timing).
3. Bass transcription to raw notes + MIDI bytes.
4. Cleanup passes on raw notes.
5. Beat-grid quantization with bar-aware snapping.
6. Fingering optimization (DP).
7. AlphaTex generation with sync points.
8. Persistence:
   - MIDI in `song_midis`.
   - AlphaTex text bytes in `song_tabs` with `tab_format='alphatex'`.

## API Plan

### New endpoint

`POST /api/tab/from-demucs-stems`

Input:
- Required: `bass.wav`, `drums.wav`
- Optional: `bpm`, `time_signature`, `subdivision`, `max_fret`

Output:
- `alphatex`
- `tempo_used`
- `bars`
- `sync_points`
- `debug_info`

### Existing analyze flow

`/api/analyze` in `analysis_and_stems` mode will reuse the same tab pipeline after stems are produced, then persist MIDI + AlphaTex.

## Error Handling

- Prefer `madmom` (`RNNDownBeatProcessor` + `DBNDownBeatTrackingProcessor`) for beat/downbeat extraction.
- Fallback to `librosa.beat.beat_track` and infer downbeats in 4/4 when needed.
- Return clear 4xx/5xx errors for missing stems, invalid rhythm extraction, or empty playable note results.
- Include `debug_info` counters and drop reasons.

## Testing Strategy

Add tests for:
- rhythm extraction monotonic timestamp guarantees.
- bar-grid construction and BPM reconciliation.
- cleanup behavior (overlap/noise/merge).
- quantization error bounds and bar splitting.
- fingering solver movement constraints.
- AlphaTex sync generation validity.
- API endpoint contract and persistence of `alphatex` format.

## Rollout and Verification

- Implement incrementally with strict TDD (test first, fail, minimal implementation, pass).
- Use subagent-driven development for implementation tasks.
- After development and pre-handoff verification, run local reset workflow: `make reset`.

---

## Brainstorming Task Checklist

- [x] Explore project context and current pipeline integration points.
- [x] Gather and confirm key rollout constraints with user.
- [x] Compare approaches and secure approval for recommended option.
- [x] Present architecture, data flow, error handling, and testing sections for approval.
- [x] Record approved design in `docs/plans`.
