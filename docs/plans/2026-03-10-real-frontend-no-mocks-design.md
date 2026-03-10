# Real Frontend No-Mocks Design

**Date:** 2026-03-10

**Goal:** Remove redesign-only mock fallback from the real frontend and replace it with honest API-driven empty states plus real inline creation flows for bands, projects, and songs.

## Problem

The current redesign shell still falls back to frontend mock data when the backend hierarchy is empty or unavailable. After `make reset`, that makes the real app show invented bands, projects, songs, stems, and comments. That is unacceptable for the production-facing frontend because it hides missing backend state behind fake content.

## Requirements

- No redesign mock fallback in the real app.
- Guest identity should come only from fingerprint resolution.
- A user can belong to multiple bands.
- A band can have multiple projects.
- The real frontend must support:
  - viewing empty states honestly
  - creating a band inline
  - creating a project inline
  - uploading songs into the selected project
- Reset may clear local runtime state, but the frontend must never replace emptiness with fabricated records.

## Recommended Approach

Use inline creation panels inside the existing Opus 5-3 shell.

### Band Layer

- Remove `MOCK_BANDS` fallback from `frontend/src/App.tsx`.
- Keep `BandSelectPage` API-driven.
- If the authenticated guest has zero bands, render an empty state with an inline `Create Band` panel.
- Creating a band should also create the initial membership row for the current user.

### Project Layer

- Add a real backend route for creating a project under a band.
- Keep `ProjectHomePage` API-driven.
- If the selected band has zero projects, render an empty state with an inline `Create Project` panel.
- If a band has projects, still offer inline project creation from the sidebar area so the user can add more without leaving context.

### Song Layer

- Keep `SongLibraryPage` honest when a project has zero songs.
- Reuse the existing upload backend where possible, but route the resulting song into the selected project instead of relying on default-project-only behavior.
- Preserve the current upload UI direction, but wire it to actual file selection and actual API submission.

## Backend Changes

### New API Endpoints

- `POST /api/bands`
- `POST /api/bands/{band_id}/projects`

These should persist real records and associate them with the resolved user. The existing schema already supports:
- multiple bands per owner
- multiple memberships per user
- multiple projects per band

### Upload Flow Adjustment

The current analyze/upload flow creates songs in the default project. The real frontend needs project-scoped upload, so the upload endpoint should accept a project identifier and persist the new song there.

## Frontend Changes

### Remove Mocking

- Delete real-app dependency on `frontend/src/redesign/lib/mockData.ts`.
- Replace fallback behavior with:
  - loading state
  - inline error state
  - inline empty states

### Inline Panels

- `BandSelectPage`
  - empty state copy
  - create band form
- `ProjectHomePage`
  - empty state for no projects
  - create project form
- `SongLibraryPage`
  - real upload form with file input
  - empty state for no songs

## UX Notes

- Keep the existing Opus 5-3 language.
- Empty states should feel intentional, not broken.
- Do not use browser `prompt()` for creation.
- Do not silently auto-create a default band/project just to avoid emptiness.

## Testing

- frontend integration test proving empty backend state renders empty states, not mocks
- frontend tests for inline band/project creation flows
- frontend test for real upload submission from song library
- backend tests for create-band and create-project routes
- backend tests for project-scoped upload persistence

## Success Criteria

This change is successful when:

- the real frontend never renders redesign mock content
- a fresh reset shows an honest empty state
- the guest user can create a band and a project inline
- the user can upload songs into a real selected project
- band/project/song lists refresh from backend data only
