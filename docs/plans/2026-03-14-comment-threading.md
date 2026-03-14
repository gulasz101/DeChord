# Comment Threading & Timestamp Removal — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the timestamp/type selector from the Song Overview comment form, and add one-level-deep reply threading to the comments sidebar.

**Architecture:** Additive DB migration (`parent_id` column + `"general"` note type), a minimal backend endpoint change, updated TypeScript types, a simplified comment form, and a threaded comment list — all scoped to `SongDetailPage`. The Player is untouched.

**Tech Stack:** Python 3.13+, FastAPI, LibSQL, pytest, uv / React 19, TypeScript, Vite, Tailwind v4, Vitest, @testing-library/react, bun

**Spec:** `docs/superpowers/specs/2026-03-14-song-overview-comment-threading-design.md`

---

## File Map

| File | Change |
|---|---|
| `backend/app/db.py` | Add `_ensure_column` call for `parent_id` |
| `backend/app/main.py` | `NoteCreate` model, `create_note` validation, `_load_song_notes`, `delete_note` cascade |
| `backend/tests/test_api.py` | Tests for `"general"` type, `parent_id`, depth guard, cascade delete |
| `frontend/src/redesign/lib/types.ts` | `SongNote.parentId`, `type` union |
| `frontend/src/lib/types.ts` | Same |
| `frontend/src/lib/api.ts` | `createSongNote` signature |
| `frontend/src/redesign/lib/mockData.ts` | `note()` factory gains `parentId` param |
| `frontend/src/redesign/pages/SongDetailPage.tsx` | Form simplification + threading UI + `onCreateReply` prop |
| `frontend/src/redesign/pages/__tests__/SongDetailPage.test.tsx` | Remove timestamp tests, add threading tests |
| `App.tsx` (lines ~987, ~1034) | Update `onCreateNote` handler, add `onCreateReply` handler |

---

## Chunk 1: Backend — DB, Model, Endpoints

### Task 1: DB migration — add `parent_id` column

**Files:**
- Modify: `backend/app/db.py`

- [ ] **Step 1: Locate the `_ensure_column` block for notes**

  Open `backend/app/db.py`. Find the block around line 124 that calls `_ensure_column("notes", "author_user_id", ...)`. Add the `parent_id` column immediately after the existing `author_avatar` ensure call:

  ```python
  await _ensure_column("notes", "parent_id", "parent_id INTEGER")
  ```

  This is a safe additive migration — existing rows get `NULL` automatically.

- [ ] **Step 2: Verify the column appears in the migration sequence**

  The `_ensure_column` function adds a column only if it doesn't already exist, so it is idempotent. No further migration code is needed.

  > **TDD note:** No isolated test is written for this migration step. The `parent_id` column is validated implicitly by the tests in Task 2 (which insert and read `parent_id`). If the column is missing those tests will fail.

- [ ] **Step 3: Commit**

  ```bash
  git add backend/app/db.py
  git commit -m "feat(db): add parent_id column to notes table

  Plan: docs/plans/2026-03-14-comment-threading.md task 1
  Tool: opencode | Model: gpt-5.1-codex-max"
  ```

---

### Task 2: Extend `NoteCreate` model and `create_note` endpoint

**Files:**
- Modify: `backend/app/main.py` (lines ~131–138 for model, ~2204–2260 for endpoint)

- [ ] **Step 1: Write the failing backend test first**

  Open `backend/tests/test_api.py`. After the last note-related test block (around line 767), add the following five tests. Each test self-contains its own setup using `_build_client` (the existing helper already used throughout this file). Use `tmp_path` and `monkeypatch` as pytest built-in parameters.

  > **Setup pattern** used throughout `test_api.py` (match exactly):
  > ```python
  > def test_xxx(tmp_path, monkeypatch):
  >     client = _build_client(tmp_path, monkeypatch)
  >     import app.main as main  # noqa: PLC0415
  >     band = client.post("/api/bands", json={"name": f"Band {tmp_path.name}"}).json()["band"]
  >     project = client.post(f"/api/bands/{band['id']}/projects", json={"name": "P", "description": ""}).json()["project"]
  >     song = client.post("/api/analyze", files={"file": ("demo.mp3", b"audio-bytes", "audio/mpeg")}, data={"process_mode": "analysis_only", "project_id": str(project["id"])}, headers={"X-DeChord-User-Id": "1"})
  >     song_id = song.json()["song_id"]
  > ```

  ```python
  def test_general_note_no_timestamp_required(tmp_path, monkeypatch):
      """General notes must not require timestamp_sec or chord_index."""
      client = _build_client(tmp_path, monkeypatch)
      band = client.post("/api/bands", json={"name": f"Band {tmp_path.name}"}).json()["band"]
      project = client.post(f"/api/bands/{band['id']}/projects", json={"name": "P", "description": ""}).json()["project"]
      song = client.post("/api/analyze", files={"file": ("demo.mp3", b"audio-bytes", "audio/mpeg")}, data={"process_mode": "analysis_only", "project_id": str(project["id"])}, headers={"X-DeChord-User-Id": "1"})
      song_id = song.json()["song_id"]

      res = client.post(
          f"/api/songs/{song_id}/notes",
          json={"type": "general", "text": "Great bassline here"},
          headers={"X-DeChord-User-Id": "1"},
      )
      assert res.status_code == 200
      body = res.json()
      assert body["type"] == "general"
      assert body["timestamp_sec"] is None
      assert body["chord_index"] is None
      assert body.get("parent_id") is None


  def test_general_note_parent_id_returned_in_song_load(tmp_path, monkeypatch):
      """parent_id must be returned by the song GET endpoint via _load_song_notes."""
      import asyncio
      import app.main as main  # noqa: PLC0415

      client = _build_client(tmp_path, monkeypatch)
      band = client.post("/api/bands", json={"name": f"Band {tmp_path.name}"}).json()["band"]
      project = client.post(f"/api/bands/{band['id']}/projects", json={"name": "P", "description": ""}).json()["project"]
      song = client.post("/api/analyze", files={"file": ("demo.mp3", b"audio-bytes", "audio/mpeg")}, data={"process_mode": "analysis_only", "project_id": str(project["id"])}, headers={"X-DeChord-User-Id": "1"})
      song_id = song.json()["song_id"]

      parent = client.post(f"/api/songs/{song_id}/notes", json={"type": "general", "text": "Top"}, headers={"X-DeChord-User-Id": "1"})
      parent_id = parent.json()["id"]
      client.post(f"/api/songs/{song_id}/notes", json={"type": "general", "text": "Reply", "parent_id": parent_id}, headers={"X-DeChord-User-Id": "1"})

      # Fetch song and inspect notes
      song_detail = client.get(f"/api/songs/{song_id}", headers={"X-DeChord-User-Id": "1"})
      notes = song_detail.json()["notes"]
      reply_note = next(n for n in notes if n["text"] == "Reply")
      assert reply_note["parent_id"] == parent_id


  def test_general_note_with_parent_id(tmp_path, monkeypatch):
      """A reply must reference a top-level note."""
      client = _build_client(tmp_path, monkeypatch)
      band = client.post("/api/bands", json={"name": f"Band {tmp_path.name}"}).json()["band"]
      project = client.post(f"/api/bands/{band['id']}/projects", json={"name": "P", "description": ""}).json()["project"]
      song = client.post("/api/analyze", files={"file": ("demo.mp3", b"audio-bytes", "audio/mpeg")}, data={"process_mode": "analysis_only", "project_id": str(project["id"])}, headers={"X-DeChord-User-Id": "1"})
      song_id = song.json()["song_id"]

      parent = client.post(f"/api/songs/{song_id}/notes", json={"type": "general", "text": "Top-level comment"}, headers={"X-DeChord-User-Id": "1"})
      assert parent.status_code == 200
      parent_id = parent.json()["id"]

      reply = client.post(f"/api/songs/{song_id}/notes", json={"type": "general", "text": "Reply to that", "parent_id": parent_id}, headers={"X-DeChord-User-Id": "1"})
      assert reply.status_code == 200
      assert reply.json()["parent_id"] == parent_id


  def test_reply_to_reply_rejected(tmp_path, monkeypatch):
      """Replying to a reply must return HTTP 400."""
      client = _build_client(tmp_path, monkeypatch)
      band = client.post("/api/bands", json={"name": f"Band {tmp_path.name}"}).json()["band"]
      project = client.post(f"/api/bands/{band['id']}/projects", json={"name": "P", "description": ""}).json()["project"]
      song = client.post("/api/analyze", files={"file": ("demo.mp3", b"audio-bytes", "audio/mpeg")}, data={"process_mode": "analysis_only", "project_id": str(project["id"])}, headers={"X-DeChord-User-Id": "1"})
      song_id = song.json()["song_id"]

      parent = client.post(f"/api/songs/{song_id}/notes", json={"type": "general", "text": "Top"}, headers={"X-DeChord-User-Id": "1"})
      parent_id = parent.json()["id"]

      reply = client.post(f"/api/songs/{song_id}/notes", json={"type": "general", "text": "Reply", "parent_id": parent_id}, headers={"X-DeChord-User-Id": "1"})
      reply_id = reply.json()["id"]

      nested = client.post(f"/api/songs/{song_id}/notes", json={"type": "general", "text": "Nested", "parent_id": reply_id}, headers={"X-DeChord-User-Id": "1"})
      assert nested.status_code == 400


  def test_time_note_still_requires_timestamp(tmp_path, monkeypatch):
      """Existing time-note validation must not regress."""
      client = _build_client(tmp_path, monkeypatch)
      band = client.post("/api/bands", json={"name": f"Band {tmp_path.name}"}).json()["band"]
      project = client.post(f"/api/bands/{band['id']}/projects", json={"name": "P", "description": ""}).json()["project"]
      song = client.post("/api/analyze", files={"file": ("demo.mp3", b"audio-bytes", "audio/mpeg")}, data={"process_mode": "analysis_only", "project_id": str(project["id"])}, headers={"X-DeChord-User-Id": "1"})
      song_id = song.json()["song_id"]

      res = client.post(f"/api/songs/{song_id}/notes", json={"type": "time", "text": "Missing timestamp"}, headers={"X-DeChord-User-Id": "1"})
      assert res.status_code == 400


  def test_delete_note_cascades_replies(tmp_path, monkeypatch):
      """Deleting a top-level note must delete its replies."""
      import asyncio
      import app.main as main  # noqa: PLC0415

      client = _build_client(tmp_path, monkeypatch)
      band = client.post("/api/bands", json={"name": f"Band {tmp_path.name}"}).json()["band"]
      project = client.post(f"/api/bands/{band['id']}/projects", json={"name": "P", "description": ""}).json()["project"]
      song = client.post("/api/analyze", files={"file": ("demo.mp3", b"audio-bytes", "audio/mpeg")}, data={"process_mode": "analysis_only", "project_id": str(project["id"])}, headers={"X-DeChord-User-Id": "1"})
      song_id = song.json()["song_id"]

      parent = client.post(f"/api/songs/{song_id}/notes", json={"type": "general", "text": "Parent"}, headers={"X-DeChord-User-Id": "1"})
      parent_id = parent.json()["id"]

      reply = client.post(f"/api/songs/{song_id}/notes", json={"type": "general", "text": "Child", "parent_id": parent_id}, headers={"X-DeChord-User-Id": "1"})
      reply_id = reply.json()["id"]

      del_res = client.delete(f"/api/notes/{parent_id}", headers={"X-DeChord-User-Id": "1"})
      assert del_res.status_code == 200

      rows = asyncio.run(
          main.execute("SELECT id FROM notes WHERE id = ?", [reply_id])
      ).rows
      assert rows == []
  ```

- [ ] **Step 2: Run tests to confirm they fail**

  ```bash
  cd /Users/wojciechgula/Projects/DeChord/backend
  uv run pytest tests/test_api.py::test_general_note_no_timestamp_required tests/test_api.py::test_general_note_with_parent_id tests/test_api.py::test_reply_to_reply_rejected tests/test_api.py::test_time_note_still_requires_timestamp tests/test_api.py::test_delete_note_cascades_replies -v
  ```

  Expected: all fail (422/400 errors, missing columns).

- [ ] **Step 3: Update `NoteCreate` model**

  In `backend/app/main.py`, find `class NoteCreate` (line ~131). Replace it with:

  ```python
  class NoteCreate(BaseModel):
      type: Literal["time", "chord", "general"]
      timestamp_sec: float | None = None
      chord_index: int | None = None
      text: str
      toast_duration_sec: float | None = None
      parent_id: int | None = None
  ```

- [ ] **Step 4: Update `create_note` endpoint validation**

  In `backend/app/main.py`, find `async def create_note` (line ~2205). The current validation block is:

  ```python
  if payload.type == "time" and payload.timestamp_sec is None:
      raise HTTPException(400, "timestamp_sec is required for time notes")
  if payload.type == "chord" and payload.chord_index is None:
      raise HTTPException(400, "chord_index is required for chord notes")
  ```

  Replace it with:

  ```python
  if payload.type == "time" and payload.timestamp_sec is None:
      raise HTTPException(400, "timestamp_sec is required for time notes")
  if payload.type == "chord" and payload.chord_index is None:
      raise HTTPException(400, "chord_index is required for chord notes")
  if payload.parent_id is not None:
      parent_rs = await execute(
          "SELECT parent_id FROM notes WHERE id = ?", [payload.parent_id]
      )
      if not parent_rs.rows:
          raise HTTPException(400, "parent note not found")
      if parent_rs.rows[0][0] is not None:
          raise HTTPException(400, "Cannot reply to a reply")
  ```

- [ ] **Step 5: Add `parent_id` to the INSERT statement**

  Still in `create_note`, update the `INSERT INTO notes` SQL:

  ```python
  inserted = await execute(
      """
      INSERT INTO notes (
          song_id,
          author_user_id,
          author_name,
          author_avatar,
          type,
          timestamp_sec,
          chord_index,
          text,
          toast_duration_sec,
          resolved,
          parent_id
      )
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
      RETURNING id
      """,
      [
          song_id,
          author["id"],
          author_name,
          author_avatar,
          payload.type,
          payload.timestamp_sec,
          payload.chord_index,
          payload.text,
          payload.toast_duration_sec,
          payload.parent_id,
      ],
  )
  ```

  Also add `"parent_id": payload.parent_id` to the returned dict:

  ```python
  return {
      "id": note_id,
      "song_id": song_id,
      "author_user_id": author["id"],
      "author_name": author_name,
      "author_avatar": author_avatar,
      "resolved": False,
      "parent_id": payload.parent_id,
      **payload.model_dump(),
  }
  ```

- [ ] **Step 6: Update `_load_song_notes` to return `parent_id`**

  Find `async def _load_song_notes` (line ~193). The current SELECT fetches 12 columns in this order:
  `id(0), author_user_id(1), author_name(2), author_avatar(3), type(4), timestamp_sec(5), chord_index(6), text(7), toast_duration_sec(8), resolved(9), created_at(10), updated_at(11)`

  Add `parent_id` as the 13th column (index 12). Update the SELECT to:

  ```python
  SELECT
      id,
      author_user_id,
      author_name,
      author_avatar,
      type,
      timestamp_sec,
      chord_index,
      text,
      toast_duration_sec,
      resolved,
      created_at,
      updated_at,
      parent_id
  FROM notes
  WHERE song_id = ?
  ORDER BY created_at ASC, id ASC
  ```

  Add `"parent_id": row[12]` to the returned dict (after `"updated_at": row[11]`):

  ```python
  "parent_id": row[12],
  ```

- [ ] **Step 7: Add cascade delete to `delete_note` endpoint**

  Find `async def delete_note` (line ~2321). Before the existing `DELETE FROM notes WHERE id = ?` call, add:

  ```python
  await execute("DELETE FROM notes WHERE parent_id = ?", [note_id])
  ```

  Full updated function body:

  ```python
  @app.delete("/api/notes/{note_id}")
  async def delete_note(note_id: int, request: Request):
      note_rs = await execute("SELECT song_id FROM notes WHERE id = ?", [note_id])
      if note_rs.rows:
          user = await _get_request_user(request)
          await _require_song_project_membership(int(note_rs.rows[0][0]), int(user["id"]))
      await execute("DELETE FROM notes WHERE parent_id = ?", [note_id])
      await execute("DELETE FROM notes WHERE id = ?", [note_id])
  ```

- [ ] **Step 8: Run all new tests — confirm they pass**

  ```bash
  cd /Users/wojciechgula/Projects/DeChord/backend
  uv run pytest tests/test_api.py::test_general_note_no_timestamp_required tests/test_api.py::test_general_note_with_parent_id tests/test_api.py::test_reply_to_reply_rejected tests/test_api.py::test_time_note_still_requires_timestamp tests/test_api.py::test_delete_note_cascades_replies -v
  ```

  Expected: all PASS.

- [ ] **Step 9: Run full backend test suite — no regressions**

  ```bash
  cd /Users/wojciechgula/Projects/DeChord/backend
  uv run pytest tests/test_api.py -v
  ```

  Expected: all existing tests still PASS.

- [ ] **Step 10: Commit**

  ```bash
  git add backend/app/main.py backend/tests/test_api.py
  git commit -m "feat(backend): add general note type, parent_id reply threading, cascade delete

  Plan: docs/plans/2026-03-14-comment-threading.md task 2
  Tool: opencode | Model: gpt-5.1-codex-max"
  ```

---

## Chunk 2: Frontend Types, API, and Mock Data

### Task 3: Extend `SongNote` TypeScript type

**Files:**
- Modify: `frontend/src/redesign/lib/types.ts`
- Modify: `frontend/src/lib/types.ts`

- [ ] **Step 1: Update `redesign/lib/types.ts`**

  Find `export interface SongNote` (line ~45). Add `parentId` and extend `type`:

  ```ts
  export interface SongNote {
    id: number;
    type: "time" | "chord" | "general";  // "general" added
    timestampSec: number | null;
    chordIndex: number | null;
    text: string;
    toastDurationSec: number | null;
    authorName: string | null;
    authorAvatar: string | null;
    resolved: boolean;
    parentId: number | null;              // new
    createdAt: string;
    updatedAt: string;
  }
  ```

- [ ] **Step 2: Apply the equivalent change to `lib/types.ts`**

  Find `export interface SongNote` (line ~71). Note that this file uses **snake_case** field names (`timestamp_sec`, `chord_index`, `author_name`, etc.) — unlike `redesign/lib/types.ts` which uses camelCase.

  Add `parent_id` (snake_case) and extend `type`:

  ```ts
  export interface SongNote {
    id: number;
    type: "time" | "chord" | "general";   // "general" added
    timestamp_sec: number | null;
    chord_index: number | null;
    text: string;
    toast_duration_sec: number | null;
    resolved: boolean;
    author_name: string | null;
    author_avatar: string | null;
    parent_id: number | null;              // new — snake_case to match this file's convention
    created_at: string;
    updated_at: string;
  }
  ```

- [ ] **Step 3: Commit**

  ```bash
  git add frontend/src/redesign/lib/types.ts frontend/src/lib/types.ts
  git commit -m "feat(types): add parentId and general type to SongNote

  Plan: docs/plans/2026-03-14-comment-threading.md task 3
  Tool: opencode | Model: gpt-5.1-codex-max"
  ```

---

### Task 4: Update `api.ts` — extend `createSongNote`

**Files:**
- Modify: `frontend/src/lib/api.ts` (line ~204)

- [ ] **Step 1: Update `createSongNote` signature**

  Find `export async function createSongNote` (line ~204). Replace the payload type:

  ```ts
  export async function createSongNote(
    songId: number,
    payload: {
      type: "time" | "chord" | "general";
      text: string;
      timestamp_sec?: number | null;
      chord_index?: number | null;
      toast_duration_sec?: number | null;
      parent_id?: number | null;
    },
  ): Promise<SongNote> {
    const res = await fetchWithIdentity(`${BASE}/api/songs/${songId}/notes`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error("Failed to create note");
    return res.json();
  }
  ```

- [ ] **Step 2: Commit**

  ```bash
  git add frontend/src/lib/api.ts
  git commit -m "feat(api): extend createSongNote with general type and parent_id

  Plan: docs/plans/2026-03-14-comment-threading.md task 4
  Tool: opencode | Model: gpt-5.1-codex-max"
  ```

---

### Task 5: Update `mockData.ts` note factory

**Files:**
- Modify: `frontend/src/redesign/lib/mockData.ts` (line ~43)

- [ ] **Step 1: Update the `note()` factory function**

  Find `function note(` (line ~43). Add `parentId` parameter with a default:

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
    parentId: number | null = null,
  ): SongNote {
    return {
      id,
      type,
      timestampSec: ts,
      chordIndex: ci,
      text,
      toastDurationSec: null,
      authorName: author,
      authorAvatar: avatar,
      resolved,
      parentId,
      createdAt: "2026-03-01T10:00:00Z",
      updatedAt: "2026-03-01T10:00:00Z",
    };
  }
  ```

  All existing `note(...)` call sites (lines ~60–64) are unaffected because `parentId` defaults to `null`.

- [ ] **Step 2: Run TypeScript check**

  ```bash
  cd /Users/wojciechgula/Projects/DeChord/frontend
  bun run tsc --noEmit
  ```

  Expected: no errors.

- [ ] **Step 3: Commit**

  ```bash
  git add frontend/src/redesign/lib/mockData.ts
  git commit -m "feat(mockData): add parentId to note factory

  Plan: docs/plans/2026-03-14-comment-threading.md task 5
  Tool: opencode | Model: gpt-5.1-codex-max"
  ```

---

## Chunk 3: SongDetailPage UI + App.tsx Wiring

### Task 6: Write failing frontend tests

**Files:**
- Modify: `frontend/src/redesign/pages/__tests__/SongDetailPage.test.tsx`

Before changing any UI code, write the tests that describe the new behavior. They will fail until the UI is updated.

- [ ] **Step 1: Remove timestamp-related test assertions**

  Open `frontend/src/redesign/pages/__tests__/SongDetailPage.test.tsx`.

  Search for any test that asserts the presence of "Timestamp", "Time Note", "Chord Note", or `timestampDraft`. Remove those assertions or the whole test block if it exists exclusively for that purpose.

- [ ] **Step 2: Add `SongNote` to the test file's import**

  At the top of the test file, find:

  ```ts
  import type { Band, Project, Song, User } from "../../lib/types";
  ```

  Replace with:

  ```ts
  import type { Band, Project, Song, SongNote, User } from "../../lib/types";
  ```

- [ ] **Step 3: Add new comment form tests**

  Add this describe block to the file (place after the existing download test):

  ```ts
  describe("comment form — simplified (no timestamp)", () => {
    it("does not render timestamp input or note type radios", () => {
      render(
        <SongDetailPage
          user={user} band={band} project={project} song={song}
          onOpenPlayer={() => {}} onBack={() => {}}
        />,
      );
      expect(screen.queryByLabelText("Timestamp")).toBeNull();
      expect(screen.queryByLabelText("Time Note")).toBeNull();
      expect(screen.queryByLabelText("Chord Note")).toBeNull();
    });

    it("submits a general note with just the text", async () => {
      const onCreateNote = vi.fn().mockResolvedValue(undefined);
      render(
        <SongDetailPage
          user={user} band={band} project={project} song={song}
          onOpenPlayer={() => {}} onBack={() => {}}
          onCreateNote={onCreateNote}
        />,
      );
      fireEvent.change(screen.getByLabelText("Note Text"), {
        target: { value: "Great groove" },
      });
      fireEvent.click(screen.getByText("Add Comment"));
      await waitFor(() => {
        expect(onCreateNote).toHaveBeenCalledWith({ type: "general", text: "Great groove" });
      });
    });
  });
  ```

- [ ] **Step 3: Add threading UI tests**

  Add a song fixture with existing notes (including a reply):

  ```ts
  const noteParent: SongNote = {
    id: 10, type: "general", timestampSec: null, chordIndex: null,
    text: "Top-level comment", toastDurationSec: null,
    authorName: "Mike R.", authorAvatar: "MR", resolved: false,
    parentId: null, createdAt: "2026-03-01T10:00:00Z", updatedAt: "2026-03-01T10:00:00Z",
  };
  const noteReply: SongNote = {
    id: 11, type: "general", timestampSec: null, chordIndex: null,
    text: "Reply to Mike", toastDurationSec: null,
    authorName: "Jake T.", authorAvatar: "JT", resolved: false,
    parentId: 10, createdAt: "2026-03-01T11:00:00Z", updatedAt: "2026-03-01T11:00:00Z",
  };
  const songWithNotes: Song = { ...song, notes: [noteParent, noteReply] };
  ```

  Then add:

  ```ts
  describe("comment threading", () => {
    it("renders top-level comments", () => {
      render(
        <SongDetailPage
          user={user} band={band} project={project} song={songWithNotes}
          onOpenPlayer={() => {}} onBack={() => {}}
        />,
      );
      expect(screen.getByText("Top-level comment")).toBeInTheDocument();
    });

    it("renders replies indented under their parent", () => {
      render(
        <SongDetailPage
          user={user} band={band} project={project} song={songWithNotes}
          onOpenPlayer={() => {}} onBack={() => {}}
        />,
      );
      expect(screen.getByText("Reply to Mike")).toBeInTheDocument();
    });

    it("shows Reply button on top-level comments", () => {
      render(
        <SongDetailPage
          user={user} band={band} project={project} song={songWithNotes}
          onOpenPlayer={() => {}} onBack={() => {}}
        />,
      );
      expect(screen.getAllByText("Reply").length).toBeGreaterThan(0);
    });

    it("opens inline reply form on Reply click", () => {
      render(
        <SongDetailPage
          user={user} band={band} project={project} song={songWithNotes}
          onOpenPlayer={() => {}} onBack={() => {}}
        />,
      );
      fireEvent.click(screen.getAllByText("Reply")[0]);
      expect(screen.getByLabelText("Reply Text")).toBeInTheDocument();
    });

    it("calls onCreateReply with parentId and text", async () => {
      const onCreateReply = vi.fn().mockResolvedValue(undefined);
      render(
        <SongDetailPage
          user={user} band={band} project={project} song={songWithNotes}
          onOpenPlayer={() => {}} onBack={() => {}}
          onCreateReply={onCreateReply}
        />,
      );
      fireEvent.click(screen.getAllByText("Reply")[0]);
      fireEvent.change(screen.getByLabelText("Reply Text"), {
        target: { value: "My reply" },
      });
      fireEvent.click(screen.getByText("Post Reply"));
      await waitFor(() => {
        expect(onCreateReply).toHaveBeenCalledWith(10, "My reply");
      });
    });

    it("replies do not show Resolve button", () => {
      render(
        <SongDetailPage
          user={user} band={band} project={project} song={songWithNotes}
          onOpenPlayer={() => {}} onBack={() => {}}
        />,
      );
      // There should be exactly one Resolve button — for the top-level note only
      expect(screen.getAllByText("Resolve").length).toBe(1);
    });
  });
  ```

- [ ] **Step 4: Run tests — confirm they fail**

  ```bash
  cd /Users/wojciechgula/Projects/DeChord/frontend
  bun run vitest run src/redesign/pages/__tests__/SongDetailPage.test.tsx
  ```

  Expected: new tests FAIL (old tests still pass).

---

### Task 7: Update `SongDetailPage.tsx`

**Files:**
- Modify: `frontend/src/redesign/pages/SongDetailPage.tsx`

- [x] **Step 1: Update `SongDetailPageProps` interface**

  At the top of the file, find `interface SongDetailPageProps`. Change the `onCreateNote` payload type and add `onCreateReply`:

  ```ts
  onCreateNote?: (payload: { type: "general"; text: string }) => Promise<void> | void;
  onCreateReply?: (parentId: number, text: string) => Promise<void> | void;
  ```

  Keep all other props (`onEditNote`, `onResolveNote`, `onDeleteNote`, etc.) unchanged.

- [x] **Step 2: Remove timestamp-related state**

  In the component body, remove these lines:

  ```ts
  const [noteType, setNoteType] = useState<"time" | "chord">("time");
  const [timestampDraft, setTimestampDraft] = useState("0:00");
  ```

  Also remove the `parseTimestampDraft` helper function entirely (lines ~74–86).

  Also remove the `hasChordTarget` constant (only used by the old form).

- [x] **Step 3: Add reply state**

  After the existing state declarations, add:

  ```ts
  const [replyingToId, setReplyingToId] = useState<number | null>(null);
  const [replyText, setReplyText] = useState("");
  ```

- [x] **Step 4: Simplify the comment creation form**

  Find the "Add note" form inside the Comments column (around line 418). Replace the entire form contents with the simplified version:

  ```tsx
  <div className="mb-4 border p-4" style={{ borderRadius: "3px", borderColor: "rgba(192, 192, 192, 0.05)", background: "rgba(255, 255, 255, 0.02)" }}>
    <h3 className="text-sm font-semibold" style={{ color: "#e2e2f0" }}>Add comment</h3>
    <div className="mt-3 grid gap-3">
      <label className="grid gap-1 text-sm" style={{ color: "#e2e2f0" }}>
        <span>Note Text</span>
        <textarea
          aria-label="Note Text"
          value={noteText}
          onChange={(event) => setNoteText(event.target.value)}
          rows={3}
          className="border px-3 py-2"
          style={{ borderRadius: "3px", borderColor: "rgba(192, 192, 192, 0.12)", background: "rgba(10, 14, 39, 0.7)", color: "#e2e2f0" }}
        />
      </label>
    </div>
    {actionError && <p className="mt-3 text-sm" style={{ color: "#ef4444" }}>{actionError}</p>}
    {actionSuccess && <p className="mt-3 text-sm" style={{ color: "#14b8a6" }}>{actionSuccess}</p>}
    <div className="mt-4 flex gap-3">
      <button
        onClick={() => {
          const trimmedText = noteText.trim();
          void runAction(async () => {
            if (!trimmedText) throw new Error("Enter comment text");
            await onCreateNote?.({ type: "general", text: trimmedText });
            setNoteText("");
          }, "Comment added.");
        }}
        disabled={isSubmitting}
        className="border px-4 py-2 text-sm font-medium transition-all disabled:opacity-60"
        style={{ borderRadius: "3px", borderColor: "rgba(20, 184, 166, 0.35)", color: "#14b8a6" }}
      >
        Add Comment
      </button>
    </div>
  </div>
  ```

- [x] **Step 5: Restructure the comment list with threading**

  Replace the current open-comments rendering block (starting at `{openComments.length === 0 && ...}`, around line 501) with the threaded version:

- [x] **Step 6: Run the frontend tests**

  ```bash
  cd /Users/wojciechgula/Projects/DeChord/frontend
  bun run vitest run src/redesign/pages/__tests__/SongDetailPage.test.tsx
  ```

  Expected: all tests PASS (including the new ones from Task 6).

- [x] **Step 7: Run TypeScript check**

  ```bash
  cd /Users/wojciechgula/Projects/DeChord/frontend
  bun run tsc --noEmit
  ```

  Expected: no errors.

- [x] **Step 8: Commit**

  Commit: https://github.com/anomalyco/DeChord/commit/1591b5d492851c37841240111c87335aaccd5378

  > **Note on `openComments`:** This is already computed at line ~59 as `song.notes.filter((n) => !n.resolved)`. The threading code filters that further for `parentId === null` (top-level). Replies are fetched directly from `song.notes` because resolved replies should stay hidden with their parent — this is intentional.

- [ ] **Step 6: Run the frontend tests**

  ```bash
  cd /Users/wojciechgula/Projects/DeChord/frontend
  bun run vitest run src/redesign/pages/__tests__/SongDetailPage.test.tsx
  ```

  Expected: all tests PASS (including the new ones from Task 6).

- [ ] **Step 7: Run TypeScript check**

  ```bash
  cd /Users/wojciechgula/Projects/DeChord/frontend
  bun run tsc --noEmit
  ```

  Expected: no errors.

- [ ] **Step 8: Commit**

  ```bash
  git add frontend/src/redesign/pages/SongDetailPage.tsx frontend/src/redesign/pages/__tests__/SongDetailPage.test.tsx
  git commit -m "feat(ui): simplify comment form and add reply threading to SongDetailPage

  Plan: docs/plans/2026-03-14-comment-threading.md task 7
  Tool: opencode | Model: gpt-5.1-codex-max"
  ```

---

### Task 8: Wire up `onCreateReply` in `App.tsx`

**Files:**
- Modify: `App.tsx` (lines ~987 and ~1034)

- [ ] **Step 1: Update the first `SongDetailPage` usage (~line 987)**

  Find the `onCreateNote` prop in the first `<SongDetailPage` usage. Replace the entire prop with:

  ```tsx
  onCreateNote={async ({ text }: { type: "general"; text: string }) => {
    const songId = Number(route.song.id);
    if (Number.isNaN(songId)) return;
    await createSongNote(songId, { type: "general", text });
    await refreshSongDetailRoute();
  }}
  onCreateReply={async (parentId: number, text: string) => {
    const songId = Number(route.song.id);
    if (Number.isNaN(songId)) return;
    await createSongNote(songId, { type: "general", text, parent_id: parentId });
    await refreshSongDetailRoute();
  }}
  ```

  > **`refreshSongDetailRoute`** is already called by `onGenerateBassTab`, `onUploadStem`, and `onEditNote` in this same block — it is the standard refresh for this route. `createSongNote` is already imported at the top of `App.tsx`.

- [ ] **Step 2: Apply the same update to the second usage (~line 1034)**

  Find the second `<SongDetailPage` usage and apply identical `onCreateNote` and `onCreateReply` prop updates.

- [ ] **Step 3: Run TypeScript check**

  ```bash
  cd /Users/wojciechgula/Projects/DeChord/frontend
  bun run tsc --noEmit
  ```

  Expected: no errors.

- [ ] **Step 4: Run all frontend tests**

  ```bash
  cd /Users/wojciechgula/Projects/DeChord/frontend
  bun run vitest run
  ```

  Expected: all tests PASS.

- [ ] **Step 5: Commit**

  ```bash
  git add frontend/src/App.tsx
  git commit -m "feat(app): wire onCreateNote and onCreateReply for SongDetailPage

  Plan: docs/plans/2026-03-14-comment-threading.md task 8
  Tool: opencode | Model: gpt-5.1-codex-max"
  ```

---

## Final Verification

- [ ] **Run `make reset` to start from a clean runtime state**

  ```bash
  cd /Users/wojciechgula/Projects/DeChord
  make reset
  ```

- [ ] **Run full backend test suite**

  ```bash
  cd /Users/wojciechgula/Projects/DeChord/backend
  uv run pytest tests/test_api.py -v
  ```

  Expected: all PASS, no regressions.

- [ ] **Run full frontend test suite**

  ```bash
  cd /Users/wojciechgula/Projects/DeChord/frontend
  bun run vitest run
  ```

  Expected: all PASS, no regressions.

- [ ] **Run TypeScript check**

  ```bash
  cd /Users/wojciechgula/Projects/DeChord/frontend
  bun run tsc --noEmit
  ```

  Expected: no errors.

- [ ] **Verify Player tests are untouched**

  ```bash
  cd /Users/wojciechgula/Projects/DeChord/frontend
  bun run vitest run src/redesign/pages/__tests__/PlayerPage.test.tsx
  ```

  Expected: all PASS.

- [ ] **Update plan: mark all tasks complete**

  Update this file (`docs/plans/2026-03-14-comment-threading.md`) — mark all `[ ]` as `[x]`.
