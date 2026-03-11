# Real Player Design

**Date:** 2026-03-10

## XML Tracking

<phase id="real-player-design" status="completed">
  <task>[x] Task 1: Define the transport-truth player promise and tight slice scope.</task>
  <task>[x] Task 2: Compare real-player approaches and recommend the transport-first slice.</task>
  <task>[x] Task 3: Specify architecture for the shared playback clock, real assets, route ownership, teardown, and prefs.</task>
  <task>[x] Task 4: Capture testing strategy, manual verification expectations, done criteria, and deferred risks.</task>
</phase>

## Product Promise

The player must tell the truth about what is playing and where playback is. When a user opens `frontend/src/redesign/pages/PlayerPage.tsx`, DeChord should play the real song audio or the selected real stems, use one shared playback clock for play/pause/seek/loop, drive chord and tab sync from that real clock, and load the real generated tab file instead of a mock AlphaTex asset.

For this slice, success is **transport truth first**:
- real audio source
- real play/pause/seek
- real current-time sync into chords and tabs
- one shared real playback clock
- persisted playback prefs if that drops in naturally without expanding scope

## Scope

This slice is intentionally narrow and centered on replacing the simulated timer transport now living inside `frontend/src/redesign/pages/PlayerPage.tsx`.

In scope:
- replace the local `setInterval(...)` transport with the real audio clock from `frontend/src/hooks/useAudioPlayer.ts`
- load the player from real backend asset URLs via `frontend/src/lib/api.ts` and `frontend/src/lib/playbackSources.ts`
- feed the same `currentTime` into `ChordTimeline`, `Fretboard`, `TransportBar`, and `TabViewerPanel`
- load the real tab file from `GET /api/songs/{song_id}/tabs/file`
- keep player route ownership in `frontend/src/App.tsx`
- persist playback preferences only for speed, volume, and loop points if the existing `savePlaybackPrefs(...)` path fits cleanly

Out of scope:
- broad mixer redesign or per-stem gain balancing
- comments create/edit/resolve work
- collaborative playback or presence
- background waveform work, beat maps, or advanced tab-following UX
- broad route rewrites outside the player entry/refresh path

## Current State

What already exists:
- `frontend/src/hooks/useAudioPlayer.ts` already knows how to play one audio source or a selected set of stem sources with a single hook-managed clock
- `frontend/src/lib/playbackSources.ts` already resolves full-mix versus stem URLs against real backend routes
- `backend/app/main.py` already serves full audio, stem audio, tab file, and playback prefs endpoints
- `frontend/src/components/TabViewerPanel.tsx` already accepts a real `tabSourceUrl`

What is still dishonest or incomplete:
- `PlayerPage` uses its own simulated `setInterval(...)` clock instead of the real audio clock
- `PlayerPage` hardcodes `"/mock-bass.alphatex"` instead of a real song tab asset
- route-level player entry in `frontend/src/App.tsx` passes a song snapshot but does not explicitly hydrate player-specific truth before entering playback
- current player state and current tab/chord sync can drift because multiple clocks exist conceptually even though only one should exist
- playback prefs exist in the backend contract but are not part of the current player experience

## Approaches Considered

### Approach 1: Swap URLs only and keep the simulated timer

Behavior:
- replace the mock tab URL with the real tab file URL
- point playback controls at real audio URLs later
- keep `PlayerPage`'s local timer as the source of truth for current time

Pros:
- fastest visible change
- minimal code churn

Cons:
- still dishonest because play/pause/seek would not come from real audio playback
- chord sync and tab sync could drift from what the user actually hears
- leaves the core player trust problem unresolved

### Approach 2: Transport-first real-player slice with one shared playback clock

Behavior:
- make `useAudioPlayer(...)` the only transport clock
- resolve real full-mix and stem URLs through `resolvePlaybackSources(...)`
- load the tab viewer from `getTabFileUrl(songId)`
- compute chord/fretboard/tab sync from the hook's `currentTime`
- keep route ownership and hydration in `App.tsx`

Pros:
- matches the approved success criteria exactly
- removes the current player lie without requiring a large redesign
- reuses existing backend endpoints and frontend helpers
- creates the right foundation for later notes/rehearsal work

Cons:
- requires a careful refactor of `PlayerPage` because the current page still owns simulated transport state
- needs coordinated tests across hook, page, and app route wiring

### Approach 3: Bigger DAW-style player and mixer slice

Behavior:
- add per-stem gain sliders, solo/mute states, richer transport, waveform views, and deeper tab follow behavior at the same time

Pros:
- more impressive end state

Cons:
- too large for the approved slice
- would bury transport truth inside mixer feature creep
- increases risk of partial, unstable player behavior

## Recommendation

Use **Approach 2: the transport-first real-player slice**.

This is the smallest slice that makes the player honest. It replaces the fake timer with the real playback clock, uses real asset URLs, keeps route ownership in `App.tsx`, and limits stem work to the minimum needed for real transport truth.

## Architecture And Data Flow

### 1. Route Ownership

`frontend/src/App.tsx` remains the owner of route truth.

Recommended flow:
1. when the user opens the player from song detail, `App.tsx` hydrates the freshest song detail for that song using the existing `loadSongDetails(...)` path before or during route entry
2. `App.tsx` passes the hydrated `song` into the `player` route, including chords, stems, tab metadata, and playback prefs
3. `PlayerPage` manages only player-local UI state plus calls back to route-owned refresh helpers and, only if prefs are included in-slice, route-owned prefs persistence helpers

Why this matters:
- the player should not invent its own route data contract
- song detail and player should agree on the same backend truth
- later slices can refresh the active player route the same way they refresh song detail today

### 2. Shared Real Playback Clock

`frontend/src/hooks/useAudioPlayer.ts` becomes the single source of truth for transport.

Recommended behavior:
- derive the active playback sources from `frontend/src/lib/playbackSources.ts`
- initialize `useAudioPlayer(audioSrc, stemSources)` in `PlayerPage`
- use the hook's public transport contract consistently as `playing`, `currentTime`, `duration`, `togglePlay`, `seek`, `seekRelative`, `setPlaybackRate`, `setVolume`, and `setLoop` for all player interactions
- remove the local `setInterval(...)` clock and the page-local `playing/currentTime` transport simulation

Truth rule:
- if the hook says `currentTime=42.3`, that same value drives transport UI, chord highlighting, fretboard next-chord logic, and tab cursor sync
- there must be no second timer in `PlayerPage`

### 3. Real Audio Source Resolution

`frontend/src/lib/playbackSources.ts` should stay the place where audio source intent becomes backend URLs.

Recommended direction:
- default playback is the real song mix from `getAudioUrl(songId)`
- if the user enables stem playback mode, build stem URLs from `getStemAudioUrl(songId, stemKey)`
- keep stem behavior minimal: enough to choose full mix versus currently enabled stems and keep them sample-synced through one hook clock
- do not add per-stem volume balancing in this slice

### 4. Real Tab Source Loading

`frontend/src/components/TabViewerPanel.tsx` already supports a real `tabSourceUrl`, so the player should pass the backend tab file URL instead of `"/mock-bass.alphatex"`.

Recommended rule:
- if `song.tab` exists and its status is usable, pass `getTabFileUrl(Number(song.id))`
- if the song has no tab yet, keep the honest empty state already rendered by `TabViewerPanel`

This keeps the slice honest without inventing client-side tab caching or alternate tab storage.

### 5. Chord Sync And UI Sync

The audio clock should drive all musical sync.

Recommended behavior:
- compute `currentIndex` from `song.chords` against the hook's `currentTime`
- clicking a chord seeks the real audio clock to that chord start and also updates loop selection state
- `TransportBar` seek and skip buttons call the hook directly
- `TabViewerPanel` receives `currentTime` and `isPlaying` from the same hook values so its cursor follows the heard transport

### 6. Playback Prefs

Persist prefs only if it fits naturally into the slice.

Recommended scope for persistence:
- `speed_percent`
- `volume`
- `loop_start_index`
- `loop_end_index`

Recommended data flow:
- if prefs persistence is included, extend the player-facing song model to carry playback prefs from `GET /api/songs/{song_id}`
- if prefs persistence is included, initialize `PlayerPage` state from those persisted values on first render for a song
- if prefs persistence is included, call `savePlaybackPrefs(songId, prefs)` only on discrete settings changes, not on every playback tick
- if persisting prefs complicates transport truth materially, keep the real transport work first and defer prefs persistence from this slice rather than forcing it in

### 7. Teardown And Source Changes

The player must clean up cleanly whenever the route leaves, the song changes, or the active audio sources change.

Required teardown behavior:
- `useAudioPlayer(...)` pauses and clears audio elements plus cancels `requestAnimationFrame`
- `TabViewerPanel` destroys its AlphaTab instance when the tab URL changes or the page unmounts
- `PlayerPage` must not leave a lingering timer because the simulated timer is removed entirely

Source-change rule:
- when the enabled stems or selected versions change, the player should rebuild the playback source list through `resolvePlaybackSources(...)` and continue using the hook-managed transport truth
- if preserving exact current time across source swaps is simple and reliable, do it; if not, the slice should at minimum reset honestly and visibly rather than pretending continuity

## Testing Strategy

### Frontend unit tests

- extend `frontend/src/hooks/__tests__/useAudioPlayerStems.test.ts` or add a transport-focused hook test file to cover play/pause/seek/loop/end behavior from the shared clock
- extend `frontend/src/lib/__tests__/playbackSources.mode.test.ts` to lock full-mix versus stem URL resolution used by the player

### Frontend component tests

- add `frontend/src/redesign/pages/__tests__/PlayerPage.test.tsx`
- cover real transport wiring: play/pause, chord seek, loop setup/clear, real tab URL usage, and sync of current time into child components
- extend `frontend/src/components/__tests__/TabViewerPanel.test.tsx` only if needed to confirm real backend tab URLs still flow through the existing component contract

### Route integration tests

- extend `frontend/src/__tests__/App.integration.test.tsx`
- verify opening the player uses hydrated song detail, passes real playback/tab sources, and does not fall back to `/mock-bass.alphatex`
- verify prefs persistence if that work lands in the slice

### Backend verification

- keep focused backend regression checks for the existing endpoints that the slice depends on: full audio, stem audio, tab file, and playback prefs
- only add backend code/tests if a real contract gap is discovered during implementation

## Manual Verification Expectations

Use a processed real song such as `test songs/Clara Luciani - La grenade.mp3`.

Manual checks:
- open the player from a real song detail page and confirm the player uses the real song title/chords/tab state for that song
- press play and confirm audio is real, not simulated UI-only playback
- pause, seek via the transport bar, and click a chord block; confirm heard playback position, chord highlight, and tab cursor stay aligned
- if stem mode is enabled, toggle into real stem playback and confirm the player still uses one coherent transport clock
- reload or reopen the player and confirm speed/volume/loop prefs restore only if persistence was included
- leave the player route and return; confirm playback does not continue from a ghost timer or stale AlphaTab instance

## Done Criteria

This slice is done when:
- `PlayerPage` no longer owns a simulated timer transport
- one shared real playback clock drives transport UI, chord highlighting, and tab sync
- the player uses real backend asset URLs for full mix, stems when enabled, and tabs
- play/pause/seek are real and audible
- route ownership stays in `frontend/src/App.tsx`
- prefs persistence is either working for speed/volume/loop points or explicitly deferred without weakening transport truth
- no broad mixer or collaboration scope has leaked into the slice

## Risks And Deferred Work

- Browser audio elements may make seamless source switching harder than honest reset behavior; do not over-engineer around this in the slice.
- `PlayerPage`, `TransportBar`, and `ChordTimeline` currently look partially out of sync on props and responsibilities; the implementation must converge them around the real hook contract instead of papering over mismatches.
- Persisting playback prefs is useful but secondary; if it threatens the transport-truth milestone, defer polish before drifting scope.
- Stem mixing sophistication, comment authoring, and rehearsal tooling remain later-slice work.

## Decision Summary

- replace the fake timer in `frontend/src/redesign/pages/PlayerPage.tsx` with `frontend/src/hooks/useAudioPlayer.ts`
- use real backend audio and tab file URLs instead of mocks
- drive chords, fretboard, transport, and tabs from one shared real clock
- keep route ownership in `frontend/src/App.tsx`
- keep stem work minimal and persistence optional behind the transport-truth milestone
