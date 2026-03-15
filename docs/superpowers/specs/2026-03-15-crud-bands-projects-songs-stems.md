# Spec: CRUD — Bands, Projects, Songs, Stems

**Date:** 2026-03-15
**Status:** Approved

---

## Problem

Bands, projects, songs, and stems lack rename and archive operations. Users cannot organise or clean up their workspace without permanently losing data. Stems already have a backend rename/delete API but no frontend UI.

---

## Goals

- Rename bands, projects, songs, and stems from the UI
- Archive any entity (soft-delete: hidden by default, recoverable)
- Cascade archive/unarchive down the ownership tree
- "Show archived" toggle per list to view and interact with archived items
- Surface `original_filename` alongside `title` for songs (read-only)

---

## Non-Goals

- Hard (permanent) delete — deferred to a future cleanup feature
- Bulk archive / multi-select
- Move songs between projects or projects between bands

---

## Data Layer

Add `archived_at TEXT` (nullable, ISO-8601) to four tables via `_ensure_column` migrations. No existing columns are changed.

```sql
-- migrations in _run_schema_migrations()
await _ensure_column("bands",      "archived_at", "archived_at TEXT")
await _ensure_column("projects",   "archived_at", "archived_at TEXT")
await _ensure_column("songs",      "archived_at", "archived_at TEXT")
await _ensure_column("song_stems", "archived_at", "archived_at TEXT")
```

### Cascade rules (explicit SQL in each PATCH handler)

| Action | Cascades to |
|---|---|
| Archive band | band → its projects → their songs → their stems |
| Unarchive band | same cascade, clears `archived_at` |
| Archive project | project → its songs → their stems |
| Unarchive project | same cascade down |
| Archive song | song → its stems |
| Unarchive song | same cascade down |
| Archive stem | stem only |
| Unarchive stem | stem only |

Cascade is implemented as explicit `UPDATE ... WHERE` SQL in the handler, not via FK triggers, for clarity and testability.

**Unarchive cascade behaviour:** Unarchiving a parent restores ALL descendants regardless of their pre-existing `archived_at` state. There is no distinction between "archived by user" and "archived by cascade." This is an explicit design choice — since hard delete is a future feature, accidental restores are low-risk and users can re-archive individual items as needed.

---

## Backend API

### New endpoints

```
PATCH /api/bands/{id}
  Request:  { name?: str, archived?: bool }
  Response: updated band object (includes archived_at)
  Events:   band_renamed | band_archived | band_unarchived

PATCH /api/projects/{id}
  Request:  { name?: str, archived?: bool }
  Response: updated project object
  Events:   project_renamed | project_archived | project_unarchived

PATCH /api/songs/{id}
  Request:  { title?: str, archived?: bool }
  Response: updated song object (title + original_filename both returned)
  Events:   song_renamed | song_archived | song_unarchived
  Note:     original_filename is read-only; renaming only changes title
```

### Updated endpoint

```
PATCH /api/stems/{stem_id}   (already exists)
  Request:  { display_name?: str, description?: str, archived?: bool }
  Response: updated stem object (includes archived_at)
  Events:   stem_updated | stem_archived | stem_unarchived
```

### Updated list endpoints

All four GET list endpoints gain an optional query param:

```
GET /api/bands                       ?include_archived=true
GET /api/bands/{id}/projects         ?include_archived=true
GET /api/projects/{id}/songs         ?include_archived=true   (or equivalent)
GET /api/songs/{id}/stems            ?include_archived=true
```

**Filtering semantics:**
- Default (`include_archived` absent or `false`): returns only rows where `archived_at IS NULL` (active items only).
- `?include_archived=true`: returns ALL rows — both active and archived. Not "archived only."
- Filtering is applied to the **directly queried entity only**, based on its own `archived_at`. Ancestor archived state is not considered — if a song is archived and thus hidden from the project song list, its stems are naturally unreachable from the UI.

All serialisers add `"archived_at": row["archived_at"]` (string or null).

**Idempotency:** PATCH is idempotent. Sending `archived: true` on an already-archived entity returns 200 with the current state unchanged. No 409 conflict.

### Pydantic request models

```python
class BandUpdateRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    archived: bool | None = None

class ProjectUpdateRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    archived: bool | None = None

class SongUpdateRequest(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=200)
    archived: bool | None = None

# StemUpdateRequest — add field:
    archived: bool | None = None
```

Name/title fields: min 1 character (blank strings rejected with 422), max 200 characters. Whitespace-only strings are rejected by FastAPI's `min_length=1` after stripping is not applied — the validator rejects a single space. If stricter trimming is desired, add a `@field_validator`.

---

## Frontend

### `lib/types.ts` changes

Add `archived_at: string | null` to:
- `BandSummary`
- `ProjectSummary` (or equivalent band-project type)
- `SongSummary`
- `SongStem`

### `lib/api.ts` additions

```ts
updateBand(id: number, payload: { name?: string; archived?: boolean }): Promise<BandSummary>
updateProject(id: number, payload: { name?: string; archived?: boolean }): Promise<ProjectSummary>
updateSong(id: number, payload: { title?: string; archived?: boolean }): Promise<SongSummary>
// extend existing updateStem (or patch function) to accept archived?: boolean
```

All list functions gain an optional `includeArchived?: boolean` parameter that appends `?include_archived=true` to the request URL.

### Reusable `ThreeDotMenu` component

**File:** `frontend/src/components/ThreeDotMenu.tsx`

```ts
interface MenuItem {
  label: string
  onClick: () => void
  variant?: 'default' | 'danger'
}
interface ThreeDotMenuProps {
  items: MenuItem[]
}
```

- Renders a `⋮` button (small, `opacity-40 hover:opacity-100`)
- On click: renders a small absolute-positioned dropdown with the menu items
- Closes on outside click or Escape
- No external dependency — plain React + Tailwind

### Rename modal

**File:** `frontend/src/components/RenameModal.tsx`

- Single text input pre-filled with current name
- Save / Cancel buttons
- Calls the appropriate update API function on Save
- Shared across bands, projects, songs, stems (label and callback passed as props)
- **For songs only:** below the editable title input, render a read-only row: `Original filename: <original_filename>` in small muted text. This also appears as a secondary line in the `SongLibraryPanel` song list rows (below the title, same muted style).

### "Show archived" toggle

Inline toggle above each list. Label: `"Show archived"`. When on, the list refetches with `include_archived=true`. Archived items render with `opacity-50` and a small grey `"Archived"` pill badge next to the name.

### Per-list integration

| Component | File (approx.) | ⋮ menu items | Show archived toggle |
|---|---|---|---|
| Band list | `BandSelectPage.tsx` | Rename, Archive / Unarchive | Above band list |
| Project list | band detail view | Rename, Archive / Unarchive | Above project list |
| Song library | `SongLibraryPanel.tsx` | Rename, Archive / Unarchive | Above song list |
| Stem list | stem panel / mixer | Rename, Edit description, Archive / Unarchive | Above stem list |

Menu items are conditional: archived items show "Unarchive" instead of "Archive".

---

## Testing

### Backend (pytest)

- `test_patch_band_rename` — rename changes `name`, `updated_at`
- `test_patch_band_archive` — sets `archived_at`, cascades to projects/songs/stems
- `test_patch_band_unarchive` — clears `archived_at` on band + all children
- `test_list_bands_excludes_archived_by_default`
- `test_list_bands_includes_archived_with_param`
- Identical pattern for projects, songs, stems

### Frontend (Vitest)

- Contract tests in existing `api.test.ts` for `updateBand`, `updateProject`, `updateSong`
- `ThreeDotMenu` renders correct items and fires callbacks
- `RenameModal` calls API and closes on save

---

## Implementation Order

Tests are written before implementation code (TDD). The order below reflects this:

1. DB migrations (add `archived_at` to all 4 tables)
2. Backend tests (pytest) — write failing tests for all PATCH routes and list filtering
3. Backend: PATCH routes for bands, projects, songs + extend stems PATCH (make tests pass)
4. Backend: update list endpoints with `include_archived` param (make tests pass)
5. Frontend: types + api.ts functions + contract tests (Vitest)
6. Frontend: `ThreeDotMenu` + `RenameModal` components + component tests
7. Frontend: wire into BandSelectPage, project list, SongLibraryPanel, stem list
