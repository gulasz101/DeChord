# Processing Journey Design

**Date:** 2026-03-10

**User promise:** After a song upload starts, DeChord immediately moves the user into an honest in-app processing journey that shows queued, active, success, or failure state in real time, and on success it automatically opens the new song's detail page.

## Scope

This slice covers the route-level upload-to-completion journey only.

In scope:
- upload initiation from the song library route
- visible queued and processing feedback after upload
- success transition into the real song detail page
- failure handling that explains what happened and offers a clear exit back to the library
- route-aware polling using existing upload job APIs

Out of scope:
- persistent jobs infrastructure across app restarts
- a global jobs center
- a modal-heavy cross-app job manager
- retry, cancel, or history for background jobs beyond the active route session

## Current State

What already exists:
- `uploadAudio(...)` posts to `POST /api/analyze` and returns `{ job_id, song_id }`
- `getJobStatus(...)` reads `GET /api/status/{job_id}`
- `getResult(...)` reads `GET /api/result/{job_id}` after completion
- `frontend/src/App.tsx` already refreshes bands/projects/songs after upload
- `frontend/src/redesign/pages/SongLibraryPage.tsx` already owns the upload entry point
- `backend/app/main.py` already records job stages such as `queued`, `splitting_stems`, `generating_tabs`, and `complete`

What is missing:
- the user is not shown a durable in-app journey after upload begins
- route state jumps back to the library and depends on refresh rather than visible progress
- there is no explicit error view for failed or reset-lost jobs
- success does not take the user directly to the new song detail page

## Approaches Considered

### Approach 1: Keep the current library refresh flow

Behavior:
- upload from the library
- stay on the library page
- silently refresh until the song eventually appears ready

Pros:
- smallest implementation
- no new route required

Cons:
- weak product honesty
- easy to miss failures or long-running work
- does not satisfy the approved rich in-app journey requirement
- does not naturally auto-open the new song detail page

### Approach 2: Add a route-level processing journey page

Behavior:
- upload from the library
- transition to a dedicated route-level processing state tied to the new `job_id` and `song_id`
- poll existing job APIs and show stage-aware progress
- on success, refresh app data and auto-open the new song detail page
- on failure, keep the user on the journey route with clear recovery actions

Pros:
- matches the approved product direction
- keeps the journey local to the upload flow instead of inventing global infrastructure
- works with current `uploadAudio`, `getJobStatus`, and `getResult` APIs
- gives a strong place to explain reset-sensitive failure states honestly

Cons:
- requires a new route state and polling lifecycle management
- needs careful cleanup when navigating away mid-poll

### Approach 3: Build a global jobs center

Behavior:
- upload from the library
- create a cross-app jobs tray, panel, or dedicated jobs page
- let users manage background work from anywhere

Pros:
- strongest long-term multi-job model

Cons:
- over-scoped for this slice
- introduces persistent-product questions the current backend cannot answer honestly
- conflicts with the approved route-level direction

## Recommendation

Use **Approach 2: a route-level processing journey page**.

It satisfies the user promise without creating fake durability. The current backend already exposes enough signal for a truthful route-local journey, and the app can keep richer infrastructure deferred until a later hardening slice.

## Proposed UX

### Entry

- The user starts on `SongLibraryPage`
- After `uploadAudio(...)` resolves, the app immediately transitions away from the library into a processing journey route state
- The route carries the current `band`, `project`, `songId`, `jobId`, uploaded file name, process mode, and tab quality so the page can render meaningful context before polling completes

### Processing view

The route-level page should show:
- the song title or uploaded filename
- the active project and band context
- a clear overall status label: queued, processing, complete, or failed
- stage-aware copy from backend status fields such as `message`, `stage`, `progress_pct`, and `stage_history`
- a progress timeline or stage list for major milestones like upload queued, chord analysis, stem split, MIDI, tab generation, and save
- a note that this is the live processing journey for the current upload, not a persistent job inbox

### Success path

- When `getJobStatus(jobId)` returns `complete`, the app fetches `getResult(jobId)`
- The app then refreshes the project hierarchy so the new song appears in canonical library state
- The app loads the full song detail using `getSong(songId)` and `listSongStems(songId)`
- The route automatically changes to `song-detail`
- The resulting song detail page becomes the post-processing landing view

### Error path

The processing journey route stays visible and explains failure instead of ejecting the user silently.

Expected failure handling:
- `status === error`: show backend error text if available and offer `Back to Library`
- `getJobStatus(...)` 404 after reset/restart: show an honest message that the in-memory processing job is no longer available and that the slice does not yet support persistent job recovery
- `getResult(...)` failure after a reported complete status: show a recoverable error state and offer `Open Library` or `Retry Refresh`

This keeps scope tight while being honest about current infrastructure limits.

## Route Transition Behavior

Recommended route model in `frontend/src/App.tsx`:
- extend the route union with a `processing-journey` page
- create the route immediately after a successful upload response
- start polling only while the route is active
- stop polling when the user navigates away or when the job reaches a terminal state

Back/exit behavior:
- explicit `Back to Library` action returns to the current project's song library
- if the user leaves the route before completion, polling stops; this slice does not continue tracking the job elsewhere
- if the browser reloads during processing, the job view is lost because route state and backend jobs are both session-local; this must be documented as a known non-goal, not hidden

## Architecture And Data Flow

### Frontend flow

1. `SongLibraryPage` submits file, mode, and tab quality through `onUploadSong`
2. `App.tsx` calls `uploadAudio(file, processMode, tabGenerationQuality, projectId)`
3. `uploadAudio(...)` returns `{ job_id, song_id }`
4. `App.tsx` sets route to `processing-journey`
5. A route-aware polling loop calls `getJobStatus(jobId)` on an interval while that route stays active
6. Intermediate responses update route-local UI state
7. On `complete`, the app calls `getResult(jobId)` and refreshes the app hierarchy
8. The app loads song detail and stems for `song_id`
9. The app navigates to `song-detail`

### API usage

Use existing APIs as-is for this slice:
- `uploadAudio(...)`
- `getJobStatus(...)`
- `getResult(...)`
- `getSong(...)`
- `listSongStems(...)`

`pollUntilComplete(...)` is a useful reference but not the final recommendation for this slice because the route must:
- update UI on each poll
- stop polling when the user leaves the route
- handle status and result failures differently
- trigger route transitions and hierarchy refresh on completion

So the slice should use either:
- a small route-aware polling helper in `App.tsx`, or
- a thin reusable helper wrapping `getJobStatus(...)` with cancellation support

It should not introduce a generic jobs framework.

### Backend expectations

This slice should reuse the current backend contract rather than add new job endpoints.

The frontend depends on these existing truths from `backend/app/main.py`:
- `POST /api/analyze` creates the song record before background processing finishes
- `GET /api/status/{job_id}` exposes status, stage, progress, message, and sub-status fields
- `GET /api/result/{job_id}` returns the completed analysis with `song_id`

Backend work is only needed if tests expose a missing edge case in those existing responses.

## Testing Strategy

### Frontend unit and component coverage

- add route-level page tests for the processing journey presentation
- verify queued, processing, success, and error states render honestly
- verify reset-lost job messaging for `getJobStatus(...)` failure

### Frontend integration coverage

- extend `frontend/src/__tests__/App.integration.test.tsx`
- verify upload navigates into the processing journey route instead of silently refreshing the library
- verify status polling updates the journey state
- verify completion auto-opens the new song detail page
- verify error keeps the user on the journey route with a clear exit path

### Backend coverage

- keep backend scope minimal
- add or adjust targeted API tests only if the frontend needs a contract guarantee that is not already covered

### Manual verification

Use the real fixture `test songs/Clara Luciani - La grenade.mp3`.

Manual check:
- start from a real project song library
- upload the fixture with `analysis_and_stems`
- confirm the app enters the processing journey route immediately
- watch stage copy update while the job runs
- confirm success auto-opens the new song detail page
- confirm a restart/reset during processing leads to an honest lost-job error instead of a fake completed state

## Risks And Non-Goals

- Jobs are still stored in memory, so reset/restart will orphan active processing state; this slice must message that honestly rather than mask it
- Polling cadence should stay simple and local; do not add background polling after the user leaves the route
- Do not expand this slice into song-detail asset generation, collaboration notifications, or release-grade job durability

## Decision Summary

- Build a rich in-app processing journey
- Keep it route-level
- Reuse `uploadAudio`, `getJobStatus`, `getResult`, `getSong`, and `listSongStems`
- Auto-open the new song detail page on success
- Handle reset-lost jobs as honest errors
- Defer persistent jobs infrastructure to a later slice
