# Opus 5-3 Frontend Redesign Design

## Task Checklist

- [x] Confirm redesign source (`designs.opus46/5-3`) and product priority.
- [x] Confirm scope exclusions (full auth/registration skipped).
- [x] Confirm identity model (fingerprint guest + claim account).
- [x] Confirm collaboration/domain model (multi-band, multi-project, per-band projects).
- [x] Confirm data migration policy (DB reset, no backward compatibility).
- [x] Confirm player entry model (from song list/detail into dedicated player route).
- [x] Confirm stem download scope (single stem + download all zip).

## Goal

Refactor DeChord web app frontend to use `designs.opus46/5-3` as the new production UX baseline while extending the backend/frontend domain model to support multi-user collaboration across multiple bands and projects, with a dedicated player screen entered from song navigation.

## Confirmed Product Decisions

- Redesign source of truth: `designs.opus46/5-3`.
- Navigation hierarchy: band list -> project list -> song list -> song detail -> dedicated player.
- Player must remain separate from song/project lists (no merged single-screen workspace).
- Full registration/auth is skipped for now.
- Identity is lightweight:
  - Browser fingerprint creates persistent guest user automatically.
  - Guest receives generated musician-style display name.
  - User can claim identity later with username + password.
- Data model reset is allowed and preferred.
- Collaboration supports multiple bands and multiple projects.
- Each project belongs to exactly one band.
- Stem downloads include per-stem and download-all-as-zip.

## Architecture

### Frontend

- Replace current single-page panel-heavy app shell with route-driven page flow matching `designs.opus46/5-3`:
  - `LandingPage`
  - `BandSelectPage`
  - `ProjectHomePage`
  - `SongLibraryPage`
  - `SongDetailPage`
  - `PlayerPage`
- Keep existing player feature depth (transport/chords/fretboard/tabs/stems/notes), but align visuals and layout to Opus 5-3.
- Use API-backed data in production app, with mock fallback adapters where APIs are not yet implemented.
- Keep auth UX minimal: guest badge + “Claim account” flow in header/account panel.

### Backend

- Reset schema and bootstrap a new normalized collaboration model:
  - `users`
  - `user_credentials` (for claimed accounts)
  - `bands`
  - `band_memberships`
  - `projects`
  - `songs`
  - `analyses`, `analysis_chords`
  - `song_stems`
  - `notes`
  - `playback_prefs`
- Preserve existing analysis/stems/tabs pipeline behavior where possible while re-keying ownership to project/song relations.
- Add endpoints for:
  - guest identity resolution by fingerprint
  - claim account
  - bands/projects CRUD (initially lightweight)
  - song listing by project
  - stem download single + zip

## Data and Identity Model

### Identity lifecycle

1. Client computes/stores browser fingerprint token.
2. On app load, client calls identity endpoint.
3. Backend returns existing user or creates guest user:
   - generated musician-style display name
   - `is_claimed = false`
4. User may claim account:
   - choose username
   - set password
   - backend stores secure password hash
   - mark user as claimed

### Collaboration model

- Many-to-many: users <-> bands through memberships.
- One-to-many: band -> projects.
- One-to-many: project -> songs.
- Songs retain stems, analysis, notes, and playback prefs.
- Notes remain visible with open/resolved state and author context.

## UX and Feature Requirements

- Full Opus 5-3 visual language in production frontend.
- Project and song browsing are separate pages from playback.
- Song detail supports:
  - stem list with metadata
  - collaborator comments/history
  - actions to open player and manage stems
- Player supports:
  - chord timeline
  - fretboard guidance
  - transport controls
  - tab viewer
  - stem mixer with versions
  - notes/comments panel
- Stem download actions:
  - single-stem file download
  - all stems zip download

## Out of Scope (This Iteration)

- Full auth suite (sessions, JWT, OAuth, password reset).
- Strict authorization policies beyond basic ownership/membership checks.
- Backward-compatible migration from old DB schema/data.

## Risks and Mitigations

- Risk: API/frontend mismatch during phased replacement.
  - Mitigation: adapter layer + contract tests for new endpoints.
- Risk: identity collisions or weak fingerprint uniqueness.
  - Mitigation: fingerprint token + random fallback suffix + claim flow.
- Risk: redesign regressions in player behavior.
  - Mitigation: preserve player logic tests, add route-flow integration tests.

## Verification Strategy

- Frontend: unit/integration tests for routing, identity bootstrap, player entry flow, stem download actions.
- Backend: API tests for identity, band/project/song traversal, stem zip endpoint.
- End-to-end sanity:
  - guest lands in app
  - selects band/project/song
  - enters player
  - downloads single stem and zip

## Implementation Handoff

Implementation plan is defined in:

- `docs/plans/2026-03-09-opus53-frontend-redesign-implementation.md`

The execution session should use isolated worktree branch `codex/frontend-opus46-5-3` and follow task-by-task TDD.
