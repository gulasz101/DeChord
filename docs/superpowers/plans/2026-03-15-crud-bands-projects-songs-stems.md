# CRUD — Bands, Projects, Songs, Stems Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add rename + soft-archive (with cascade) to bands, projects, songs, and stems, with "Show archived" toggle per list.

**Architecture:** All backend lives in `backend/app/main.py` (single-file FastAPI). Migrations use additive `_ensure_column`. Four new PATCH endpoints (bands, projects, songs extend existing stems PATCH). Frontend adds two shared components (`ThreeDotMenu`, `RenameModal`) wired into four existing list views.

**Tech Stack:** FastAPI, Python 3.13+, LibSQL (`execute()` async helper), React 19, TypeScript, Tailwind v4, Vitest, pytest, httpx.

---

## Chunk 1: Backend — Migrations, PATCH Routes, List Filtering

### Task 1: DB Migrations

**Files:**
- Modify: `backend/app/main.py` (find `_run_schema_migrations`)

- [ ] **Step 1: Read `_run_schema_migrations` in `backend/app/main.py`**

  Search for `async def _run_schema_migrations` and find the exact location. It calls `_ensure_column(...)` repeatedly. You will add 4 new calls at the end of the function.

- [ ] **Step 2: Add the 4 new `_ensure_column` calls**

  Add these lines at the end of `_run_schema_migrations`, before the closing of the function:

  ```python
  await _ensure_column("bands",      "archived_at", "archived_at TEXT")
  await _ensure_column("projects",   "archived_at", "archived_at TEXT")
  await _ensure_column("songs",      "archived_at", "archived_at TEXT")
  await _ensure_column("song_stems", "archived_at", "archived_at TEXT")
  ```

- [ ] **Step 3: Start the backend and verify columns exist**

  ```bash
  cd backend && uv run python -c "
  import asyncio
  from app.main import init_db, execute
  async def check():
      await init_db()
      for table in ['bands', 'projects', 'songs', 'song_stems']:
          rs = await execute(f'PRAGMA table_info({table})')
          cols = [str(r[1]) for r in rs.rows]
          assert 'archived_at' in cols, f'MISSING archived_at in {table}'
          print(f'{table}: OK')
  asyncio.run(check())
  "
  ```
  Expected output: `bands: OK`, `projects: OK`, `songs: OK`, `song_stems: OK`

- [ ] **Step 4: Commit**

  ```bash
  git add backend/app/main.py
  git commit -m "feat(db): add archived_at column to bands, projects, songs, song_stems [plan: docs/superpowers/plans/2026-03-15-crud-bands-projects-songs-stems.md, Task 1, cli: claude-code, model: claude-sonnet-4-6]"
  ```

---

### Task 2: Write Failing Backend Tests — Band PATCH + List Filtering

**Files:**
- Read: `backend/tests/test_db_bootstrap.py` (understand existing test setup + fixture pattern)
- Create: `backend/tests/test_crud_archive.py`

- [ ] **Step 1: Read the existing test file to understand setup**

  ```bash
  cat backend/tests/test_db_bootstrap.py
  ```

  Note: how the app is imported, how the test database is initialised, whether `TestClient` or `httpx.AsyncClient` is used. Follow the same pattern exactly.

- [ ] **Step 2: Create `backend/tests/test_crud_archive.py` with band tests**

  ```python
  """Tests for rename + archive CRUD on bands, projects, songs, stems."""
  import pytest
  from fastapi.testclient import TestClient

  # Import following the same pattern as test_db_bootstrap.py
  # If it uses a different import, match it.
  from app.main import app, init_db, execute

  @pytest.fixture(autouse=True)
  def setup_db(tmp_path, monkeypatch):
      """Each test gets a fresh in-memory or temp database."""
      import os
      db_file = tmp_path / "test.db"
      monkeypatch.setenv("DECHORD_DB_URL", f"file:{db_file}")
      # Reset the LibSQL client so it picks up the new URL
      import app.main as main_module
      main_module._client = None
      import asyncio
      asyncio.get_event_loop().run_until_complete(init_db())
      yield
      main_module._client = None


  def _client_with_user(user_id: int = 1) -> TestClient:
      client = TestClient(app, raise_server_exceptions=True)
      client.headers["X-DeChord-User-Id"] = str(user_id)
      return client


  def _get_default_band_id(client: TestClient) -> int:
      res = client.get("/api/bands")
      assert res.status_code == 200
      return res.json()["bands"][0]["id"]


  def _get_default_project_id(client: TestClient, band_id: int) -> int:
      res = client.get(f"/api/bands/{band_id}/projects")
      assert res.status_code == 200
      return res.json()["projects"][0]["id"]


  # ── Band rename ──────────────────────────────────────────────────────────────

  def test_patch_band_rename():
      client = _client_with_user()
      band_id = _get_default_band_id(client)
      res = client.patch(f"/api/bands/{band_id}", json={"name": "New Band Name"})
      assert res.status_code == 200
      assert res.json()["name"] == "New Band Name"


  def test_patch_band_rename_blank_rejected():
      client = _client_with_user()
      band_id = _get_default_band_id(client)
      res = client.patch(f"/api/bands/{band_id}", json={"name": ""})
      assert res.status_code == 422


  # ── Band archive ─────────────────────────────────────────────────────────────

  def test_patch_band_archive_sets_archived_at():
      client = _client_with_user()
      band_id = _get_default_band_id(client)
      res = client.patch(f"/api/bands/{band_id}", json={"archived": True})
      assert res.status_code == 200
      assert res.json()["archived_at"] is not None


  def test_patch_band_archive_cascades_to_projects_songs_stems():
      client = _client_with_user()
      band_id = _get_default_band_id(client)
      project_id = _get_default_project_id(client, band_id)

      client.patch(f"/api/bands/{band_id}", json={"archived": True})

      # Project should be archived
      rs = client.get(f"/api/bands/{band_id}/projects?include_archived=true")
      assert rs.status_code == 200
      projects = rs.json()["projects"]
      archived_project = next(p for p in projects if p["id"] == project_id)
      assert archived_project["archived_at"] is not None


  def test_patch_band_unarchive_clears_all_descendants():
      client = _client_with_user()
      band_id = _get_default_band_id(client)
      client.patch(f"/api/bands/{band_id}", json={"archived": True})
      client.patch(f"/api/bands/{band_id}", json={"archived": False})

      res = client.patch(f"/api/bands/{band_id}", json={"archived": False})
      assert res.status_code == 200
      assert res.json()["archived_at"] is None

      # Projects should be unarchived
      rs = client.get(f"/api/bands/{band_id}/projects")
      assert rs.status_code == 200
      assert len(rs.json()["projects"]) > 0


  def test_patch_band_archive_idempotent():
      client = _client_with_user()
      band_id = _get_default_band_id(client)
      client.patch(f"/api/bands/{band_id}", json={"archived": True})
      res = client.patch(f"/api/bands/{band_id}", json={"archived": True})
      assert res.status_code == 200
      assert res.json()["archived_at"] is not None


  # ── Band list filtering ───────────────────────────────────────────────────────

  def test_list_bands_excludes_archived_by_default():
      client = _client_with_user()
      band_id = _get_default_band_id(client)
      client.patch(f"/api/bands/{band_id}", json={"archived": True})
      res = client.get("/api/bands")
      assert res.status_code == 200
      ids = [b["id"] for b in res.json()["bands"]]
      assert band_id not in ids


  def test_list_bands_includes_archived_with_param():
      client = _client_with_user()
      band_id = _get_default_band_id(client)
      client.patch(f"/api/bands/{band_id}", json={"archived": True})
      res = client.get("/api/bands?include_archived=true")
      assert res.status_code == 200
      ids = [b["id"] for b in res.json()["bands"]]
      assert band_id in ids
  ```

- [ ] **Step 3: Run tests to confirm they fail (endpoint not yet implemented)**

  ```bash
  cd backend && uv run pytest tests/test_crud_archive.py -v 2>&1 | head -40
  ```
  Expected: multiple FAILED with `404` or `422` or `AttributeError`.

- [ ] **Step 4: Commit the test file**

  ```bash
  git add backend/tests/test_crud_archive.py
  git commit -m "test(crud): add failing tests for band rename/archive/list-filter [plan: docs/superpowers/plans/2026-03-15-crud-bands-projects-songs-stems.md, Task 2, cli: claude-code, model: claude-sonnet-4-6]"
  ```

---

### Task 3: Implement `PATCH /api/bands/{id}` + Update `list_bands`

**Files:**
- Modify: `backend/app/main.py`

- [ ] **Step 1: Read the existing `list_bands` function in `main.py`**

  Search for `@app.get("/api/bands")`. Read the full SQL query. You will add a `WHERE b.archived_at IS NULL` clause and an `include_archived` query param.

- [ ] **Step 2: Read `_serialize_band` (or equivalent serialiser)**

  Search for where the bands list response is built (`{"id": ..., "name": ...}`). The serialiser needs `archived_at` added.

- [ ] **Step 3: Add `BandUpdateRequest` Pydantic model**

  Find the block of Pydantic models near the top of `main.py` (search for `class StemUpdateRequest`) and add alongside it:

  ```python
  from pydantic import Field  # add to existing pydantic import if not present

  class BandUpdateRequest(BaseModel):
      name: str | None = Field(None, min_length=1, max_length=200)
      archived: bool | None = None
  ```

- [ ] **Step 4: Update `list_bands` to support `include_archived`**

  Change the function signature and SQL:

  ```python
  @app.get("/api/bands")
  async def list_bands(request: Request, include_archived: bool = False):
      user = await _get_request_user(request)
      archived_filter = "" if include_archived else "AND b.archived_at IS NULL"
      rows = await execute(
          f"""
          SELECT
              b.id,
              b.name,
              b.owner_user_id,
              b.created_at,
              b.archived_at,
              (
                  SELECT COUNT(*)
                  FROM projects p
                  WHERE p.band_id = b.id
              ) AS project_count
          FROM bands b
          JOIN band_memberships bm ON bm.band_id = b.id
          WHERE bm.user_id = ? {archived_filter}
          ORDER BY b.created_at DESC, b.id DESC
          """,
          [int(user["id"])],
      )
      bands = [
          {
              "id": int(row[0]),
              "name": row[1],
              "owner_user_id": int(row[2]),
              "created_at": row[3],
              "archived_at": row[4],
              "project_count": int(row[5]),
          }
          for row in rows.rows
      ]
      return {"bands": bands}
  ```

  > **Note:** If the existing SQL has a different shape (extra columns, different WHERE), adapt accordingly — but always add `b.archived_at` to the SELECT and the `archived_filter` to the WHERE.

- [ ] **Step 5: Add `PATCH /api/bands/{band_id}` endpoint**

  Add after the `list_bands` route (or near the other band routes):

  ```python
  @app.patch("/api/bands/{band_id}")
  async def patch_band(band_id: int, body: BandUpdateRequest, request: Request):
      user = await _get_request_user(request)
      await _require_band_membership(band_id, int(user["id"]))

      # Verify band exists
      rs = await execute(
          "SELECT id, name, archived_at FROM bands WHERE id = ?", [band_id]
      )
      if not rs.rows:
          raise HTTPException(status_code=404, detail="Band not found.")

      updates: dict = {}
      if body.name is not None:
          updates["name"] = body.name

      if body.archived is not None:
          now_sql = "CURRENT_TIMESTAMP"
          if body.archived:
              # Archive band + cascade to projects, songs, stems
              await execute(
                  "UPDATE bands SET archived_at = CURRENT_TIMESTAMP WHERE id = ?",
                  [band_id],
              )
              await execute(
                  "UPDATE projects SET archived_at = CURRENT_TIMESTAMP WHERE band_id = ?",
                  [band_id],
              )
              await execute(
                  """UPDATE songs SET archived_at = CURRENT_TIMESTAMP
                     WHERE project_id IN (SELECT id FROM projects WHERE band_id = ?)""",
                  [band_id],
              )
              await execute(
                  """UPDATE song_stems SET archived_at = CURRENT_TIMESTAMP
                     WHERE song_id IN (
                         SELECT s.id FROM songs s
                         JOIN projects p ON s.project_id = p.id
                         WHERE p.band_id = ?
                     )""",
                  [band_id],
              )
          else:
              # Unarchive band + cascade
              await execute(
                  "UPDATE bands SET archived_at = NULL WHERE id = ?", [band_id]
              )
              await execute(
                  "UPDATE projects SET archived_at = NULL WHERE band_id = ?",
                  [band_id],
              )
              await execute(
                  """UPDATE songs SET archived_at = NULL
                     WHERE project_id IN (SELECT id FROM projects WHERE band_id = ?)""",
                  [band_id],
              )
              await execute(
                  """UPDATE song_stems SET archived_at = NULL
                     WHERE song_id IN (
                         SELECT s.id FROM songs s
                         JOIN projects p ON s.project_id = p.id
                         WHERE p.band_id = ?
                     )""",
                  [band_id],
              )

      # Apply name update if any
      if updates:
          set_clause = ", ".join(f"{k} = ?" for k in updates)
          await execute(
              f"UPDATE bands SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
              list(updates.values()) + [band_id],
          )

      # Return updated band
      rs2 = await execute(
          "SELECT id, name, owner_user_id, created_at, archived_at FROM bands WHERE id = ?",
          [band_id],
      )
      row = rs2.rows[0]
      return {
          "id": int(row[0]),
          "name": row[1],
          "owner_user_id": int(row[2]),
          "created_at": row[3],
          "archived_at": row[4],
      }
  ```

- [ ] **Step 6: Run band tests — expect PASS**

  ```bash
  cd backend && uv run pytest tests/test_crud_archive.py -k "band" -v
  ```
  Expected: all band tests PASS.

- [ ] **Step 7: Commit**

  ```bash
  git add backend/app/main.py
  git commit -m "feat(api): add PATCH /api/bands/{id} — rename and archive/unarchive with cascade [plan: docs/superpowers/plans/2026-03-15-crud-bands-projects-songs-stems.md, Task 3, cli: claude-code, model: claude-sonnet-4-6]"
  ```

---

### Task 4: Write Failing Tests — Project + Song PATCH

**Files:**
- Modify: `backend/tests/test_crud_archive.py`

- [ ] **Step 1: Append project tests to `test_crud_archive.py`**

  Add these tests to the existing file. First read `GET /api/bands/{band_id}/projects` response shape (check what fields are returned for a project) to verify your assertions.

  ```python
  # ── Project rename + archive ──────────────────────────────────────────────────

  def test_patch_project_rename():
      client = _client_with_user()
      band_id = _get_default_band_id(client)
      project_id = _get_default_project_id(client, band_id)
      res = client.patch(f"/api/projects/{project_id}", json={"name": "Renamed Project"})
      assert res.status_code == 200
      assert res.json()["name"] == "Renamed Project"


  def test_patch_project_archive_cascades_to_songs():
      client = _client_with_user()
      band_id = _get_default_band_id(client)
      project_id = _get_default_project_id(client, band_id)

      res = client.patch(f"/api/projects/{project_id}", json={"archived": True})
      assert res.status_code == 200
      assert res.json()["archived_at"] is not None

      # Default list should exclude it
      rs = client.get(f"/api/bands/{band_id}/projects")
      ids = [p["id"] for p in rs.json()["projects"]]
      assert project_id not in ids


  def test_patch_project_unarchive():
      client = _client_with_user()
      band_id = _get_default_band_id(client)
      project_id = _get_default_project_id(client, band_id)

      client.patch(f"/api/projects/{project_id}", json={"archived": True})
      res = client.patch(f"/api/projects/{project_id}", json={"archived": False})
      assert res.status_code == 200
      assert res.json()["archived_at"] is None

      # Should be visible in default list again
      rs = client.get(f"/api/bands/{band_id}/projects")
      ids = [p["id"] for p in rs.json()["projects"]]
      assert project_id in ids


  def test_list_projects_include_archived():
      client = _client_with_user()
      band_id = _get_default_band_id(client)
      project_id = _get_default_project_id(client, band_id)
      client.patch(f"/api/projects/{project_id}", json={"archived": True})

      res = client.get(f"/api/bands/{band_id}/projects?include_archived=true")
      ids = [p["id"] for p in res.json()["projects"]]
      assert project_id in ids
  ```

- [ ] **Step 2: Append song tests to `test_crud_archive.py`**

  First read `GET /api/projects/{id}/songs` (or equivalent in `main.py`) to know the exact URL. The URL may be `/api/projects/{project_id}/songs`.

  ```python
  # ── Song rename + archive ─────────────────────────────────────────────────────

  def _get_project_songs_url(project_id: int) -> str:
      # Read main.py to confirm: search for 'list_project_songs' or songs by project
      # Most likely: /api/projects/{project_id}/songs
      return f"/api/projects/{project_id}/songs"


  def test_patch_song_rename():
      """Upload a song via direct DB insert, then rename it."""
      import asyncio
      async def insert_song(project_id):
          rs = await execute(
              """INSERT INTO songs (project_id, title, original_filename, status)
                 VALUES (?, 'Test Song', 'test.mp3', 'complete')
                 RETURNING id""",
              [project_id],
          )
          return int(rs.rows[0][0])

      client = _client_with_user()
      band_id = _get_default_band_id(client)
      project_id = _get_default_project_id(client, band_id)
      song_id = asyncio.get_event_loop().run_until_complete(insert_song(project_id))

      res = client.patch(f"/api/songs/{song_id}", json={"title": "Renamed Song"})
      assert res.status_code == 200
      assert res.json()["title"] == "Renamed Song"
      # original_filename must be unchanged
      assert res.json()["original_filename"] == "test.mp3"


  def test_patch_song_archive():
      import asyncio
      async def insert_song(project_id):
          rs = await execute(
              """INSERT INTO songs (project_id, title, original_filename, status)
                 VALUES (?, 'Song To Archive', 'archive_me.mp3', 'complete')
                 RETURNING id""",
              [project_id],
          )
          return int(rs.rows[0][0])

      client = _client_with_user()
      band_id = _get_default_band_id(client)
      project_id = _get_default_project_id(client, band_id)
      song_id = asyncio.get_event_loop().run_until_complete(insert_song(project_id))

      res = client.patch(f"/api/songs/{song_id}", json={"archived": True})
      assert res.status_code == 200
      assert res.json()["archived_at"] is not None

      # Should be hidden from default list
      songs_res = client.get(_get_project_songs_url(project_id))
      ids = [s["id"] for s in songs_res.json().get("songs", [])]
      assert song_id not in ids


  def test_list_songs_include_archived():
      import asyncio
      async def insert_song(project_id):
          rs = await execute(
              """INSERT INTO songs (project_id, title, original_filename, status)
                 VALUES (?, 'Hidden Song', 'hidden.mp3', 'complete')
                 RETURNING id""",
              [project_id],
          )
          return int(rs.rows[0][0])

      client = _client_with_user()
      band_id = _get_default_band_id(client)
      project_id = _get_default_project_id(client, band_id)
      song_id = asyncio.get_event_loop().run_until_complete(insert_song(project_id))
      client.patch(f"/api/songs/{song_id}", json={"archived": True})

      res = client.get(_get_project_songs_url(project_id) + "?include_archived=true")
      ids = [s["id"] for s in res.json().get("songs", [])]
      assert song_id in ids
  ```

  > **Note on songs table schema:** Read `backend/app/db_schema.sql` to confirm the `songs` table columns before using `INSERT INTO songs`. If the `status` column doesn't exist or has different constraints, adjust the INSERT accordingly.

  > **Note on asyncio in tests:** The `asyncio.get_event_loop().run_until_complete(...)` pattern used for DB helpers works in a synchronous pytest context. If the existing `test_db_bootstrap.py` uses `asyncio.run(...)` instead, switch to that pattern. Do NOT use this inside async test functions — keep helpers as sync wrappers calling `asyncio.run(...)`.

- [ ] **Step 3: Run to verify all new tests FAIL**

  ```bash
  cd backend && uv run pytest tests/test_crud_archive.py -k "project or song" -v 2>&1 | tail -20
  ```

- [ ] **Step 4: Commit**

  ```bash
  git add backend/tests/test_crud_archive.py
  git commit -m "test(crud): add failing tests for project and song rename/archive [plan: docs/superpowers/plans/2026-03-15-crud-bands-projects-songs-stems.md, Task 4, cli: claude-code, model: claude-sonnet-4-6]"
  ```

---

### Task 5: Implement `PATCH /api/projects/{id}` + `PATCH /api/songs/{id}`

**Files:**
- Modify: `backend/app/main.py`

- [ ] **Step 1: Read existing project list + song list routes in `main.py`**

  Search for `@app.get("/api/bands/{band_id}/projects")` and the song list route (likely `@app.get("/api/projects/{project_id}/songs")`). Understand the SELECT query shape and add `archived_at` to both.

- [ ] **Step 2: Add Pydantic models**

  ```python
  class ProjectUpdateRequest(BaseModel):
      name: str | None = Field(None, min_length=1, max_length=200)
      archived: bool | None = None

  class SongUpdateRequest(BaseModel):
      title: str | None = Field(None, min_length=1, max_length=200)
      archived: bool | None = None
  ```

- [ ] **Step 3: Update `list_band_projects` to support `include_archived`**

  Add `include_archived: bool = False` param and add `AND p.archived_at IS NULL` to the WHERE clause when false. Add `p.archived_at` to the SELECT and serialiser output.

- [ ] **Step 4: Update the project songs list route to support `include_archived`**

  Same pattern: add `include_archived: bool = False` param, `AND s.archived_at IS NULL` filter, `s.archived_at` in SELECT and serialiser.

- [ ] **Step 5: Add `PATCH /api/projects/{project_id}` endpoint**

  ```python
  @app.patch("/api/projects/{project_id}")
  async def patch_project(project_id: int, body: ProjectUpdateRequest, request: Request):
      user = await _get_request_user(request)

      # Verify project exists and user has access via band membership
      rs = await execute(
          "SELECT id, name, band_id, archived_at FROM projects WHERE id = ?",
          [project_id],
      )
      if not rs.rows:
          raise HTTPException(status_code=404, detail="Project not found.")
      band_id = int(rs.rows[0][2])
      await _require_band_membership(band_id, int(user["id"]))

      if body.archived is not None:
          if body.archived:
              await execute(
                  "UPDATE projects SET archived_at = CURRENT_TIMESTAMP WHERE id = ?",
                  [project_id],
              )
              await execute(
                  "UPDATE songs SET archived_at = CURRENT_TIMESTAMP WHERE project_id = ?",
                  [project_id],
              )
              await execute(
                  """UPDATE song_stems SET archived_at = CURRENT_TIMESTAMP
                     WHERE song_id IN (SELECT id FROM songs WHERE project_id = ?)""",
                  [project_id],
              )
          else:
              await execute(
                  "UPDATE projects SET archived_at = NULL WHERE id = ?", [project_id]
              )
              await execute(
                  "UPDATE songs SET archived_at = NULL WHERE project_id = ?",
                  [project_id],
              )
              await execute(
                  """UPDATE song_stems SET archived_at = NULL
                     WHERE song_id IN (SELECT id FROM songs WHERE project_id = ?)""",
                  [project_id],
              )

      if body.name is not None:
          await execute(
              "UPDATE projects SET name = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
              [body.name, project_id],
          )

      rs2 = await execute(
          "SELECT id, band_id, name, archived_at, created_at FROM projects WHERE id = ?",
          [project_id],
      )
      row = rs2.rows[0]
      return {
          "id": int(row[0]),
          "band_id": int(row[1]),
          "name": row[2],
          "archived_at": row[3],
          "created_at": row[4],
      }
  ```

- [ ] **Step 6: Add `PATCH /api/songs/{song_id}` endpoint**

  ```python
  @app.patch("/api/songs/{song_id}")
  async def patch_song(song_id: int, body: SongUpdateRequest, request: Request):
      user = await _get_request_user(request)

      rs = await execute(
          "SELECT id, title, original_filename, project_id, archived_at FROM songs WHERE id = ?",
          [song_id],
      )
      if not rs.rows:
          raise HTTPException(status_code=404, detail="Song not found.")

      # Verify user access via project → band membership
      project_id = int(rs.rows[0][3])
      proj_rs = await execute("SELECT band_id FROM projects WHERE id = ?", [project_id])
      if proj_rs.rows:
          await _require_band_membership(int(proj_rs.rows[0][0]), int(user["id"]))

      if body.archived is not None:
          if body.archived:
              await execute(
                  "UPDATE songs SET archived_at = CURRENT_TIMESTAMP WHERE id = ?",
                  [song_id],
              )
              await execute(
                  "UPDATE song_stems SET archived_at = CURRENT_TIMESTAMP WHERE song_id = ?",
                  [song_id],
              )
          else:
              await execute(
                  "UPDATE songs SET archived_at = NULL WHERE id = ?", [song_id]
              )
              await execute(
                  "UPDATE song_stems SET archived_at = NULL WHERE song_id = ?",
                  [song_id],
              )

      if body.title is not None:
          await execute(
              "UPDATE songs SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
              [body.title, song_id],
          )

      rs2 = await execute(
          "SELECT id, title, original_filename, project_id, archived_at, created_at FROM songs WHERE id = ?",
          [song_id],
      )
      row = rs2.rows[0]
      return {
          "id": int(row[0]),
          "title": row[1],
          "original_filename": row[2],
          "project_id": int(row[3]),
          "archived_at": row[4],
          "created_at": row[5],
      }
  ```

- [ ] **Step 7: Run all tests — expect PASS**

  ```bash
  cd backend && uv run pytest tests/test_crud_archive.py -v
  ```
  Expected: all tests PASS.

- [ ] **Step 8: Commit**

  ```bash
  git add backend/app/main.py
  git commit -m "feat(api): add PATCH /api/projects/{id} and PATCH /api/songs/{id} with cascade archive [plan: docs/superpowers/plans/2026-03-15-crud-bands-projects-songs-stems.md, Task 5, cli: claude-code, model: claude-sonnet-4-6]"
  ```

---

### Task 6: Extend `PATCH /api/stems/{id}` with Archive + Update Stem List

**Files:**
- Modify: `backend/app/main.py`
- Modify: `backend/tests/test_crud_archive.py`

- [ ] **Step 1: Read existing `PATCH /api/stems/{stem_id}` handler**

  Search for `@app.patch("/api/stems/{stem_id}")`. Read the full handler and `StemUpdateRequest` model.

- [ ] **Step 2: Write failing stem archive tests**

  Add to `test_crud_archive.py`:

  ```python
  # ── Stem archive ──────────────────────────────────────────────────────────────

  def test_patch_stem_archive():
      """Requires an existing song with a stem. Use the default project's first song if any,
      or insert a stem directly via DB."""
      import asyncio

      async def insert_song_and_stem(project_id):
          song_rs = await execute(
              """INSERT INTO songs (project_id, title, original_filename, status)
                 VALUES (?, 'Stem Test Song', 'stem_test.mp3', 'complete')
                 RETURNING id""",
              [project_id],
          )
          song_id = int(song_rs.rows[0][0])
          stem_rs = await execute(
              """INSERT INTO song_stems (song_id, stem_key, audio_blob, mime_type,
                 source_type, display_name, version_label)
                 VALUES (?, 'bass', X'', 'audio/wav', 'system', 'Bass', 'v1')
                 RETURNING id""",
              [song_id],
          )
          return song_id, int(stem_rs.rows[0][0])

      client = _client_with_user()
      band_id = _get_default_band_id(client)
      project_id = _get_default_project_id(client, band_id)
      _, stem_id = asyncio.get_event_loop().run_until_complete(
          insert_song_and_stem(project_id)
      )

      res = client.patch(f"/api/stems/{stem_id}", json={"archived": True})
      assert res.status_code == 200
      assert res.json()["archived_at"] is not None


  def test_patch_stem_unarchive():
      import asyncio

      async def insert_song_and_stem(project_id):
          song_rs = await execute(
              """INSERT INTO songs (project_id, title, original_filename, status)
                 VALUES (?, 'Stem Test Song 2', 'stem_test2.mp3', 'complete')
                 RETURNING id""",
              [project_id],
          )
          song_id = int(song_rs.rows[0][0])
          stem_rs = await execute(
              """INSERT INTO song_stems (song_id, stem_key, audio_blob, mime_type,
                 source_type, display_name, version_label)
                 VALUES (?, 'drums', X'', 'audio/wav', 'system', 'Drums', 'v1')
                 RETURNING id""",
              [song_id],
          )
          return song_id, int(stem_rs.rows[0][0])

      client = _client_with_user()
      band_id = _get_default_band_id(client)
      project_id = _get_default_project_id(client, band_id)
      song_id, stem_id = asyncio.get_event_loop().run_until_complete(
          insert_song_and_stem(project_id)
      )

      client.patch(f"/api/stems/{stem_id}", json={"archived": True})
      res = client.patch(f"/api/stems/{stem_id}", json={"archived": False})
      assert res.status_code == 200
      assert res.json()["archived_at"] is None


  def test_list_stems_excludes_archived_by_default():
      import asyncio

      async def insert_song_and_stem(project_id):
          song_rs = await execute(
              """INSERT INTO songs (project_id, title, original_filename, status)
                 VALUES (?, 'Stem Filter Song', 'stem_filter.mp3', 'complete')
                 RETURNING id""",
              [project_id],
          )
          song_id = int(song_rs.rows[0][0])
          stem_rs = await execute(
              """INSERT INTO song_stems (song_id, stem_key, audio_blob, mime_type,
                 source_type, display_name, version_label)
                 VALUES (?, 'vocals', X'', 'audio/wav', 'system', 'Vocals', 'v1')
                 RETURNING id""",
              [song_id],
          )
          return song_id, int(stem_rs.rows[0][0])

      client = _client_with_user()
      band_id = _get_default_band_id(client)
      project_id = _get_default_project_id(client, band_id)
      song_id, stem_id = asyncio.get_event_loop().run_until_complete(
          insert_song_and_stem(project_id)
      )
      client.patch(f"/api/stems/{stem_id}", json={"archived": True})

      res = client.get(f"/api/songs/{song_id}/stems")
      ids = [s["id"] for s in res.json().get("stems", [])]
      assert stem_id not in ids
  ```

- [ ] **Step 3: Run to confirm new stem tests FAIL**

  ```bash
  cd backend && uv run pytest tests/test_crud_archive.py -k "stem" -v 2>&1 | tail -20
  ```

- [ ] **Step 4: Add `archived` field to `StemUpdateRequest`**

  In `main.py`, find `class StemUpdateRequest(BaseModel)` and add:

  ```python
  archived: bool | None = None
  ```

- [ ] **Step 5: Update `patch_stem` handler to apply archive/unarchive**

  Inside `patch_stem`, after the existing `display_name`/`description` update block and before the return, add:

  ```python
  if body.archived is not None:
      if body.archived:
          await execute(
              "UPDATE song_stems SET archived_at = CURRENT_TIMESTAMP WHERE id = ?",
              [stem_id],
          )
      else:
          await execute(
              "UPDATE song_stems SET archived_at = NULL WHERE id = ?", [stem_id]
          )
  ```

  Also add `"archived_at": ...` to the `_serialize_song_stem` return dict (or wherever stems are serialised). Find `_serialize_song_stem` and add `"archived_at": row[13]` (adjust index to match actual column order after adding `archived_at` to the `_STEM_SELECT` query).

  Update `_STEM_SELECT` to include `archived_at`:

  ```python
  _STEM_SELECT = """
      SELECT id, stem_key, mime_type, duration, source_type, display_name, description,
             version_label, generation_id, uploaded_by_name, created_by_name, created_at,
             updated_at, archived_at
      FROM song_stems
  """
  ```

  And update `_serialize_song_stem`:
  ```python
  "archived_at": str(row[13]) if row[13] else None,
  ```

- [ ] **Step 6: Update `GET /api/songs/{song_id}/stems` to support `include_archived`**

  Find the stems list route (search `@app.get("/api/songs/{song_id}/stems")`). Add `include_archived: bool = False` param and a SQL filter on `archived_at`:

  ```python
  @app.get("/api/songs/{song_id}/stems")
  async def list_song_stems(song_id: int, include_archived: bool = False):
      archived_filter = "" if include_archived else "AND archived_at IS NULL"
      rs = await execute(
          f"{_STEM_SELECT} WHERE song_id = ? {archived_filter} ORDER BY created_at ASC",
          [song_id],
      )
      stems = [_serialize_song_stem(row) for row in rs.rows]
      return {"stems": stems}
  ```

  > Adapt to match the existing route's auth/user checks if any are present.

- [ ] **Step 7: Run all tests — expect PASS**

  ```bash
  cd backend && uv run pytest tests/test_crud_archive.py -v
  ```
  Expected: all tests PASS.

- [ ] **Step 8: Commit**

  ```bash
  git add backend/app/main.py backend/tests/test_crud_archive.py
  git commit -m "feat(api): extend PATCH /api/stems/{id} with archive; add include_archived to stems list [plan: docs/superpowers/plans/2026-03-15-crud-bands-projects-songs-stems.md, Task 6, cli: claude-code, model: claude-sonnet-4-6]"
  ```

---

## Chunk 2: Frontend — Types, API Client, Components, Wiring

### Task 7: Update Types + `api.ts` + Contract Tests

**Files:**
- Modify: `frontend/src/lib/types.ts`
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/lib/api.test.ts` (find existing api test file; path may be `frontend/src/components/__tests__/api.test.ts` or similar — grep for `listBands` to locate it)

- [ ] **Step 1: Find the existing api test file**

  ```bash
  grep -r "listBands" frontend/src --include="*.test.*" -l
  ```

- [ ] **Step 2: Add `archived_at` to types in `types.ts`**

  Find each interface and add the field:

  ```typescript
  // In BandSummary (or Band interface — find by searching 'project_count')
  archived_at: string | null;

  // In ProjectSummary (find by searching 'band_id' in types)
  archived_at: string | null;

  // In SongSummary
  archived_at: string | null;

  // In SongStem (find by searching 'stem_key' or 'display_name' in types)
  archived_at: string | null;
  ```

  > Read `types.ts` first to identify the exact interface names before editing.

- [ ] **Step 3: Add new types for update payloads**

  At the end of `types.ts`, add:

  ```typescript
  export interface BandUpdatePayload {
    name?: string;
    archived?: boolean;
  }

  export interface ProjectUpdatePayload {
    name?: string;
    archived?: boolean;
  }

  export interface SongUpdatePayload {
    title?: string;
    archived?: boolean;
  }

  export interface StemUpdatePayload {
    display_name?: string;
    description?: string;
    archived?: boolean;
  }
  ```

- [ ] **Step 4: Add update functions to `api.ts`**

  After the `listBands` function, add:

  ```typescript
  export async function updateBand(
    bandId: number,
    payload: BandUpdatePayload,
  ): Promise<BandSummary> {
    const res = await fetchWithIdentity(`${BASE}/api/bands/${bandId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error("Failed to update band");
    return res.json();
  }

  export async function updateProject(
    projectId: number,
    payload: ProjectUpdatePayload,
  ): Promise<ProjectSummary> {
    const res = await fetchWithIdentity(`${BASE}/api/projects/${projectId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error("Failed to update project");
    return res.json();
  }

  export async function updateSong(
    songId: number,
    payload: SongUpdatePayload,
  ): Promise<SongSummary> {
    const res = await fetchWithIdentity(`${BASE}/api/songs/${songId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error("Failed to update song");
    return res.json();
  }

  export async function updateStem(
    stemId: number,
    payload: StemUpdatePayload,
  ): Promise<SongStem> {
    const res = await fetchWithIdentity(`${BASE}/api/stems/${stemId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error("Failed to update stem");
    return res.json();
  }
  ```

- [ ] **Step 5: Add `includeArchived` param to list functions**

  Update each list function signature and URL:

  ```typescript
  // listBands
  export async function listBands(includeArchived = false): Promise<BandsListResponse> {
    const url = includeArchived ? `${BASE}/api/bands?include_archived=true` : `${BASE}/api/bands`;
    const res = await fetchWithIdentity(url);
    ...
  }

  // listBandProjects
  export async function listBandProjects(bandId: number, includeArchived = false): Promise<ProjectsListResponse> {
    const url = includeArchived
      ? `${BASE}/api/bands/${bandId}/projects?include_archived=true`
      : `${BASE}/api/bands/${bandId}/projects`;
    ...
  }

  // listProjectSongs (find its name in api.ts)
  export async function listProjectSongs(projectId: number, includeArchived = false): Promise<...> {
    const url = includeArchived
      ? `${BASE}/api/projects/${projectId}/songs?include_archived=true`
      : `${BASE}/api/projects/${projectId}/songs`;
    ...
  }

  // listSongStems
  export async function listSongStems(songId: number, includeArchived = false): Promise<SongStemsResponse> {
    const url = includeArchived
      ? `${BASE}/api/songs/${songId}/stems?include_archived=true`
      : `${BASE}/api/songs/${songId}/stems`;
    ...
  }
  ```

- [ ] **Step 6: Add contract tests to the existing api test file**

  ```typescript
  import { updateBand, updateProject, updateSong, updateStem, listBands } from "../api"; // adjust import path

  it("updateBand sends PATCH with name payload", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ id: 1, name: "New Name", archived_at: null }),
    });
    (globalThis as any).fetch = fetchMock;
    const res = await updateBand(1, { name: "New Name" });
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/bands/1",
      expect.objectContaining({ method: "PATCH" }),
    );
    expect(res.name).toBe("New Name");
  });

  it("updateBand sends archive payload", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ id: 1, name: "Band", archived_at: "2026-03-15T00:00:00" }),
    });
    (globalThis as any).fetch = fetchMock;
    const res = await updateBand(1, { archived: true });
    const body = JSON.parse(fetchMock.mock.calls[0][1].body);
    expect(body.archived).toBe(true);
    expect(res.archived_at).toBeTruthy();
  });

  it("listBands appends include_archived param when true", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ bands: [] }),
    });
    (globalThis as any).fetch = fetchMock;
    await listBands(true);
    expect(fetchMock.mock.calls[0][0]).toContain("include_archived=true");
  });
  ```

- [ ] **Step 7: Run frontend tests**

  ```bash
  cd frontend && bun run test --run 2>&1 | tail -30
  ```
  Expected: all tests PASS (or pre-existing failures only).

- [ ] **Step 8: Commit**

  ```bash
  git add frontend/src/lib/types.ts frontend/src/lib/api.ts
  git add $(grep -r "listBands" frontend/src --include="*.test.*" -l)
  git commit -m "feat(frontend): add archived_at types; add updateBand/Project/Song/Stem api functions [plan: docs/superpowers/plans/2026-03-15-crud-bands-projects-songs-stems.md, Task 7, cli: claude-code, model: claude-sonnet-4-6]"
  ```

---

### Task 8: `ThreeDotMenu` Component + Tests

**Files:**
- Create: `frontend/src/components/ThreeDotMenu.tsx`
- Create: `frontend/src/components/__tests__/ThreeDotMenu.test.tsx`

- [ ] **Step 1: Create `ThreeDotMenu.tsx`**

  ```tsx
  import { useState, useEffect, useRef } from "react";

  export interface MenuItem {
    label: string;
    onClick: () => void;
    variant?: "default" | "danger";
  }

  interface ThreeDotMenuProps {
    items: MenuItem[];
    /** Optional: className for the trigger button */
    className?: string;
  }

  export function ThreeDotMenu({ items, className = "" }: ThreeDotMenuProps) {
    const [open, setOpen] = useState(false);
    const ref = useRef<HTMLDivElement>(null);

    useEffect(() => {
      if (!open) return;
      function handleClick(e: MouseEvent) {
        if (ref.current && !ref.current.contains(e.target as Node)) {
          setOpen(false);
        }
      }
      function handleKeyDown(e: KeyboardEvent) {
        if (e.key === "Escape") setOpen(false);
      }
      document.addEventListener("mousedown", handleClick);
      document.addEventListener("keydown", handleKeyDown);
      return () => {
        document.removeEventListener("mousedown", handleClick);
        document.removeEventListener("keydown", handleKeyDown);
      };
    }, [open]);

    return (
      <div ref={ref} className={`relative inline-block ${className}`}>
        <button
          type="button"
          aria-label="More options"
          onClick={(e) => {
            e.stopPropagation();
            setOpen((o) => !o);
          }}
          className="flex h-6 w-6 items-center justify-center rounded text-slate-400 opacity-40 hover:bg-slate-700 hover:opacity-100 transition-opacity"
        >
          ⋮
        </button>
        {open && (
          <div
            className="absolute right-0 z-50 mt-1 min-w-[140px] rounded border border-slate-700 bg-slate-800 py-1 shadow-lg"
            role="menu"
          >
            {items.map((item) => (
              <button
                key={item.label}
                type="button"
                role="menuitem"
                onClick={(e) => {
                  e.stopPropagation();
                  setOpen(false);
                  item.onClick();
                }}
                className={`block w-full px-3 py-1.5 text-left text-sm transition-colors hover:bg-slate-700 ${
                  item.variant === "danger" ? "text-red-400" : "text-slate-200"
                }`}
              >
                {item.label}
              </button>
            ))}
          </div>
        )}
      </div>
    );
  }
  ```

- [ ] **Step 2: Create `ThreeDotMenu.test.tsx`**

  ```tsx
  import { describe, it, expect, vi } from "vitest";
  import { render, screen, fireEvent } from "@testing-library/react";
  import { ThreeDotMenu } from "../ThreeDotMenu";

  describe("ThreeDotMenu", () => {
    it("renders a ⋮ trigger button", () => {
      render(<ThreeDotMenu items={[]} />);
      expect(screen.getByRole("button", { name: "More options" })).toBeTruthy();
    });

    it("shows menu items on click", () => {
      render(
        <ThreeDotMenu
          items={[{ label: "Rename", onClick: vi.fn() }]}
        />,
      );
      fireEvent.click(screen.getByRole("button", { name: "More options" }));
      expect(screen.getByRole("menuitem", { name: "Rename" })).toBeTruthy();
    });

    it("calls onClick and closes menu when item clicked", () => {
      const handler = vi.fn();
      render(
        <ThreeDotMenu
          items={[{ label: "Archive", onClick: handler }]}
        />,
      );
      fireEvent.click(screen.getByRole("button", { name: "More options" }));
      fireEvent.click(screen.getByRole("menuitem", { name: "Archive" }));
      expect(handler).toHaveBeenCalledTimes(1);
      expect(screen.queryByRole("menuitem")).toBeNull();
    });

    it("closes on Escape key", () => {
      render(
        <ThreeDotMenu items={[{ label: "Rename", onClick: vi.fn() }]} />,
      );
      fireEvent.click(screen.getByRole("button", { name: "More options" }));
      expect(screen.getByRole("menuitem")).toBeTruthy();
      fireEvent.keyDown(document, { key: "Escape" });
      expect(screen.queryByRole("menuitem")).toBeNull();
    });
  });
  ```

- [ ] **Step 3: Run tests**

  ```bash
  cd frontend && bun run test --run -- ThreeDotMenu 2>&1 | tail -20
  ```
  Expected: 4 PASS.

- [ ] **Step 4: Commit**

  ```bash
  git add frontend/src/components/ThreeDotMenu.tsx \
          frontend/src/components/__tests__/ThreeDotMenu.test.tsx
  git commit -m "feat(ui): add ThreeDotMenu component [plan: docs/superpowers/plans/2026-03-15-crud-bands-projects-songs-stems.md, Task 8, cli: claude-code, model: claude-sonnet-4-6]"
  ```

---

### Task 9: `RenameModal` Component + Tests

**Files:**
- Create: `frontend/src/components/RenameModal.tsx`
- Create: `frontend/src/components/__tests__/RenameModal.test.tsx`

- [ ] **Step 1: Create `RenameModal.tsx`**

  ```tsx
  import { useState, useEffect, useRef } from "react";

  interface RenameModalProps {
    /** Label shown above the input (e.g. "Band Name", "Song Title") */
    label: string;
    currentName: string;
    /** Only for songs: shows the read-only original upload filename */
    originalFilename?: string | null;
    onSave: (newName: string) => Promise<void> | void;
    onClose: () => void;
  }

  export function RenameModal({
    label,
    currentName,
    originalFilename,
    onSave,
    onClose,
  }: RenameModalProps) {
    const [name, setName] = useState(currentName);
    const [saving, setSaving] = useState(false);
    const inputRef = useRef<HTMLInputElement>(null);

    useEffect(() => {
      inputRef.current?.focus();
      inputRef.current?.select();
    }, []);

    async function handleSave() {
      if (!name.trim() || name.trim() === currentName) {
        onClose();
        return;
      }
      setSaving(true);
      try {
        await onSave(name.trim());
        onClose();
      } finally {
        setSaving(false);
      }
    }

    return (
      <div
        className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
        onClick={onClose}
      >
        <div
          className="w-full max-w-sm rounded-lg border border-slate-700 bg-slate-900 p-5 shadow-2xl"
          onClick={(e) => e.stopPropagation()}
        >
          <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-slate-300">
            Rename {label}
          </h2>
          <label className="block text-xs font-medium uppercase tracking-wide text-slate-400">
            {label}
            <input
              ref={inputRef}
              aria-label={label}
              value={name}
              onChange={(e) => setName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") void handleSave();
                if (e.key === "Escape") onClose();
              }}
              className="mt-1 w-full rounded border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-100 focus:border-purple-500 focus:outline-none"
            />
          </label>
          {originalFilename && (
            <p className="mt-2 text-xs text-slate-500">
              Original filename: <span className="font-mono">{originalFilename}</span>
            </p>
          )}
          <div className="mt-4 flex justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-3 py-1.5 text-sm text-slate-400 hover:text-white transition-colors"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={() => void handleSave()}
              disabled={saving || !name.trim()}
              className="rounded bg-purple-600 px-4 py-1.5 text-sm font-semibold text-white hover:bg-purple-500 disabled:opacity-50 transition-colors"
            >
              {saving ? "Saving…" : "Save"}
            </button>
          </div>
        </div>
      </div>
    );
  }
  ```

- [ ] **Step 2: Create `RenameModal.test.tsx`**

  ```tsx
  import { describe, it, expect, vi } from "vitest";
  import { render, screen, fireEvent, waitFor } from "@testing-library/react";
  import { RenameModal } from "../RenameModal";

  describe("RenameModal", () => {
    it("renders with current name pre-filled", () => {
      render(
        <RenameModal
          label="Band Name"
          currentName="My Band"
          onSave={vi.fn()}
          onClose={vi.fn()}
        />,
      );
      expect((screen.getByRole("textbox") as HTMLInputElement).value).toBe("My Band");
    });

    it("calls onSave with trimmed new name", async () => {
      const onSave = vi.fn().mockResolvedValue(undefined);
      const onClose = vi.fn();
      render(
        <RenameModal
          label="Band Name"
          currentName="Old Name"
          onSave={onSave}
          onClose={onClose}
        />,
      );
      fireEvent.change(screen.getByRole("textbox"), { target: { value: "  New Name  " } });
      fireEvent.click(screen.getByText("Save"));
      await waitFor(() => expect(onSave).toHaveBeenCalledWith("New Name"));
      await waitFor(() => expect(onClose).toHaveBeenCalled());
    });

    it("shows originalFilename for songs", () => {
      render(
        <RenameModal
          label="Song Title"
          currentName="My Song"
          originalFilename="track_01.mp3"
          onSave={vi.fn()}
          onClose={vi.fn()}
        />,
      );
      expect(screen.getByText(/track_01\.mp3/)).toBeTruthy();
    });

    it("calls onClose when Cancel is clicked", () => {
      const onClose = vi.fn();
      render(
        <RenameModal
          label="Band Name"
          currentName="My Band"
          onSave={vi.fn()}
          onClose={onClose}
        />,
      );
      fireEvent.click(screen.getByText("Cancel"));
      expect(onClose).toHaveBeenCalled();
    });
  });
  ```

- [ ] **Step 3: Run tests**

  ```bash
  cd frontend && bun run test --run -- RenameModal 2>&1 | tail -20
  ```
  Expected: 4 PASS.

- [ ] **Step 4: Commit**

  ```bash
  git add frontend/src/components/RenameModal.tsx \
          frontend/src/components/__tests__/RenameModal.test.tsx
  git commit -m "feat(ui): add RenameModal component [plan: docs/superpowers/plans/2026-03-15-crud-bands-projects-songs-stems.md, Task 9, cli: claude-code, model: claude-sonnet-4-6]"
  ```

---

### Task 10: Wire Band List (`BandSelectPage`)

**Files:**
- Read + Modify: `frontend/src/components/BandSelectPage.tsx`
- Read + Modify: `frontend/src/App.tsx` (to pass new props down)

- [ ] **Step 1: Read `BandSelectPage.tsx` fully**

  Understand its props interface (`BandSelectPageProps`) and how bands are rendered.

- [ ] **Step 2: Add props for CRUD callbacks + show-archived state**

  Add to `BandSelectPageProps`:
  ```typescript
  onRenameBand?: (bandId: number, newName: string) => Promise<void>;
  onArchiveBand?: (bandId: number, archived: boolean) => Promise<void>;
  showArchived?: boolean;
  onToggleShowArchived?: () => void;
  ```

- [ ] **Step 3: Add `ThreeDotMenu` to each band card**

  Inside the `bands.map(...)` render, add `ThreeDotMenu` to each band row:

  ```tsx
  import { ThreeDotMenu } from "./ThreeDotMenu";
  import { RenameModal } from "./RenameModal";

  // Inside the component, add state:
  const [renamingBand, setRenamingBand] = useState<Band | null>(null);

  // Inside the band card (the <button> that renders each band):
  // Wrap in a relative div so the ⋮ can be positioned correctly
  <div key={band.id} className="relative group">
    <button onClick={() => onSelectBand(band)} ...>
      {/* existing band card content */}
    </button>
    <div className="absolute right-4 top-4 opacity-0 group-hover:opacity-100 transition-opacity">
      <ThreeDotMenu
        items={[
          {
            label: "Rename",
            onClick: () => setRenamingBand(band),
          },
          {
            label: band.archived_at ? "Unarchive" : "Archive",
            onClick: () => onArchiveBand?.(band.id, !band.archived_at),
          },
        ]}
      />
    </div>
  </div>
  ```

- [ ] **Step 4: Add "Show archived" toggle above the band list**

  ```tsx
  <div className="mb-3 flex items-center justify-between">
    <span className="text-xs text-slate-500">
      {bands.length} band{bands.length !== 1 ? "s" : ""}
    </span>
    <label className="flex items-center gap-2 text-xs text-slate-400 cursor-pointer select-none">
      <input
        type="checkbox"
        checked={showArchived ?? false}
        onChange={onToggleShowArchived}
        className="rounded"
      />
      Show archived
    </label>
  </div>
  ```

- [ ] **Step 5: Add archived item visual treatment**

  Inside the band card, when `band.archived_at` is not null, add:
  - `opacity-50` class to the card
  - A small `"Archived"` badge: `<span className="ml-2 rounded bg-slate-700 px-1.5 py-0.5 text-[10px] text-slate-400">Archived</span>`

- [ ] **Step 6: Add `RenameModal` at bottom of component**

  ```tsx
  {renamingBand && (
    <RenameModal
      label="Band Name"
      currentName={renamingBand.name}
      onSave={(newName) => onRenameBand?.(renamingBand.id, newName) ?? Promise.resolve()}
      onClose={() => setRenamingBand(null)}
    />
  )}
  ```

- [ ] **Step 7: Wire callbacks in `App.tsx`**

  Read `App.tsx` to find where `<BandSelectPage>` is rendered. Add:

  ```tsx
  // State for show-archived toggle
  const [showArchivedBands, setShowArchivedBands] = useState(false);

  // Re-fetch bands when toggle changes
  useEffect(() => {
    void loadBands(showArchivedBands);
  }, [showArchivedBands]);

  // Callbacks
  async function handleRenameBand(bandId: number, newName: string) {
    await updateBand(bandId, { name: newName });
    await loadBands(showArchivedBands);
  }

  async function handleArchiveBand(bandId: number, archived: boolean) {
    await updateBand(bandId, { archived });
    await loadBands(showArchivedBands);
  }

  // Pass to BandSelectPage:
  <BandSelectPage
    ...
    onRenameBand={handleRenameBand}
    onArchiveBand={handleArchiveBand}
    showArchived={showArchivedBands}
    onToggleShowArchived={() => setShowArchivedBands((v) => !v)}
  />
  ```

  > **Note:** `loadBands` is whatever the existing function is called in App.tsx that fetches and sets band state. Find it by searching for `listBands` usage.

- [ ] **Step 8: Manual smoke test**

  Start the app (`make frontend` or `make up`). Navigate to band list. Hover a band — ⋮ should appear. Click "Rename" → modal opens. Rename and save → band name updates. Click "Archive" → band disappears. Toggle "Show archived" → band reappears with badge.

- [ ] **Step 9: Commit**

  ```bash
  git add frontend/src/components/BandSelectPage.tsx frontend/src/App.tsx
  git commit -m "feat(ui): wire ThreeDotMenu + archive toggle into BandSelectPage [plan: docs/superpowers/plans/2026-03-15-crud-bands-projects-songs-stems.md, Task 10, cli: claude-code, model: claude-sonnet-4-6]"
  ```

---

### Task 11: Wire Project List

**Files:**
- Read: `frontend/src/App.tsx` (find project list rendering — search for `listBandProjects` usage)
- Modify: whichever component renders the project list (may be inside `App.tsx` or a separate component)

- [ ] **Step 1: Find where projects are listed**

  ```bash
  grep -r "listBandProjects\|projects\.map" frontend/src --include="*.tsx" -l
  ```

  Read the identified file(s) fully before making any changes.

- [ ] **Step 2: Add props for project CRUD to the project list component**

  If projects are rendered in a dedicated component (e.g. `BandDetailPage`, `ProjectListPanel`, or similar), add these props to its interface:

  ```typescript
  onRenameProject?: (projectId: number, newName: string) => Promise<void>;
  onArchiveProject?: (projectId: number, archived: boolean) => Promise<void>;
  showArchived?: boolean;
  onToggleShowArchived?: () => void;
  ```

  If projects are rendered directly in `App.tsx` without a separate component, add the state and handlers there directly (no prop-passing needed).

- [ ] **Step 3: Add `ThreeDotMenu` to each project card**

  Inside the `projects.map(...)` render, wrap each project card in a `relative group` div and add the ⋮ menu:

  ```tsx
  import { ThreeDotMenu } from "./ThreeDotMenu";
  import { RenameModal } from "./RenameModal";

  // State inside the component:
  const [renamingProject, setRenamingProject] = useState<ProjectSummary | null>(null);

  // Per project card:
  <div key={project.id} className="relative group">
    <button onClick={() => onSelectProject?.(project)} ...>
      {/* existing project card content */}
      {project.archived_at && (
        <span className="ml-2 rounded bg-slate-700 px-1.5 py-0.5 text-[10px] text-slate-400">
          Archived
        </span>
      )}
    </button>
    <div className={`absolute right-3 top-3 opacity-0 group-hover:opacity-100 transition-opacity ${project.archived_at ? "opacity-100" : ""}`}>
      <ThreeDotMenu
        items={[
          { label: "Rename", onClick: () => setRenamingProject(project) },
          {
            label: project.archived_at ? "Unarchive" : "Archive",
            onClick: () => onArchiveProject?.(project.id, !project.archived_at),
          },
        ]}
      />
    </div>
  </div>

  {renamingProject && (
    <RenameModal
      label="Project Name"
      currentName={renamingProject.name}
      onSave={(newName) => onRenameProject?.(renamingProject.id, newName) ?? Promise.resolve()}
      onClose={() => setRenamingProject(null)}
    />
  )}
  ```

  Apply `opacity-50` to the card button when `project.archived_at` is set:
  ```tsx
  className={`... ${project.archived_at ? "opacity-50" : ""}`}
  ```

- [ ] **Step 4: Add "Show archived" toggle above the project list**

  ```tsx
  <div className="mb-3 flex items-center justify-between">
    <span className="text-xs text-slate-500">
      {projects.length} project{projects.length !== 1 ? "s" : ""}
    </span>
    <label className="flex items-center gap-2 text-xs text-slate-400 cursor-pointer select-none">
      <input
        type="checkbox"
        checked={showArchived ?? false}
        onChange={onToggleShowArchived}
        className="rounded"
      />
      Show archived
    </label>
  </div>
  ```

- [ ] **Step 5: Wire callbacks in `App.tsx`**

  ```tsx
  // State
  const [showArchivedProjects, setShowArchivedProjects] = useState(false);

  // Re-fetch when toggle changes (find the existing loadProjects function or equivalent)
  useEffect(() => {
    if (selectedBandId) void loadProjects(selectedBandId, showArchivedProjects);
  }, [showArchivedProjects, selectedBandId]);

  // Handlers
  async function handleRenameProject(projectId: number, newName: string) {
    await updateProject(projectId, { name: newName });
    if (selectedBandId) await loadProjects(selectedBandId, showArchivedProjects);
  }

  async function handleArchiveProject(projectId: number, archived: boolean) {
    await updateProject(projectId, { archived });
    if (selectedBandId) await loadProjects(selectedBandId, showArchivedProjects);
  }

  // Pass to project list component (or use directly if inline):
  // onRenameProject={handleRenameProject}
  // onArchiveProject={handleArchiveProject}
  // showArchived={showArchivedProjects}
  // onToggleShowArchived={() => setShowArchivedProjects(v => !v)}
  ```

  > `loadProjects` is whatever the existing function is called in App.tsx that calls `listBandProjects`. Find it by searching for `listBandProjects` usage. Update its call to pass `includeArchived`.

- [ ] **Step 6: Commit**

  Stage all modified files identified in Step 1 plus App.tsx:

  ```bash
  # Stage all files changed in this task (adapt paths from Step 1 results)
  git add frontend/src/App.tsx
  # Also stage the project list component file if it is separate from App.tsx
  git commit -m "feat(ui): wire ThreeDotMenu + archive toggle into project list [plan: docs/superpowers/plans/2026-03-15-crud-bands-projects-songs-stems.md, Task 11, cli: claude-code, model: claude-sonnet-4-6]"
  ```

---

### Task 12: Wire Song Library (`SongLibraryPanel`) + Stem Mixer (`StemMixerPanel`)

**Files:**
- Read + Modify: `frontend/src/components/SongLibraryPanel.tsx`
- Read + Modify: `frontend/src/components/StemMixerPanel.tsx`
- Modify: `frontend/src/App.tsx` (to pass new callbacks)

- [ ] **Step 1: Read `SongLibraryPanel.tsx` fully**

  Understand its props interface. Note: songs are shown as a list; there's an "Upload" button. You will add ⋮ menus and a show-archived toggle.

- [ ] **Step 2: Add song CRUD props to `SongLibraryPanelProps`**

  ```typescript
  onRenameSong?: (songId: number, newName: string) => Promise<void>;
  onArchiveSong?: (songId: number, archived: boolean) => Promise<void>;
  showArchived?: boolean;
  onToggleShowArchived?: () => void;
  ```

- [ ] **Step 3: Wire `ThreeDotMenu` + `RenameModal` into song list**

  Follow the same pattern as Task 10:
  - `ThreeDotMenu` in each song row with "Rename" (opens `RenameModal`) and "Archive|Unarchive"
  - `RenameModal` for songs passes `originalFilename={song.original_filename}` so the modal shows the original filename
  - "Show archived" toggle above the list
  - Archived items: `opacity-50` + "Archived" badge
  - Each song row should also display `original_filename` below the title as muted text (if it differs from title):
    ```tsx
    {song.original_filename && song.original_filename !== song.title && (
      <span className="block text-[10px] text-slate-500 font-mono">{song.original_filename}</span>
    )}
    ```

- [ ] **Step 4: Read `StemMixerPanel.tsx` fully**

  Understand its props. Note: it renders stems as a list of checkboxes. You will add ⋮ menus and a show-archived toggle.

- [ ] **Step 5: Add stem CRUD props to `StemMixerPanel`**

  ```typescript
  onRenameStem?: (stemId: number, newName: string) => Promise<void>;
  onDescribeStem?: (stemId: number, description: string) => Promise<void>;
  onArchiveStem?: (stemId: number, archived: boolean) => Promise<void>;
  showArchived?: boolean;
  onToggleShowArchived?: () => void;
  ```

  > Note: `StemMixerPanel` may not have stem `id` fields in its current props — read the component and its type to check. If `SongStem` doesn't have `id`, add it.

- [ ] **Step 6: Wire `ThreeDotMenu` into each stem row**

  Each stem label row gets a ⋮ menu with "Rename", "Edit description", "Archive|Unarchive":

  ```tsx
  <ThreeDotMenu
    items={[
      { label: "Rename", onClick: () => setRenamingStem(stem) },
      { label: "Edit description", onClick: () => setDescribingStem(stem) },
      {
        label: stem.archived_at ? "Unarchive" : "Archive",
        onClick: () => onArchiveStem?.(stem.id, !stem.archived_at),
      },
    ]}
  />
  ```

  For "Edit description", open `RenameModal` with `label="Description"` and `currentName={stem.description ?? ""}`.

- [ ] **Step 7: Wire callbacks in `App.tsx`**

  Add `showArchivedSongs`, `showArchivedStems` state + toggle handlers + `updateSong`/`updateStem` callbacks, and refetch logic.

- [ ] **Step 8: Run all frontend tests**

  ```bash
  cd frontend && bun run test --run 2>&1 | tail -30
  ```
  Fix any regressions before committing.

- [ ] **Step 9: Commit**

  ```bash
  git add frontend/src/components/SongLibraryPanel.tsx \
          frontend/src/components/StemMixerPanel.tsx \
          frontend/src/App.tsx
  git commit -m "feat(ui): wire ThreeDotMenu + archive toggle into SongLibraryPanel and StemMixerPanel [plan: docs/superpowers/plans/2026-03-15-crud-bands-projects-songs-stems.md, Task 12, cli: claude-code, model: claude-sonnet-4-6]"
  ```

---

## Final Verification

- [ ] Run full backend test suite: `cd backend && uv run pytest -v`
- [ ] Run full frontend test suite: `cd frontend && bun run test --run`
- [ ] Start app with `make up` and manually verify:
  - Band: rename, archive, show-archived toggle, unarchive
  - Project: same
  - Song: rename (original filename shown), archive, show-archived
  - Stem: rename, edit description, archive, show-archived
- [ ] Invoke `superpowers:verification-before-completion` skill before final handoff
