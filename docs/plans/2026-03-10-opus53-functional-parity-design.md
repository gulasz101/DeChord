# Opus 5-3 Functional Parity Design

## Task Checklist

- [x] Confirm redesign baseline remains `designs.opus46/5-3`.
- [x] Confirm pre-refactor MVP functionality must remain available after redesign.
- [x] Confirm manual stem upload is only valid inside an existing song context.
- [x] Identify redesign regressions against the previous single-page MVP.
- [x] Select restoration strategy: keep 5-3 surfaces and rewire real MVP behavior behind them.
- [x] Define song upload flow in 5-3 language.
- [x] Define song-scoped stem upload flow in 5-3 language.
- [x] Define player parity requirements for comments, playback, tabs, stems, and persistence.

## Goal

Restore all user-facing functionality that existed in the pre-refactor single-page MVP while preserving the Opus 5-3 route structure and visual language, and extend the redesign with a new song-scoped manual stem upload flow.

## Context

The redesign shipped on Monday, March 9, 2026 and replaced the old single-page MVP shell with route-driven pages inspired by `designs.opus46/5-3`. The previous MVP was functionally complete for core workflows: song upload, upload progress, stem failure warnings, notes CRUD, playback preference persistence, stem playback, tab viewing, and artifact download. The redesign preserved backend routes and some frontend API utilities, but several surfaces became presentation-only.

## Gap Summary

### Regressions introduced by redesign

- `SongLibraryPage` visually shows song upload controls but is not wired to file input, API upload, polling, progress, errors, or warnings.
- `SongDetailPage` exposes `Upload Stem`, `Generate Stems`, and `Generate Bass Tab` actions as static buttons without connected behavior.
- `PlayerPage` uses simulated playback instead of real audio playback, uses a mock tab source, and does not persist playback preferences.
- Comments are display-only in the redesign; the MVP supported create, edit, and delete for timed and chord notes.
- Stem playback switching and per-stem enablement are no longer connected to the real audio player.
- Tab download and real tab availability handling are no longer represented in the redesign shell.

### Functionality that already exists and should be reused

- Backend upload and analysis pipeline: `/api/analyze`, `/api/status/{job_id}`, `/api/result/{job_id}`.
- Song detail APIs for stems, tabs, notes, playback prefs, audio, and downloads.
- Frontend API client helpers and audio player primitives from the previous MVP.

## Chosen Approach

Restore MVP behavior behind the existing Opus 5-3 pages instead of reintroducing the old MVP layout or rebuilding the redesign state model from scratch.

### Why this approach

- Preserves the route-driven information architecture and visual language already approved in `5-3`.
- Reuses stable backend contracts and much of the previous frontend logic.
- Minimizes churn by replacing disconnected presentation-only state with real data and real side effects.
- Keeps scope targeted: functional parity plus one explicitly requested new stem-upload capability.

## UX Design

### Song Library Upload Flow

`SongLibraryPage` keeps the Opus 5-3 editorial card layout and purple/teal glass styling, but the upload panel becomes a real interaction surface.

Behavior:
- `+ Upload Song` toggles the upload card.
- The upload card supports click-to-browse and drag/drop.
- Process mode and tab quality controls remain visible and styled like the design.
- Selecting a file starts the same upload path the MVP used.
- While processing, the card shows stage label, overall progress, and stage progress in-place.
- Upload errors and stem warnings are shown in the same card rather than a detached global message.
- On completion, project songs refresh and the newly uploaded song becomes the active detail target.

### Song Detail Stem Upload Flow

Manual stem upload is only available from `SongDetailPage`.

Behavior:
- `Upload Stem` opens a compact inline panel below the stem action row in the same 5-3 language.
- Required fields: audio file, stem name, description.
- Submission uploads the stem against the current song only.
- On success, the stems list refreshes immediately and the new item appears as a `User` stem with uploader metadata and description.
- The flow never creates a new song.

Visual treatment:
- Same border radius, translucent panels, Playfair headers, muted silver text, and purple call-to-action accents used elsewhere in `5-3`.
- Inputs are dark glass fields, not default browser controls dropped naked into the page.

### Player Functional Parity

`PlayerPage` keeps the current 5-3 spatial layout: top nav, main timeline/tab area, optional side panel, and transport footer. Behind that layout, the logic returns to the real MVP behavior.

Behavior to restore:
- Real full-mix and stems playback via `useAudioPlayer`.
- Real tab file source instead of mock AlphaTex.
- Real note markers derived from API-backed notes.
- Real timed/chord comment create, edit, and delete flows.
- Real loop handling, seek, speed, and volume controls.
- Real playback preference persistence to the backend.
- Real stem side panel controlling enabled playback stems.

## Technical Design

### Frontend state strategy

Keep `App.tsx` as the top-level controller for route transitions and API orchestration, but move real upload/player/detail handlers into the redesign routes through explicit props instead of hidden local mock state.

Key principle:
- Redesign pages own presentation state.
- `App.tsx` owns API state, route transitions, and persistence.

### Backend extension

Add one new backend route for song-scoped manual stem uploads.

Proposed contract:
- `POST /api/songs/{song_id}/stems`
- multipart form fields: `file`, `stem_name`, `description`

Expected backend responsibilities:
- Validate song existence.
- Store uploaded audio under the existing stems storage strategy.
- Insert a `song_stems` row with `stem_key`, stored path, mime type, and optional duration.
- Return enough metadata for the frontend to reload or optimistically display the new stem.

### Mapping user stems into redesign data

The redesign stem card model supports label, source type, uploader name, description, version, and archive state. Existing system stems returned from `/api/songs/{song_id}/stems` need to continue mapping cleanly, and manual uploads will be mapped as user stems in the redesign layer.

## Testing Design

TDD is mandatory for implementation work.

Coverage to add:
- Backend test for song-scoped stem upload endpoint and persistence.
- Frontend test for `SongLibraryPage` real upload interactions and handler wiring.
- Frontend integration test for `App.tsx` upload flow through redesigned song library.
- Frontend tests for `SongDetailPage` manual stem upload UI.
- Frontend integration tests for player route behavior that uses real audio/tab URLs and note actions.

## Non-Goals

- No auth redesign beyond the current identity model.
- No new standalone stem-only entity outside song context.
- No visual departure from Opus 5-3 language.
- No broad backend schema redesign beyond what is required to persist manual stems correctly.
