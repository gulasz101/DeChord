# DeChord Practice UX Redesign - Design Document

**Date:** 2026-02-28
**Status:** Approved
**Mode:** Single-user localhost (hardcoded default user: `Wojtek`)

## Overview

This redesign evolves DeChord from a basic analyzer player into a persistent practice workstation inspired by Guitar Pro / Go PlayAlong playback ergonomics, while preserving the current upload-and-analyze speed.

## Core Goals

1. Make playback and transport feel more polished and practice-centric.
2. Add harmonic look-ahead on fretboard (current chord + next chord note highlights).
3. Add playback speed control from 40% to 200% in 10% increments.
4. Add timestamp/chord notes that appear as contextual playback toasts.
5. Persist songs, audio data, analysis, notes, and playback preferences.
6. Show clear note markers on playback progress/timeline.

## Product Constraints

- Single user, localhost-only usage for now.
- No auth flow required; default local user record can be auto-created as `Wojtek`.
- Use LibSQL (local SQLite-compatible mode) for persistence.
- Store uploaded audio files directly in DB as BLOB for portability.

## UX Direction

### Visual tone

- Dark “studio desk” aesthetic with restrained accent colors.
- Strong playback hierarchy: transport and playhead clarity first.
- Compact but readable timeline blocks and clear sectioning.

### Layout

- Mobile-first vertical stacking:
  - Header
  - Song library + upload
  - Timeline/progress with note indicators
  - Fretboard
  - Transport controls
- Desktop:
  - Library + controls in side/top region
  - Main timeline area centered
  - Sticky bottom dock for fretboard + transport

### Accessibility

- Keyboard-focus visible for all clickable controls.
- Sufficient contrast on note markers and chord states.
- Hit targets >= 40px on touch interactions.
- Non-color cues for states where appropriate.

## Interaction Design

### Playback

- Speed dropdown values: 40, 50, 60, …, 200 (%).
- Speed persists per song.
- Timeline maintains current chord emphasis and loop state.

### Fretboard

- Current chord notes: primary highlight color.
- Next chord notes: secondary highlight color.
- If note belongs to both, render overlap state (third style).

### Notes and Toasts

1. Timestamp note flow:
   - User clicks playback progress rail.
   - Modal opens with:
     - note text
     - toast duration (seconds)
   - Note is stored at precise time.

2. Chord note flow:
   - User clicks chord block and chooses “Add note”.
   - Modal opens with note text.
   - Toast duration derived from chord duration automatically.

3. Playback toasts:
   - Timestamp notes fire at timestamp and show for configured duration.
   - Chord notes fire when chord becomes active and show through chord duration.
   - Toast queue handles overlaps deterministically.

### Indicators

- Timeline blocks with notes show badge/marker.
- Progress rail displays markers at note times.
- Hover/focus can preview note summary.

## Persistence Architecture

### LibSQL schema

- `users`
  - `id`, `display_name`, timestamps
- `songs`
  - `id`, `user_id`, `title`, `original_filename`, `mime_type`, `audio_blob`, `created_at`, `updated_at`
- `analyses`
  - `id`, `song_id`, `song_key`, `tempo`, `duration`, `created_at`
- `analysis_chords`
  - `id`, `analysis_id`, `chord_index`, `start_sec`, `end_sec`, `label`
- `playback_prefs`
  - `song_id`, `speed_percent`, `volume`, `loop_start_index`, `loop_end_index`, `updated_at`
- `notes`
  - `id`, `song_id`, `type` (`time` or `chord`), `timestamp_sec` (nullable), `chord_index` (nullable), `text`, `toast_duration_sec` (nullable), timestamps

### File strategy

- Audio binary data stored in `songs.audio_blob`.
- API streams audio from DB by `song_id`.
- No dependency on external file paths.

## API Evolution

Keep existing analyze flow but pivot to song-centric IDs.

### Existing flow (adapted)

- `POST /api/analyze` -> persists song+analysis, returns `job_id` and optionally `song_id`.
- `GET /api/status/{job_id}` -> existing polling.
- `GET /api/result/{job_id}` -> analysis payload + `song_id`.

### New endpoints

- `GET /api/songs` -> list persisted songs.
- `GET /api/songs/{song_id}` -> song metadata + latest analysis + notes + prefs.
- `GET /api/audio/{song_id}` -> stream BLOB.
- `DELETE /api/songs/{song_id}` -> remove song and related data.
- `POST /api/songs/{song_id}/notes` -> create note.
- `PATCH /api/notes/{note_id}` and `DELETE /api/notes/{note_id}`.
- `PUT /api/songs/{song_id}/playback-prefs` -> persist speed/volume/loop.

## Frontend Component Architecture

### New components

- `SongLibraryPanel` (list + select + delete + upload entry)
- `PlaybackSpeedSelect`
- `NoteEditorModal`
- `PlaybackNoteMarkers`
- `ToastCueLayer`

### Extended components

- `ChordTimeline`
  - note markers per chord
  - context action for chord note creation
- `Fretboard`
  - current vs next chord highlighting
- `TransportBar`
  - speed dropdown
  - richer control grouping

### State strategy

- `selectedSongId` controls loaded context.
- Playback and sync remain in hooks.
- Notes and prefs are server-backed and cached in React state.

## Error Handling

- Graceful fallback when DB unavailable.
- Show non-blocking toast/error banners for note save failures.
- Prevent note creation if analysis not loaded.
- Handle missing/invalid audio blob responses.

## Testing Strategy

### Backend

- DB migration tests.
- Songs CRUD tests (including audio blob roundtrip).
- Notes CRUD tests.
- Playback prefs persistence tests.

### Frontend

- Speed selection behavior.
- Note modal creation flows (timestamp/chord).
- Marker rendering on timeline/progress.
- Fretboard dual-highlight rendering logic.

### Integration

- Upload -> analyze -> persist -> reopen from library.
- Replaying persisted song triggers saved toasts correctly.

## Rollout Plan

1. Add DB + migrations + repository layer.
2. Persist uploads/analysis/song reads.
3. Add notes/prefs APIs.
4. Implement frontend library + playback UX upgrades.
5. Add notes/toasts + markers.
6. Final verification and polish.

## Notes on Process Constraints

The requested subagent-driven-development workflow is followed conceptually. True runtime subagent dispatch is unavailable in this environment, so implementation is executed in explicit subagent-style phases with TDD checkpoints.
