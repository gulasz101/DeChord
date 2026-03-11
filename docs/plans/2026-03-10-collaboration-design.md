# Collaboration Design

**Date:** 2026-03-10

## XML Tracking

<phase id="collaboration-design" status="completed">
  <task>[x] Task 1: Define the truthful collaboration-basics product promise and scope guardrails.</task>
  <task>[x] Task 2: Compare collaboration-slice approaches and recommend the smallest honest vertical slice.</task>
  <task>[x] Task 3: Specify architecture and data flow for members, project activity, unread counts, acting-user attribution, and placeholder presence handling.</task>
  <task>[x] Task 4: Capture testing strategy, manual verification expectations, done criteria, and deferred risks.</task>
</phase>

## Product Promise

DeChord should make `frontend/src/redesign/pages/ProjectHomePage.tsx` feel collaborative because the data is real, not because the UI looks collaborative. In this slice, a band member should be able to open a project and see the real band member list, a real project activity feed, and real unread counts backed by persisted read state. The page must stay honest about presence: if live presence is not implemented, the UI should say so and avoid implying that green dots are real.

For this slice, success means:
- real members come from `band_memberships` and `users`
- real project activity comes from persisted project events, not frontend synthesis
- real unread counts come from persisted per-user read markers
- activity attribution uses the resolved acting user, not the hardcoded default user
- placeholder presence comes from the backend member payload and stays explicitly non-live rather than falsely live

## Scope

This slice is intentionally collaboration-focused but still narrow.

In scope:
- make band member lists in project home truthful
- add a persisted project activity feed for collaboration-relevant actions
- add per-user unread counts for project activity
- make acting-user attribution honest for collaboration events
- add an explicit backend-owned placeholder presence strategy in the member contract and UI
- refresh project-home collaboration state after collaboration-relevant mutations

Out of scope:
- invites, join links, permission editing, or role-management UI
- live cursors, collaborative editing, typing indicators, or chat
- notifications, email, push, or mobile presence
- per-note unread state, mentions, assignments, or threaded conversations
- a full audit log for every backend mutation in the product

## Current State

What already exists:
- `frontend/src/redesign/pages/ProjectHomePage.tsx` already has member, unread, and recent-activity sections in the UI
- `frontend/src/redesign/lib/types.ts` already models `Band`, `Project`, `BandMember`, and `ActivityItem`
- `frontend/src/App.tsx` already loads bands, projects, and songs into a route-owned hierarchy
- `backend/app/db_schema.sql` already has `users`, `bands`, `band_memberships`, `projects`, `songs`, and `notes`

What is still incomplete or dishonest:
- `frontend/src/App.tsx` currently fabricates collaboration state with `recentActivity: []`, `unreadCount: 0`, and a one-member band built from the current browser user only
- `BandMember.isOnline` is currently synthesized as `true` for the current user even though there is no live presence backend contract
- `backend/app/main.py` exposes no collaboration endpoints for band members, project activity, or read markers
- collaboration-relevant mutations still use `get_default_user()` for authorship, so cross-user activity would be misattributed
- there is no persisted unread/read model anywhere in the backend schema

## Approaches Considered

### Approach 1: Compute collaboration locally from existing songs and notes

Behavior:
- derive member lists from whatever user is currently loaded in the browser
- build recent activity by scraping existing songs and notes in the frontend
- keep unread counts as local UI counters only

Pros:
- smallest amount of backend work
- looks fast to ship

Cons:
- still dishonest because member lists, unread counts, and activity attribution are not persisted
- cannot distinguish one user's read state from another's
- collapses as soon as there is more than one identity or browser
- repeats the exact placeholder pattern this program is trying to remove

### Approach 2: Truthful collaboration basics with persisted activity and read markers

Behavior:
- use `band_memberships` plus `users` for real member lists
- add persisted project activity events for a tight set of collaboration-relevant actions
- add per-user read markers so unread counts are real
- pass the resolved acting user through collaboration-related API requests
- return placeholder presence from the backend member payload as explicitly not live yet

Pros:
- matches the approved direction exactly
- makes the existing project-home UI truthful without growing into a social system
- gives later collaboration work a durable base for notifications or richer feeds
- keeps the slice vertical: schema, API, route loading, and project-home rendering all become real together

Cons:
- requires touching both backend identity flow and frontend API plumbing
- needs discipline about which events enter the activity feed so the slice stays small

### Approach 3: Full collaboration system now

Behavior:
- add invites, membership management, live presence, richer roles, mentions, and notifications in one slice

Pros:
- ambitious end state

Cons:
- directly violates the approved guidance to keep scope honest
- creates a large amount of partially truthful UI and policy work
- would delay the smaller collaboration fundamentals already visible in project home

## Recommendation

Use **Approach 2: truthful collaboration basics with persisted activity and read markers**.

This is the smallest slice that makes `ProjectHomePage` real. It fixes the current fake member list, fake unread counts, and empty activity feed by introducing backend-backed collaboration data, while explicitly deferring live presence and all social-system expansion.

## Architecture and Data Flow

### 1. Acting-user attribution becomes a collaboration prerequisite

Collaboration cannot be truthful while `backend/app/main.py` attributes note, stem, and project activity mutations to `get_default_user()`.

Recommended direction:
- add a lightweight acting-user contract for frontend API calls, for example an `X-DeChord-User-Id` header sent from `frontend/src/lib/api.ts`
- set that header from the already-resolved identity in `frontend/src/App.tsx`
- validate the acting user on collaboration endpoints and on collaboration-relevant mutations that create activity events
- keep this identity flow narrow to the current local product model; do not introduce login sessions or tokens in this slice

Truth rule:
- if a collaboration event appears in the activity feed, its author must come from the resolved acting user, not a backend default-user shortcut

### 2. Members come from `band_memberships`, not from frontend placeholders

The real member list already has enough backend source data to exist today.

Recommended backend contract:
- add a band-members endpoint such as `GET /api/bands/{band_id}/members`
- query `band_memberships` joined to `users`
- return stable identity fields needed by the existing redesign surface: member id, display name, avatar initials, role, and placeholder presence state
- stop requiring a fake instrument string for collaboration surfaces; if `frontend/src/redesign/lib/types.ts` currently requires `instrument`, make it optional or replace its display with a truthful role/subtitle

Recommended frontend behavior:
- `frontend/src/App.tsx` should load real members per band and store them in the route-owned hierarchy
- `frontend/src/redesign/pages/ProjectHomePage.tsx` should render the real members list from that backend payload and a short presence disclaimer

### 3. Project activity needs an explicit durable event table

The feed in `ProjectHomePage` should be backed by an event log rather than by scraping song state after the fact.

Recommended schema addition in `backend/app/db_schema.sql`:
- `project_activity_events`
  - `id`
  - `project_id`
  - `actor_user_id`
  - `actor_name`
  - `actor_avatar`
  - `event_type`
  - `song_id` nullable
  - `song_title` nullable
  - `message`
  - `created_at`

Keep the first event set intentionally small and collaboration-relevant:
- `song_added` when upload creates a project song
- `status_change` when processing settles into a meaningful user-visible result such as ready or failed
- `comment` when a note is created
- `comment_resolved` when a note is resolved or reopened
- `stem_upload` for uploaded or regenerated stems and regenerated tabs when those actions materially affect project collaboration

Design rule:
- prefer a small truthful event vocabulary over a broad but half-maintained audit log

### 4. Unread counts should be event-based and per user

Unread counts should describe unseen project activity, not unresolved notes and not browser-local badges.

Recommended schema addition:
- `project_activity_reads`
  - `project_id`
  - `user_id`
  - `last_read_event_id`
  - `updated_at`

Recommended behavior:
1. a project activity query returns newest events plus the current viewer's unread count
2. `GET /api/bands/{band_id}/projects` includes `unread_count` for each project so the sidebar can render real badges
3. opening a project home surface triggers `POST /api/projects/{project_id}/activity/read`
4. the unread count falls to zero for that user after the read marker is updated

Why use `last_read_event_id` instead of timestamps:
- it avoids ordering ambiguity when multiple events share a timestamp
- it makes unread counting a simple `id > last_read_event_id` query in LibSQL

Recommended unread rule:
- exclude events authored by the current viewer from unread counts so single-user local activity does not create fake unread work

### 5. Presence handling stays explicitly placeholder

Live presence would overscope this slice, so the product needs a truthful placeholder strategy.

Recommended approach:
- do not add heartbeats, websockets, polling presence, or inferred online status
- return member rows with a presence field that is explicitly placeholder, such as `presence_state: "not_live"`
- render a short UI label in `ProjectHomePage`, for example `Presence updates are not live yet.`
- keep online dots muted or absent until a real presence system exists

Truth rule:
- never show a green online indicator unless it is backed by a real presence source
- do not infer presence from `resolveIdentity`, recent API calls, or the current open browser tab

### 6. Frontend loading model should stay route-owned in `App.tsx`

`frontend/src/App.tsx` should continue to own project-home collaboration state rather than letting `ProjectHomePage` fetch independently.

Recommended flow:
1. after identity bootstrap, set the API acting-user context once
2. when loading bands, fetch real band members and project unread counts
3. when entering the `project` route, fetch that project's activity feed
4. immediately mark the selected project as read and then refresh the hierarchy so sidebar unread badges stay accurate
5. after collaboration-relevant mutations already wired through `App.tsx` such as upload completion, note create/resolve, stem upload, stem regeneration, and tab regeneration, refresh collaboration state for the affected project

Why keep it here:
- unread badges, member lists, and recent activity all belong to shared route state
- both project selection and later slice work already flow through `App.tsx`
- it prevents project-home-specific fetch logic from drifting away from the rest of the app shell

## Real vs Placeholder vs Deferred

### Real in this slice

- member lists sourced from `band_memberships` and `users`
- project activity sourced from persisted `project_activity_events`
- unread counts sourced from persisted `project_activity_reads`
- activity author names and avatars sourced from the acting user who performed the mutation

### Intentional placeholder in this slice

- placeholder presence is carried in the backend member payload as `presence_state: "not_live"`
- presence rendering may use muted or absent status dots plus explanatory copy
- no claim is made that member availability is live or current, and the frontend should not invent any separate presence mapping

### Explicitly deferred

- invites and membership-management flows
- permissions editing, role editing, or owner transfer UX
- direct messages, mentions, reactions, or assignments
- live presence, push notifications, or background sync
- richer collaboration analytics and per-thread unread state

## Testing Strategy

### Backend tests

- extend `backend/tests/test_api.py`
- cover real member listing from `band_memberships`
- cover activity feed reads and unread counts for two different users
- cover read-marker writes and idempotent unread clearing
- cover collaboration event creation for at least note create/resolve and one project-song action

### Frontend API and route tests

- extend `frontend/src/lib/__tests__/api.bands-projects.test.ts` or add a dedicated collaboration API test file
- verify the acting-user header is attached to collaboration requests
- verify `App.tsx` hydrates real members, unread counts, and project activity instead of synthesized defaults
- verify opening project home marks the project as read and updates the unread badge

### Frontend page tests

- add `frontend/src/redesign/pages/__tests__/ProjectHomePage.collaboration.test.tsx`
- cover member list rendering, unread badge rendering, project activity rows, and presence placeholder copy
- keep the page test focused on truthful rendering, not on independent fetching

## Manual Verification Expectations

Use two resolved identities in separate browsers or profiles if possible.

Manual checks:
- create or load a band with at least one additional member and confirm project home shows the real member list rather than only the current user
- from user A, upload a song or add a note in a project and confirm project home for user B shows a real unread badge
- open that project as user B and confirm the activity feed shows the real event author, song context, and unread badge clears after read-marking
- resolve a note or regenerate stems and confirm the activity feed records the new event with the correct author and message
- confirm the members area says presence is not live yet and does not show fake green dots

## Done Criteria

This slice is done when:
- project-home member lists come from backend memberships rather than frontend placeholders
- project-home recent activity comes from persisted backend events
- unread counts are per-user, persisted, and clear after project read-marking
- activity author attribution uses the resolved acting user
- the backend member contract and UI are both explicit that presence is placeholder and not live
- no invites, permissions, role-management UI, or live presence system have leaked into the slice

## Risks and Deferred Work

- The biggest honesty risk is user attribution: if acting-user context is not propagated through the collaboration-related routes, the feed will still look collaborative while crediting the wrong person.
- The current redesign types assume member instrumentation that the backend does not store. This slice should prefer truthful role or generic member subtitles over invented instrument data.
- Single-user local development can hide unread bugs. The implementation must use multi-user backend tests even if manual verification is mostly local.
- Event logging can sprawl quickly. Keep the first event vocabulary tight and skip low-value noise such as every edit or every background backend step.

## Decision Summary

- make project-home collaboration truthful before making it richer
- use persisted activity events and read markers as the core slice
- require acting-user attribution for collaboration events
- treat presence as explicitly placeholder, not silently fake
- defer invites, permissions, role-management, and live presence to later work
