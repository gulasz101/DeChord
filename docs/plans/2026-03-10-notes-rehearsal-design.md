# Notes and Rehearsal Design

**Date:** 2026-03-10

## XML Tracking

<phase id="notes-rehearsal-design" status="completed">
  <task>[x] Task 1: Define the note-first rehearsal promise and keep the slice tightly scoped.</task>
  <task>[x] Task 2: Compare rehearsal-slice approaches and recommend the real note workflow first.</task>
  <task>[x] Task 3: Specify architecture for note CRUD, time/chord context, song-detail rendering, player rendering, and honest resolved/open state.</task>
  <task>[x] Task 4: Capture testing strategy, manual verification expectations, done criteria, and deferred risks.</task>
</phase>

## Product Promise

DeChord should let a musician leave a real rehearsal note exactly where the problem happens, then see and manage that same note from both `frontend/src/redesign/pages/SongDetailPage.tsx` and `frontend/src/redesign/pages/PlayerPage.tsx`. The promise for this slice is simple: users can create, edit, delete, and resolve notes tied to either a playback timestamp or a chord index, and the UI must show the true open/resolved state instead of pretending every note is always open.

For this slice, success means:
- real note creation from song detail and player
- real note editing, deleting, and resolving
- real time-linked and chord-linked context
- shared rendering truth between song detail and player
- honest open versus resolved state

## Scope

This slice is intentionally narrow and rehearsal-first rather than collaboration-first.

In scope:
- extend the existing notes backend contract so notes can be resolved and returned with enough metadata for honest rendering
- make notes usable from `frontend/src/redesign/pages/SongDetailPage.tsx`
- make notes usable from `frontend/src/redesign/pages/PlayerPage.tsx`
- support creating notes from the current player time and from the selected or current chord context
- support edit, delete, and resolve actions in both surfaces
- keep route-owned refresh behavior in `frontend/src/App.tsx` so song detail and player stay in sync after note mutations

Out of scope:
- member mentions, unread counts, presence, and activity feeds
- multi-user live cursors or collaborative typing
- notifications, assignments, or threaded discussions
- full rehearsal history analytics or broad DAW-style annotation tooling
- broad project-home collaboration UI

## Current State

What already exists:
- `backend/app/main.py` already exposes create, update, and delete note endpoints
- `frontend/src/lib/api.ts` already wraps create, update, and delete note requests
- `frontend/src/redesign/pages/SongDetailPage.tsx` and `frontend/src/redesign/pages/PlayerPage.tsx` already render notes/comments sidebars from route state
- `frontend/src/App.tsx` already owns song-detail hydration via `loadSongDetails(...)`

What is still incomplete or dishonest:
- notes cannot currently be resolved even though both redesign pages render resolved/open UI affordances conceptually
- the backend `GET /api/songs/{song_id}` note payload does not include author, timestamps suitable for real UI history, or resolved state
- `frontend/src/App.tsx` currently maps every fetched note to `resolved: false` and invents author/time values locally, so note state is not truthful
- song detail and player expose note lists, but they do not yet provide real note mutation entry points
- player note context is visible through markers and chord highlighting, but there is no real authoring workflow from current playback state

## Approaches Considered

### Approach 1: Song-detail comments only

Behavior:
- add CRUD in `SongDetailPage`
- keep `PlayerPage` read-only
- defer time-linked note creation until later

Pros:
- smallest UI change
- easiest to ship quickly

Cons:
- misses the approved goal that notes be usable from both song detail and player
- weak rehearsal value because the best moment to capture a note is while listening
- would likely force a second near-duplicate slice later

### Approach 2: Note-first rehearsal slice with shared note truth

Behavior:
- make the backend note contract truthful first
- add create/edit/delete/resolve from song detail and player
- let the player create notes from current time or current chord
- let song detail show and manage the same note state with the same backend truth
- refresh route-owned song data after every mutation so both surfaces converge on one source of truth

Pros:
- matches the approved direction exactly
- delivers real rehearsal value without drifting into collaboration scope
- builds on existing note APIs and existing route hydration patterns
- creates the right foundation for later unread/activity/member work without prematurely implementing them

Cons:
- requires coordinated backend payload work plus frontend route refresh work
- needs careful UX trimming so player interactions stay lightweight

### Approach 3: Broader collaboration slice now

Behavior:
- combine notes with unread counts, member presence, activity feed entries, and collaboration summaries

Pros:
- more ambitious end state

Cons:
- directly conflicts with the approved instruction to defer member/activity/unread/presence work
- makes it harder to ship honest note behavior quickly
- increases risk of building partial collaboration scaffolding before note truth is solid

## Recommendation

Use **Approach 2: the note-first rehearsal slice with shared note truth**.

This is the smallest vertical slice that makes rehearsal notes genuinely useful. It starts with real note data, exposes real note actions in both song detail and player, links notes to time or chord context, and explicitly defers broader collaboration concerns to Slice 5.

## Architecture and Data Flow

### 1. Backend note contract becomes truthful

`backend/app/main.py` should be the source of truth for note state rather than a minimal placeholder API.

Recommended direction:
- extend note reads from `GET /api/songs/{song_id}` to include `resolved`, `created_at`, `updated_at`, and stable author fields that the frontend can render directly
- extend note mutations with a resolve/unresolve operation rather than overloading text edit semantics
- keep `POST /api/songs/{song_id}/notes`, `PATCH /api/notes/{note_id}`, and `DELETE /api/notes/{note_id}` for CRUD, and add a dedicated resolve route such as `PATCH /api/notes/{note_id}/resolve`
- validate context honestly: time notes require `timestamp_sec`, chord notes require `chord_index`, and resolve should target an existing note only

Truth rule:
- the backend owns whether a note is open or resolved; the frontend must stop synthesizing that state

### 2. Route ownership stays in `frontend/src/App.tsx`

`frontend/src/App.tsx` should continue to own the freshest song-detail state for both song detail and player routes.

Recommended flow:
1. `loadSongDetails(...)` fetches notes, stems, and tab data
2. note payload mapping preserves backend values for `resolved`, author display, and timestamps
3. song-detail and player actions call route-owned note mutation helpers
4. after every successful mutation, `App.tsx` reloads song details and updates the active route if it is still pointing at that song

Why this matters:
- song detail and player must agree on the same note set
- mutations should not fork page-local note caches
- later collaboration work can reuse the same route refresh pattern

### 3. Song detail note workflow

`frontend/src/redesign/pages/SongDetailPage.tsx` should become the management surface for notes when the user is reviewing the song outside active playback.

Recommended behavior:
- add an inline note composer with an explicit context choice
- for this slice, `SongDetailPage` time notes use a manual timestamp entry field in seconds such as `Timestamp (mm:ss or seconds)`; do not depend on a new scrubber, waveform, or player-only control
- keep the Song Detail composer simple: one text field, one context selector, and a conditional timestamp input shown only when `time` is selected
- chord notes from Song Detail should default to a simple chord selector tied to existing song chords rather than trying to infer a live playback position
- render open notes first and resolved notes in a collapsible secondary section
- each note row should expose edit, resolve/unresolve, and delete actions
- note rows should display context clearly: timestamp notes as time labels and chord notes as chord number plus, where easy, chord label
- success/error feedback should reuse the page's existing inline action-success/action-error pattern

Song Detail time-note rule for this slice:
- a user creates a Song Detail time note by typing note text, choosing `time`, and entering a manual timestamp
- accepted entry can be normalized from `mm:ss` or raw seconds into `timestamp_sec`
- if that parsing path feels too large during implementation, the fallback allowed by this design is a plain numeric seconds input only; do not invent a hidden heuristic or rely on player state

### 4. Player rehearsal workflow

`frontend/src/redesign/pages/PlayerPage.tsx` should focus on fast note capture during playback, not on broad collaboration UX.

Recommended behavior:
- keep the existing comments side panel but upgrade it into a real notes panel
- provide a compact create-note form with two quick actions: `Note at current time` and `Note on current chord`
- default timestamp note creation to the live transport time from `useAudioPlayer(...)`
- default chord note creation to `currentIndex` when a chord is active
- allow edit, resolve/unresolve, and delete from the same panel so users do not need to leave playback to clean up notes
- keep resolved notes visible but visually secondary, matching the honest state used in song detail

The player should stay rehearsal-centric:
- fast capture during listening
- direct links to time and chord context
- no mentions, unread counters, or presence indicators

### 5. Time and chord context

This slice should prioritize note context that is actionable during rehearsal.

Recommended rules:
- a time note stores `timestamp_sec` and renders against the shared transport clock in player and as a readable time label in song detail
- a chord note stores `chord_index` and renders as chord number plus optional chord label when available from `song.chords`
- player note markers continue to derive from the current song note collection so transport UI reflects backend truth after refresh
- if both time and chord context are useful later, do not add a hybrid note type now; keep one primary link per note to avoid scope creep

### 6. Honest resolved/open state

Resolved notes must stop behaving like a cosmetic frontend-only section.

Recommended rule set:
- open notes are the default list and count surfaced in both song detail and player
- resolved notes move into a clearly separate, collapsible section
- resolve/unresolve is a first-class mutation, not a local UI filter
- delete permanently removes a note; resolve preserves history but marks it closed

This gives the product an honest distinction:
- open notes still need rehearsal attention
- resolved notes remain visible as history without pretending they are active

### 7. API and type alignment

The slice should align the frontend contracts with the backend rather than adding page-local adapters that hide truth gaps.

Recommended changes:
- extend `frontend/src/lib/types.ts` and `frontend/src/redesign/lib/types.ts` so note types include real resolved and author/timestamp fields
- extend `frontend/src/lib/api.ts` with a dedicated resolve-note helper and, if useful, broaden `updateSongNote(...)` return typing so the frontend can treat responses as real note payloads
- update `frontend/src/App.tsx` note mapping to stop synthesizing `resolved: false`, fake timestamps, or fallback note authors for records touched by this slice

Author-truth rule:
- once Slice 4 expands the backend note contract, note author metadata rendered in song detail and player must come from backend note payloads
- `frontend/src/App.tsx` must not silently substitute the current user as `authorName` or `authorAvatar` for fetched notes in this slice
- if backend note author fields are missing, that is a contract bug to fix in Slice 4, not something the frontend should mask

## Testing Strategy

### Backend tests

- extend `backend/tests/test_api.py`
- cover create/edit/delete/resolve/unresolve flows plus truthful note payloads from `GET /api/songs/{song_id}`
- cover validation for missing `timestamp_sec` and missing `chord_index`

### Frontend API and route integration tests

- extend `frontend/src/__tests__/App.integration.test.tsx`
- verify song detail and player can mutate notes through route-owned callbacks and refresh to the same note truth
- verify resolved notes stay resolved after refresh rather than being remapped to open

### Frontend page/component tests

- add `frontend/src/redesign/pages/__tests__/SongDetailPage.notes.test.tsx`
- extend `frontend/src/redesign/pages/__tests__/PlayerPage.test.tsx`
- cover Song Detail manual timestamp-note creation, Song Detail chord-note creation, create/edit/delete/resolve actions, time/chord context labels, open/resolved grouping, and current-time note capture in the player

## Manual Verification Expectations

Use a real processed song such as `test songs/Clara Luciani - La grenade.mp3`.

Manual checks:
- open song detail and create a time-linked note using the manual timestamp field; confirm it appears as open with the expected time label
- open song detail and create a chord-linked note; confirm it appears as open with the expected chord context
- open player for the same song, create a time-linked note from the live transport, and confirm it appears without leaving playback
- edit note text from one surface and confirm the other surface shows the updated text after refresh
- resolve a note and confirm it leaves the open list and appears under resolved on both song detail and player
- delete a note and confirm it disappears from both surfaces after refresh
- verify the player still shows time markers and chord-linked indicators based on the updated backend-backed note set

## Done Criteria

This slice is done when:
- notes can be created, edited, deleted, and resolved with real backend persistence
- notes can be authored from both `SongDetailPage` and `PlayerPage`, with Song Detail explicitly supporting manual timestamp entry for time notes
- the player supports at least one quick time-linked flow and one quick chord-linked flow
- song detail and player both render the same truthful open/resolved note state
- `App.tsx` no longer fabricates resolved state, author identity, or timestamps for fetched notes
- no member/activity/unread/presence work has leaked into the slice

## Risks and Deferred Work

- The current backend note schema may not yet store all author metadata needed for richer multi-user history; for this slice, use the honest single-user/default-user truth available now and defer multi-user attribution depth to the collaboration slice.
- Player note UX can sprawl quickly; keep capture/edit controls compact rather than turning the side panel into a full discussion client.
- If chord labels are not already exposed everywhere needed, use chord index first and only add label decoration where it is cheap and truthful.
- Unread counters, activity feeds, member lists, and presence remain explicit Slice 5 work.

## Decision Summary

- make the backend note contract truthful before adding more UI
- ship note CRUD plus resolve/unresolve from both song detail and player
- prioritize current-time and current-chord rehearsal actions
- keep route-owned refresh in `frontend/src/App.tsx` so both surfaces share one note source of truth
- defer collaboration features to the dedicated collaboration slice
