# Song Overview — Comment Threading & Timestamp Removal

**Date:** 2026-03-14
**Status:** Approved
**Scope:** `SongDetailPage` only — Player page is out of scope and must not be changed.

---

## Problem

The comment section on the Song Overview (right sidebar of `SongDetailPage`) has two issues:

1. **Timestamp / chord-type input is noise.** The song overview has no playback context — no waveform, no chord timeline. Forcing users to pick "Time Note" or "Chord Note" and enter a timestamp is meaningless friction.

2. **No reply threading.** Comments are a flat list. There is no way to respond to a specific comment, which limits collaboration between band members.

---

## Goals

- Remove timestamp and note-type selector from the comment creation form on Song Overview.
- Show existing top-level comments with a Reply button on each.
- Allow one level of threaded replies (replies to top-level comments only).
- Leave the Player's time/chord note functionality completely untouched.

---

## Out of Scope

- Player page note creation or display.
- Recursive (multi-level) threading.
- Edit / resolve on replies (can be added later).
- Pagination or infinite scroll of comments.

---

## Data Model

### DB — `notes` table (additive migration via `_ensure_column`)

One new nullable column:

| Column | Type | Default | Notes |
|---|---|---|---|
| `parent_id` | `INTEGER` | `NULL` | FK → `notes.id`. `NULL` = top-level comment. Non-null = reply. |

No existing rows are touched. No columns are removed.

**Cascade delete:** When a top-level note is deleted, its replies (notes with `parent_id = <deleted_id>`) must also be deleted. The `delete_note` endpoint must issue `DELETE FROM notes WHERE parent_id = ?` before deleting the parent row.

### New note type: `"general"`

The `type` column currently accepts `"time"` and `"chord"`. A new value `"general"` is added:

- No `timestamp_sec` required.
- No `chord_index` required.
- Used exclusively from the Song Overview comment form.
- Existing `"time"` and `"chord"` notes created by the Player are unaffected.

### Frontend `SongNote` type

Both `frontend/src/redesign/lib/types.ts` and `frontend/src/lib/types.ts`:

```ts
export interface SongNote {
  id: number;
  type: "time" | "chord" | "general";   // "general" added
  timestampSec: number | null;
  chordIndex: number | null;
  text: string;
  toastDurationSec: number | null;
  authorName: string | null;
  authorAvatar: string | null;
  resolved: boolean;
  parentId: number | null;               // new
  createdAt: string;
  updatedAt: string;
}
```

---

## API

### `NoteCreate` Pydantic model — updated

Current:
```python
class NoteCreate(BaseModel):
    type: Literal["time", "chord"]
    timestamp_sec: float | None = None
    chord_index: int | None = None
    text: str
    toast_duration_sec: float | None = None
```

Updated:
```python
class NoteCreate(BaseModel):
    type: Literal["time", "chord", "general"]   # "general" added
    timestamp_sec: float | None = None
    chord_index: int | None = None
    text: str
    toast_duration_sec: float | None = None
    parent_id: int | None = None                # new
```

### `POST /api/songs/{song_id}/notes` — updated validation rules

- `type == "time"` → `timestamp_sec` required (unchanged).
- `type == "chord"` → `chord_index` required (unchanged).
- `type == "general"` → neither `timestamp_sec` nor `chord_index` required.
- **Depth guard:** if `parent_id` is provided, verify the referenced note exists and has `parent_id IS NULL`. If the referenced note is itself a reply, return HTTP 400: `"Cannot reply to a reply"`. This enforces the single-level threading invariant.
- `parent_id` is written to the `notes` table.

### `_load_song_notes` — updated

Include `parent_id` in the `SELECT` and in the serialized dict returned to the client:
```python
{ ..., "parent_id": row[n] }  # mapped to parentId on frontend
```

### `DELETE /api/notes/{note_id}` — updated

Before deleting the note, delete its replies:
```sql
DELETE FROM notes WHERE parent_id = ?
```
Then delete the note itself.

### All other note endpoints (`PATCH`, resolve)

Unchanged. Replies always have `resolved = False` at creation and should not be resolved via the UI (no resolve button on replies). The `PATCH /resolve` endpoint need not block calls for replies — it just won't be wired up in the UI.

### `frontend/src/lib/api.ts` — updated

`createSongNote` currently:
```ts
export async function createSongNote(
  songId: string,
  payload: { type: "time" | "chord"; text: string; timestamp_sec?: number | null; chord_index?: number | null; toast_duration_sec?: number | null }
): Promise<SongNote>
```

Updated signature:
```ts
export async function createSongNote(
  songId: string,
  payload: {
    type: "time" | "chord" | "general";
    text: string;
    timestamp_sec?: number | null;
    chord_index?: number | null;
    toast_duration_sec?: number | null;
    parent_id?: number | null;
  }
): Promise<SongNote>
```

No new function needed — `createSongNote` with `parent_id` set handles replies.

---

## Frontend — `SongDetailPage`

### Simplified comment creation form

**Removed state:**
- `noteType` — radio button state
- `timestampDraft` — timestamp string state
- `parseTimestampDraft` helper function

**Retained:**
- `noteText` state
- Textarea + "Add Comment" button

**Payload sent on submit:**
```ts
{ type: "general", text: trimmedText }
```

### Updated `SongDetailPageProps`

`onCreateNote` payload type scoped to what the Song Overview sends:
```ts
onCreateNote?: (payload: { type: "general"; text: string; parentId?: number | null }) => Promise<void> | void;
```

New prop:
```ts
onCreateReply?: (parentId: number, text: string) => Promise<void> | void;
```

### `App.tsx` handler update

The `onCreateNote` handler at lines ~987 and ~1034 currently destructures:
```ts
async ({ type, text, timestampSec, chordIndex, toastDurationSec }: { ... })
```

For the Song Overview wiring, update both `SongDetailPage` usages to:
```ts
onCreateNote={async ({ text }: { type: "general"; text: string }) => {
  await createSongNote(song.id, { type: "general", text });
  // refresh song
}}
onCreateReply={async (parentId: number, text: string) => {
  await createSongNote(song.id, { type: "general", text, parent_id: parentId });
  // refresh song
}}
```

The Player's `onCreateNote` handler (which passes `"time"` / `"chord"` types) is **not changed**.

### Comment list restructure

**Grouping logic (computed in component, no backend change):**
```ts
const topLevel = song.notes.filter(n => n.parentId === null && !n.resolved);
const repliesFor = (id: number) => song.notes.filter(n => n.parentId === id);
```

Sort top-level and replies by `createdAt` ascending.

**Per top-level comment:**
- Author avatar + name
- Comment text
- "Reply" button → toggles inline reply form (only one open at a time, tracked by `replyingToId: number | null` state)
- Edit / Resolve / Delete actions (unchanged from today)
- Replies rendered indented below, each showing: author avatar + name + text + Delete button

**Inline reply form:**
- Textarea + "Post Reply" + "Cancel"
- On submit: calls `onCreateReply(parentId, text)`
- Collapses on successful submit or Cancel

**Resolved comments:**
- Toggle "Show resolved" remains unchanged.
- Replies of a resolved parent are shown/hidden together with the parent.

### `mockData.ts` factory update

Add `parentId` parameter with a default of `null`:
```ts
function note(
  id: number,
  type: "time" | "chord" | "general",
  ts: number | null,
  ci: number | null,
  text: string,
  author: string,
  avatar: string,
  resolved = false,
  parentId: number | null = null   // new, default null
): SongNote {
  return { id, type, timestampSec: ts, chordIndex: ci, text, toastDurationSec: null,
           authorName: author, authorAvatar: avatar, resolved, parentId,
           createdAt: "2026-03-01T10:00:00Z", updatedAt: "2026-03-01T10:00:00Z" };
}
```

All existing `note(...)` call sites are unaffected (default applies).

---

## Affected Files

| File | Change |
|---|---|
| `backend/app/db.py` | `_ensure_column("notes", "parent_id", "parent_id INTEGER")` |
| `backend/app/main.py` | `NoteCreate` model, `create_note` depth guard, `delete_note` cascade, `_load_song_notes` |
| `frontend/src/redesign/lib/types.ts` | `SongNote.parentId`, `type` union extended |
| `frontend/src/lib/types.ts` | same |
| `frontend/src/redesign/lib/mockData.ts` | `note()` factory gains `parentId` param with default |
| `frontend/src/redesign/pages/SongDetailPage.tsx` | form simplification + threading UI + new `onCreateReply` prop |
| `frontend/src/lib/api.ts` | `createSongNote` signature extended with `parent_id` |
| `App.tsx` (Song Overview wiring ~line 987, ~1034) | update `onCreateNote` handler + add `onCreateReply` handler |

**Player files (`PlayerPage.tsx`, player-related components) are not modified.**

---

## Testing

- **Frontend unit:** `SongDetailPage` tests — remove timestamp assertions, add: reply button renders, inline form submits, replies shown indented, delete on reply works.
- **Backend `test_api.py`:** `POST /api/songs/{id}/notes` with `type: "general"` (no timestamp); with `parent_id` referencing a top-level note; with `parent_id` referencing a reply (expect 400); confirm `"time"` notes still require `timestamp_sec`.
- **Cascade delete test:** delete a top-level note that has replies → replies are gone.
- **Existing Player tests** must pass without modification.
