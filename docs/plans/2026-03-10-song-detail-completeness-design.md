# Song Detail Completeness Design

**Date:** 2026-03-10

## XML Tracking

<phase id="song-detail-completeness-design" status="completed">
  <task>[x] Task 1: Define the song-detail asset-management promise and scope.</task>
  <task>[x] Task 2: Compare candidate approaches and recommend the honest asset-management slice.</task>
  <task>[x] Task 3: Specify upload, regenerate, provenance, refresh, and feedback behavior.</task>
  <task>[x] Task 4: Capture testing strategy, done criteria, and deferred work.</task>
</phase>

## Product Promise

The song detail screen must tell the truth about the assets attached to a song. From `SongDetailPage`, a user can upload a replacement or supplemental stem, regenerate system stems from the original mix, regenerate bass tab from a clearly identified source stem, and immediately see which assets are available, where they came from, what the latest generation produced, and whether an action succeeded or failed.

## Scope

This slice is intentionally narrow and centered on `frontend/src/redesign/pages/SongDetailPage.tsx` plus the route-level wiring in `frontend/src/App.tsx`.

In scope:
- make `Upload Stem` a real song-detail action
- make stem provenance honest enough for users to understand system versus manual assets
- make bass-tab provenance and refresh behavior visible on the detail screen
- keep regenerate flows honest by showing actionable success and failure states
- reuse the existing song-detail route shell and existing regeneration endpoints where possible

Out of scope:
- comments create/edit/resolve workflow changes
- rehearsal/player transport work
- global asset job history, retries, background workers, or asset lineage browsers
- broad redesign of band/project/library routes

## Current State

What already exists:
- `frontend/src/App.tsx` loads real song detail data, real stem lists, and can call `regenerateSongStems(...)` plus `regenerateSongTabs(...)`
- `backend/app/main.py` already exposes song detail, stem list/download, tab metadata/file/download, and regeneration endpoints
- `SongDetailPage` already contains inline panels for `Generate Stems` and `Generate Bass Tab`

What is still dishonest or incomplete:
- `Upload Stem` is a dead button
- stem rows are mapped to placeholder provenance values in `mapStem(...)` (`System`, `version: 1`, synthetic uploader)
- `App.tsx` does not load tab metadata into the song-detail route, so the page cannot explain current tab provenance or freshness
- refresh after generation is thin: the UI reports a generic success message, but the page does not explain what changed or which source produced the current tab
- clear error states exist only at the button-panel level, not as a full asset-truth model

## Approaches Considered

### Approach 1: Frontend-only polish over the current backend shape

Behavior:
- wire `Upload Stem` to a minimal endpoint
- keep the current synthetic stem mapping
- show generic toasts or inline success copy after refresh

Pros:
- fastest implementation
- minimal data-model changes

Cons:
- still hides provenance truth behind placeholder labels
- does not explain whether the visible tab came from a system bass stem or a manual upload
- risks another slice that looks finished but still misleads users

### Approach 2: Honest asset-management slice with minimal metadata expansion

Behavior:
- add a real song-scoped upload-stem flow
- expose enough stem metadata for `SongDetailPage` to distinguish manual versus system assets and show recency/version intent honestly
- load current tab metadata into the song-detail route and render provenance next to generation controls
- keep actions synchronous from the page perspective: user starts action, the route refreshes the latest song/stem/tab state, and the UI reports the outcome clearly

Pros:
- matches the approved priority: honest asset management first
- keeps work centered on `SongDetailPage` and `App.tsx`
- reuses current regeneration endpoints instead of inventing a jobs system
- creates a credible base for later comments/player slices without overscoping

Cons:
- needs small backend contract work for upload and metadata truth
- requires coordinated frontend and backend test updates

### Approach 3: Full asset-history workspace on song detail

Behavior:
- add per-asset history, lineage, retries, archived versions, and job history across stems, MIDI, and tabs

Pros:
- strongest long-term asset model

Cons:
- too large for the current slice
- broadens into product-management questions the backend cannot yet answer honestly
- delays fixing the dead `Upload Stem` path and thin provenance cues

## Recommendation

Use **Approach 2: the honest asset-management slice**.

It removes the immediate trust failures without pretending DeChord already has full asset versioning. The slice should add only the minimum metadata and UI needed to make the song-detail page truthful: real upload, real provenance, real refresh, and explicit success/failure outcomes.

## Proposed Behavior

### 1. Real Upload Stem Flow

Entry point:
- the existing `Upload Stem` control in `SongDetailPage`

Recommended behavior:
- clicking `Upload Stem` opens a compact inline panel or file-picker-backed panel on the detail page
- the user chooses a file and a `stem_key` (`bass`, `drums`, `vocals`, `other`, or `guitar` if supported by the backend contract)
- submit calls a new song-scoped upload endpoint rather than routing through the upload journey
- while upload is active, disable duplicate submission and show explicit loading copy
- on success, refresh song detail, stems, and tab metadata in place, then show a success message that names the uploaded stem role
- on failure, keep the panel open and show a specific error message

Truth rules:
- uploaded stems are user assets, not system-generated assets
- upload must not silently claim the tab was refreshed unless a tab action was actually run
- the active-stem model for this slice is one current row per `(song_id, stem_key)`; a manual upload replaces the active row for that key and the page must describe that newest asset as the current active stem

### 2. Generate Stems Flow

Meaning:
- regenerate system stems from the original uploaded mix only

Behavior:
- reuse `POST /api/songs/{song_id}/stems/regenerate`
- keep the current confirmation-panel pattern
- update copy to match the current backend truth: regeneration refreshes the active system stem rows for the generated keys, and because the slice uses one active row per `(song_id, stem_key)`, a regenerated system stem can replace a previously active manual stem for the same key
- after success, refresh the route-level song detail data and surface which system stems are now active
- after failure, preserve the panel and show the backend error

Truth rule:
- the copy must match actual persistence behavior: this slice does not promise side-by-side active manual and system variants for the same key

### 3. Generate Bass Tab Flow

Meaning:
- regenerate MIDI/tab from an explicitly chosen source stem already attached to the song

Behavior:
- reuse `POST /api/songs/{song_id}/tabs/regenerate`
- keep explicit source selection in `SongDetailPage`
- prefer the latest active bass stem by default; if no bass stem exists, allow another eligible uploaded stem only if the backend supports that path honestly
- after success, refresh song detail plus tab metadata, then show success copy naming the selected source stem
- after failure, keep the selected source and show the error inline

Truth rule:
- the page must display the provenance of the current tab after refresh, not just the provenance of the requested action

### 4. Provenance Visibility

The song detail page should expose two kinds of provenance:

Stem provenance:
- source type: system or user-uploaded
- stem role: bass, drums, vocals, guitar, other
- recency marker: timestamp or version label grounded in backend truth
- active versus replaced/archive state only if the backend actually stores it

Tab provenance:
- current tab status (`complete`, `failed`, or absent)
- source stem key used to generate the current tab
- generator/version metadata already returned by the backend
- last updated timestamp

Recommended UI placement:
- keep provenance close to the stem list and tab generation controls
- add a compact "Current bass tab" summary block rather than a separate asset dashboard

## Route Refresh Behavior

Route-level ownership stays in `frontend/src/App.tsx`.

Recommended flow:
1. `App.tsx` loads `getSong(songId)`, `listSongStems(songId)`, and `getSongTabs(songId)` when entering or refreshing the song-detail route
2. `SongDetailPage` remains presentational and receives action callbacks plus hydrated asset metadata
3. after upload, stem regeneration, or tab regeneration, `App.tsx` runs one shared refresh helper for the active song-detail route
4. the helper updates the route only if the user is still on that same song-detail page

Why this matters:
- it keeps route truth in one place
- it avoids stale UI after an action finishes
- it prevents navigation hacks or local page-only patching from diverging from backend state

## Success And Error States

Required success states:
- upload success names the stem role that was added or refreshed
- stem regeneration success confirms the active system stems were refreshed
- tab regeneration success confirms the selected source and updates the visible tab provenance block

Required error states:
- upload failure shows why the file was rejected or could not be persisted
- stem regeneration failure keeps the confirmation panel open and shows the backend error
- tab regeneration failure keeps the selected source visible and explains why generation failed
- route refresh failure after an apparently successful action is shown as a refresh problem, not falsely as action success

## Backend Design Direction

This slice should keep backend expansion minimal.

Recommended additions:
- add a real upload endpoint for song-scoped stems, likely `POST /api/songs/{song_id}/stems/upload`
- expand stem-list responses so the frontend can render honest provenance instead of synthetic placeholders
- preserve and return current tab metadata from `GET /api/songs/{song_id}/tabs`

Recommended backend discipline:
- do not add a new background job system for these song-detail actions
- do not expand into comments or player APIs here
- if schema changes are needed for provenance, keep them limited to the current asset surfaces

## Testing Strategy

### Frontend API tests

- add or extend tests for new upload-stem API helpers and richer stem/tab contract parsing in `frontend/src/lib/__tests__/`

### Frontend component tests

- extend `frontend/src/redesign/pages/__tests__/SongDetailPage.test.tsx`
- cover upload panel/file selection behavior, provenance rendering, current-tab summary, and actionable error/success states

### Route integration tests

- extend `frontend/src/__tests__/App.integration.test.tsx`
- verify song detail loads tab metadata, upload/regenerate actions refresh the route, and navigation remains stable while refreshing the same song

### Backend API tests

- extend `backend/tests/test_api.py`
- cover upload-stem persistence, stem metadata truth, regeneration refresh behavior, and tabs provenance contract

### Manual verification

Use a real song that already has analysis data.

Manual checks:
- open song detail for a processed song
- upload a bass or alternate stem and confirm the stem list refreshes honestly
- regenerate stems and confirm the stem list reflects the real post-action state
- regenerate bass tab from a chosen source and confirm the current-tab summary updates to that source
- verify error copy is actionable when one of the actions fails

## Done Criteria

This slice is done when:
- `Upload Stem` is a real end-to-end flow from the song detail page
- the stem list no longer relies on obviously synthetic provenance labels when backend truth is available
- the page shows current tab provenance and freshness on the song detail screen
- upload/regenerate actions refresh the active song-detail route without requiring navigation away and back
- success and failure states are explicit, accurate, and tied to the action that just ran
- comments workflow remains untouched except for any passive rendering already present

## Risks And Deferred Work

- The current schema may not support full historical lineage; this slice should expose current truth, not invent hidden history.
- If backend persistence can only store one active stem per `stem_key`, the UX copy must reflect replacement/supersession rather than preservation.
- Comments, rehearsal flows, and broader asset-history UX are deliberately deferred to later slices.

## Decision Summary

- make `Upload Stem` real on `SongDetailPage`
- expose honest stem and tab provenance instead of placeholders
- reuse existing regeneration endpoints and the route-level app shell
- refresh the active song-detail route after every asset action
- keep scope centered on asset truth, not comments or a full asset-workspace rebuild
