# Upload Modes + Stem Playback Design Document

**Date:** 2026-03-02
**Status:** Proposed

## Request Summary

Add two upload modes:
1. Upload and analyze for chords only.
2. Upload, analyze for chords, and also split to stems.

If stems exist for a song, playback should use stems (all enabled by default), and UI should allow muting/selecting stems (checkboxes preferred). Upload progress must show real processing progress for both chord analysis and stem separation.

## Current Context (DeChord)

- Backend has async job flow: `POST /api/analyze` + `GET /api/status/{job_id}` + `GET /api/result/{job_id}`.
- Job progress is currently text-only (`"Analyzing audio..."`) and not numeric.
- Frontend upload flow polls `/api/status/{job_id}` and renders spinner + status text in `DropZone`.
- Playback currently uses a single `HTMLAudioElement` and one source URL (`/api/audio/{song_id}`).

## Demucs-Gui Analysis (Reference)

`./Demucs-Gui` uses:
- `demucs.api.Separator(...)` for model loading and separation.
- `separator.update_parameter(..., callback=self.updateProgress)` with callback-driven incremental progress.
- A computed total progress value from model/shift/segment offsets, then UI progress bars update from that numeric value.
- FFmpeg-compatible read/write pipeline and explicit status transitions (`reading`, `separating`, `writing`, `finished`, `failed`).

## Approaches Considered

### Approach A: Synchronous stem split inside existing analysis job

- One worker thread runs: analyze chords -> split stems -> persist -> complete.
- Pros: minimal API changes, single job id.
- Cons: long-running request lifecycle with coarse failure recovery and poorer observability.

### Approach B (Recommended): Multi-stage pipeline under one job with structured stage progress

- Keep one job id, but track stages and weighted numeric progress.
- Stages: `upload_saved -> chord_analysis -> stem_separation (optional) -> persist -> complete`.
- Expose structured status payload with `stage`, `progress_pct`, `stage_progress_pct`, and detail text.
- Pros: best UX, easy polling contract, easy to show true progress for both analysis and stems.
- Cons: moderate refactor of job schema and frontend progress UI.

### Approach C: Separate jobs for analysis and stems

- First job for analysis, optional second job for stems.
- Pros: independent retries.
- Cons: more frontend complexity and orchestration; harder single-progress UX.

## Recommended Design

Use Approach B.

### Backend

1. Add upload mode flag to `POST /api/analyze`:
- `process_mode=analysis_only | analysis_and_stems`

2. Extend in-memory job schema:
- `status`: `queued|processing|complete|error`
- `stage`: `queued|analyzing_chords|splitting_stems|persisting|complete|error`
- `progress_pct`: `0..100` (overall)
- `stage_progress_pct`: `0..100` (current stage)
- `message`: human text
- `result.song_id`, `error`

3. Integrate Demucs separation service inspired by Demucs-Gui:
- Add `app/stems.py` with a service wrapping `demucs.api.Separator`.
- Use callback-based progress updates from Demucs internals to produce real stage progress.
- Save stems to per-song folder under backend storage, then register metadata in DB.

4. Progress weighting (initial):
- Chord analysis: 40%
- Stem splitting: 55% (only when requested)
- Persist/finalization: 5%
- For `analysis_only`, remap to 95%+5%.

5. Persist stems metadata:
- New table(s): `song_stems` and optionally `stem_jobs` history.
- Store `song_id`, `stem_key` (`vocals`, `drums`, `bass`, `other`, etc.), file path/mime, duration.

6. Add API endpoints:
- `GET /api/songs/{song_id}/stems` to list available stems.
- `GET /api/audio/{song_id}/stems/{stem_key}` to stream a stem.

### Frontend

1. Upload UI:
- Add mode selector near drop zone:
  - `Analyze chords only`
  - `Analyze + split stems`

2. Progress UI:
- Replace spinner-only view with stage-aware progress bar.
- Show:
  - overall percentage
  - current stage label
  - stage percentage and detail text

3. Stem playback UI:
- Add `StemMixerPanel` with checkboxes per detected stem.
- Default: all stems enabled.
- If no stems, fall back to single mixed track.

4. Playback engine changes:
- Extend `useAudioPlayer` to manage multiple synchronized audio elements for stems.
- One master clock (primary stem) and synchronized seeks/play/pause/rate/volume.
- Track-level mute via element volume 0/1 for now (future: gain sliders).

5. Auto-detection and labels:
- Prefer model-provided stem keys (for Demucs typical 4-stem: drums/bass/other/vocals).
- UI labels derived from keys; unknown keys shown as raw names.

## Error Handling

- If stem split fails but chord analysis succeeds:
  - Mark job complete with warning state in payload (`stems_status=failed`).
  - Song remains usable for chord playback.
- If analysis fails:
  - Job fails and no result.

## Testing Strategy

- Backend TDD:
  - API tests for new analyze mode and status schema.
  - Service tests for stem metadata persistence and fallback behavior.
  - Mock Demucs callback progression to validate numeric progress updates.
- Frontend TDD:
  - Component tests for mode selector and staged progress rendering.
  - Hook tests for multi-source sync and stem toggle behavior.
  - Integration test for upload -> polling -> stem panel visible.

## Constraints and Notes

- Demucs-Gui is GPL-3.0; reuse architecture and integration strategy, not direct code copy.
- Stem splitting is resource heavy; keep default model and parameters conservative.
- This plan assumes local single-user environment as in current app.

## Approval Gate

If this design is accepted, proceed with implementation planning and execution in this order:
`using-superpowers -> brainstorming -> writing-plans -> executing-plans`.
