# Stem Blob Storage & Management — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate stem audio from local filesystem to LibSQL BLOBs, make generation additive (never replace), and expose rename/describe/delete endpoints wired into the activity feed.

**Architecture:** Table-rebuild migration drops the `UNIQUE(song_id, stem_key)` constraint and adds `audio_blob`, `description`, `generation_id`, and attribution columns. `StemResult` and `BassAnalysisStemResult` return `audio_data: bytes` instead of paths. All three new endpoints (`GET /audio`, `PATCH`, `DELETE`) fire activity events.

**Tech Stack:** Python 3.13+, FastAPI, LibSQL (`libsql_client`), pytest, uv

**Spec:** `docs/superpowers/specs/2026-03-13-stem-blob-storage-design.md`

**Commit convention:** Each commit message must reference `docs/plans/2026-03-13-stem-blob-storage-implementation.md`, the task name, tool `opencode`, and model `gpt-5.1-codex-max`.

---

## Chunk 1: DB Migration + Schema

### Task 1: DB migration — table rebuild for `song_stems`

**Files:**
- Modify: `backend/app/db_schema.sql`
- Modify: `backend/app/db.py`
- Test: `backend/tests/test_db_bootstrap.py`

**Context:** The existing `song_stems` table has `UNIQUE(song_id, stem_key)` and `relative_path TEXT NOT NULL`. SQLite cannot drop constraints or change column nullability with `ALTER TABLE`, so we must rebuild the table. The migration guard checks for `audio_blob` column existence — if present, skip.

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_db_bootstrap.py`:

```python
import asyncio
import pytest
from pathlib import Path

def _make_db(tmp_path, monkeypatch):
    import importlib
    db_path = tmp_path / "test-migration.db"
    monkeypatch.setenv("DECHORD_DB_URL", f"file:{db_path}")
    import app.db as db_mod
    asyncio.run(db_mod.reset_db_client_for_tests())
    return importlib.reload(db_mod)

def test_song_stems_migration_adds_audio_blob_and_drops_unique(tmp_path, monkeypatch):
    db_mod = _make_db(tmp_path, monkeypatch)
    asyncio.run(db_mod.init_db())

    async def check():
        rs = await db_mod.execute("PRAGMA table_info(song_stems)")
        cols = {str(row[1]) for row in rs.rows}
        assert "audio_blob" in cols, "audio_blob column missing"
        assert "description" in cols, "description column missing"
        assert "generation_id" in cols, "generation_id column missing"
        assert "created_by_user_id" in cols, "created_by_user_id column missing"
        assert "created_by_name" in cols, "created_by_name column missing"
        # relative_path must still exist (nullable) for legacy compat
        assert "relative_path" in cols, "relative_path must be retained as nullable"
        # Insert two rows with the same stem_key — must not violate any constraint
        await db_mod.execute(
            "INSERT INTO song_stems (song_id, stem_key, audio_blob, mime_type, source_type, display_name, version_label) "
            "SELECT s.id, 'bass', X'', 'audio/wav', 'system', 'Bass', 'v1' FROM songs s LIMIT 1"
        )
        await db_mod.execute(
            "INSERT INTO song_stems (song_id, stem_key, audio_blob, mime_type, source_type, display_name, version_label) "
            "SELECT s.id, 'bass', X'', 'audio/wav', 'system', 'Bass v2', 'v2' FROM songs s LIMIT 1"
        )
        count_rs = await db_mod.execute("SELECT COUNT(*) FROM song_stems WHERE stem_key = 'bass'")
        assert int(count_rs.rows[0][0]) == 2, "Expected 2 bass stems (additive)"

    # Upload a stub song first so the FK constraint is satisfied
    async def setup_and_check():
        await db_mod.init_db()
        await db_mod.execute(
            "INSERT INTO songs (user_id, title, audio_blob) SELECT id, 'Test', X'' FROM users LIMIT 1"
        )
        await check()

    asyncio.run(setup_and_check())

def test_song_stems_migration_is_idempotent(tmp_path, monkeypatch):
    db_mod = _make_db(tmp_path, monkeypatch)
    async def run():
        await db_mod.init_db()
        await db_mod.init_db()  # second call must not error
    asyncio.run(run())
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/wojciechgula/Projects/DeChord/backend
uv run pytest tests/test_db_bootstrap.py::test_song_stems_migration_adds_audio_blob_and_drops_unique -v
```
Expected: FAIL — `audio_blob` column missing

- [ ] **Step 3: Update `db_schema.sql`**

Replace the `song_stems` CREATE TABLE block (keep the rest of the file intact):

```sql
CREATE TABLE IF NOT EXISTS song_stems (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    song_id INTEGER NOT NULL,
    stem_key TEXT NOT NULL,
    relative_path TEXT,
    audio_blob BLOB NOT NULL DEFAULT X'',
    mime_type TEXT,
    duration REAL,
    source_type TEXT NOT NULL DEFAULT 'system' CHECK(source_type IN ('system', 'user')),
    display_name TEXT,
    description TEXT,
    version_label TEXT NOT NULL DEFAULT 'legacy',
    generation_id TEXT,
    created_by_user_id INTEGER,
    created_by_name TEXT,
    uploaded_by_name TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (song_id) REFERENCES songs(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by_user_id) REFERENCES users(id) ON DELETE SET NULL
);
```

Also add to the index block at the bottom of `db_schema.sql`:
```sql
CREATE INDEX IF NOT EXISTS idx_song_stems_generation_id ON song_stems(generation_id);
```

- [ ] **Step 4: Add table-rebuild migration to `db.py`**

Add a new async helper before `_run_schema_migrations`:

```python
async def _migrate_song_stems_to_blob() -> None:
    """Rebuild song_stems to add audio_blob and drop UNIQUE(song_id, stem_key)."""
    if await _table_has_column("song_stems", "audio_blob"):
        return  # already migrated

    await execute("""
        CREATE TABLE IF NOT EXISTS song_stems_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            song_id INTEGER NOT NULL,
            stem_key TEXT NOT NULL,
            relative_path TEXT,
            audio_blob BLOB NOT NULL DEFAULT X'',
            mime_type TEXT,
            duration REAL,
            source_type TEXT NOT NULL DEFAULT 'system' CHECK(source_type IN ('system', 'user')),
            display_name TEXT,
            description TEXT,
            version_label TEXT NOT NULL DEFAULT 'legacy',
            generation_id TEXT,
            created_by_user_id INTEGER,
            created_by_name TEXT,
            uploaded_by_name TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (song_id) REFERENCES songs(id) ON DELETE CASCADE,
            FOREIGN KEY (created_by_user_id) REFERENCES users(id) ON DELETE SET NULL
        )
    """)
    await execute("""
        INSERT INTO song_stems_new (
            id, song_id, stem_key, relative_path, audio_blob,
            mime_type, duration, source_type, display_name, description,
            version_label, generation_id, created_by_user_id, created_by_name,
            uploaded_by_name, created_at, updated_at
        )
        SELECT
            id, song_id, stem_key, relative_path, X'',
            mime_type, duration, source_type, display_name, NULL,
            version_label, NULL, NULL, uploaded_by_name,
            uploaded_by_name, created_at, updated_at
        FROM song_stems
    """)
    await execute("DROP TABLE song_stems")
    await execute("ALTER TABLE song_stems_new RENAME TO song_stems")
    await execute("CREATE INDEX IF NOT EXISTS idx_song_stems_song_id ON song_stems(song_id)")
    await execute("CREATE INDEX IF NOT EXISTS idx_song_stems_generation_id ON song_stems(generation_id)")
```

Call it at the top of `_run_schema_migrations()`:

```python
async def _run_schema_migrations() -> None:
    await _migrate_song_stems_to_blob()   # <-- add this line first
    await _ensure_column("notes", "author_user_id", "author_user_id INTEGER")
    # ... rest unchanged ...
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd /Users/wojciechgula/Projects/DeChord/backend
uv run pytest tests/test_db_bootstrap.py -v
```
Expected: all test_db_bootstrap tests PASS

- [ ] **Step 6: Commit**

```bash
cd /Users/wojciechgula/Projects/DeChord
git add backend/app/db_schema.sql backend/app/db.py backend/tests/test_db_bootstrap.py
git commit -m "$(cat <<'EOF'
feat: rebuild song_stems with audio_blob and drop UNIQUE constraint

docs/plans/2026-03-13-stem-blob-storage-implementation.md task: DB migration — table rebuild for song_stems | opencode | gpt-5.1-codex-max

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Chunk 2: `stems.py` — In-Memory Pipeline

### Task 2: `StemResult`, `_read_wav_to_bytes`, `split_to_stems`, `build_stems_zip`

**Files:**
- Modify: `backend/app/stems.py`
- Modify: `backend/tests/test_stems.py`

**Context:** `StemResult.relative_path: str` → `audio_data: bytes`. `split_to_stems` still accepts `output_dir` for Demucs' internal use, but reads every output file into bytes before returning, then deletes the temp files. `build_stems_zip` switches from reading disk paths to accepting bytes directly.

- [ ] **Step 1: Write failing tests**

Add to `backend/tests/test_stems.py`:

```python
def test_split_to_stems_returns_audio_bytes_not_paths(tmp_path: Path):
    """split_to_stems must return audio_data bytes, not relative_path strings."""
    audio_path = tmp_path / "track.wav"
    audio_path.write_bytes(b"fake-audio")
    out_dir = tmp_path / "stems"

    def fake_separate(input_audio: str, output_dir: Path, progress_callback):
        output_dir.mkdir(parents=True, exist_ok=True)
        bass = output_dir / "bass.wav"
        bass.write_bytes(b"bass-data")
        return {"bass": bass}

    results = split_to_stems(
        audio_path=str(audio_path),
        output_dir=out_dir,
        separate_fn=fake_separate,
    )

    assert len(results) == 1
    stem = results[0]
    assert stem.stem_key == "bass"
    assert stem.audio_data == b"bass-data"
    assert not hasattr(stem, "relative_path") or stem.relative_path is None  # old field gone


def test_split_to_stems_deletes_temp_files_after_reading(tmp_path: Path):
    """Temp output files must be deleted after bytes are read."""
    audio_path = tmp_path / "track.wav"
    audio_path.write_bytes(b"fake-audio")
    out_dir = tmp_path / "stems"
    written_paths: list[Path] = []

    def fake_separate(input_audio: str, output_dir: Path, progress_callback):
        output_dir.mkdir(parents=True, exist_ok=True)
        p = output_dir / "vocals.wav"
        p.write_bytes(b"vocals")
        written_paths.append(p)
        return {"vocals": p}

    split_to_stems(audio_path=str(audio_path), output_dir=out_dir, separate_fn=fake_separate)

    assert written_paths, "fake separator was not called"
    for p in written_paths:
        assert not p.exists(), f"Temp file {p} was not deleted"


def test_build_stems_zip_from_bytes(tmp_path: Path):
    """build_stems_zip accepts (stem_key, audio_data, mime_type) tuples."""
    from app.stems import build_stems_zip
    archive_bytes, archive_name = build_stems_zip(
        "My Song",
        stems=[
            ("bass", b"bass-audio", "audio/wav"),
            ("drums", b"drums-audio", "audio/wav"),
        ],
    )
    assert archive_name == "My_Song-stems.zip"
    import io, zipfile
    with zipfile.ZipFile(io.BytesIO(archive_bytes), "r") as z:
        assert sorted(z.namelist()) == ["bass.wav", "drums.wav"]
        assert z.read("bass.wav") == b"bass-audio"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/wojciechgula/Projects/DeChord/backend
uv run pytest tests/test_stems.py::test_split_to_stems_returns_audio_bytes_not_paths tests/test_stems.py::test_split_to_stems_deletes_temp_files_after_reading tests/test_stems.py::test_build_stems_zip_from_bytes -v
```
Expected: FAIL (attribute errors)

- [ ] **Step 3: Update `StemResult` in `stems.py`**

```python
@dataclass
class StemResult:
    stem_key: str
    audio_data: bytes
    mime_type: str
    duration: float | None = None
```

- [ ] **Step 4: Add `_read_wav_to_bytes` helper**

Add after `_write_wav_mono`:

```python
def _read_wav_to_bytes(path: Path) -> bytes:
    data = path.read_bytes()
    path.unlink(missing_ok=True)
    return data
```

- [ ] **Step 5: Update `split_to_stems` — read bytes, delete temp files**

In `split_to_stems`, replace the loop that builds `stems`:

```python
    stems: list[StemResult] = []
    for stem_key in sorted(separated.keys()):
        stem_path = separated[stem_key]
        mime_type, _ = mimetypes.guess_type(stem_path.name)
        audio_data = _read_wav_to_bytes(stem_path)  # reads bytes and deletes the file
        stems.append(
            StemResult(
                stem_key=stem_key,
                audio_data=audio_data,
                mime_type=mime_type or "audio/wav",
            )
        )
```

- [ ] **Step 6: Update `build_stems_zip` signature and implementation**

Replace the function:

```python
def build_stems_zip(
    song_title: str,
    stems: list[tuple[str, bytes, str]],  # (stem_key, audio_data, mime_type)
) -> tuple[bytes, str]:
    safe_title = re.sub(r"[^a-zA-Z0-9._-]+", "_", song_title or "song").strip("._-") or "song"
    archive_name = f"{safe_title}-stems.zip"
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for stem_key, audio_data, mime_type in stems:
            if not audio_data:
                continue  # skip legacy empty-blob stems
            ext = mimetypes.guess_extension(mime_type) or ".wav"
            if ext == ".ksh":  # mimetypes maps audio/wav to .ksh on some systems
                ext = ".wav"
            archive.writestr(f"{stem_key}{ext}", audio_data)
    return zip_buffer.getvalue(), archive_name
```

- [ ] **Step 7: Fix existing `test_build_stems_zip_packages_existing_files` test**

The old test passes `StemResult` objects. Update it to use the new tuple signature:

```python
def test_build_stems_zip_packages_existing_files(tmp_path: Path):
    from app.stems import build_stems_zip

    archive_bytes, archive_name = build_stems_zip(
        "The Trooper",
        stems=[
            ("bass", b"bass", "audio/wav"),
            ("drums", b"drums", "audio/wav"),
        ],
    )

    assert archive_name == "The_Trooper-stems.zip"
    with zipfile.ZipFile(io.BytesIO(archive_bytes), "r") as archive:
        assert sorted(archive.namelist()) == ["bass.wav", "drums.wav"]
```

- [ ] **Step 8: Run all stems tests**

```bash
cd /Users/wojciechgula/Projects/DeChord/backend
uv run pytest tests/test_stems.py -v
```
Expected: all PASS (the fake-separator tests that check `stem.relative_path` will need updating — fix any failures by replacing `stem.relative_path` assertions with `stem.audio_data`)

- [ ] **Step 9: Commit**

```bash
cd /Users/wojciechgula/Projects/DeChord
git add backend/app/stems.py backend/tests/test_stems.py
git commit -m "$(cat <<'EOF'
feat: StemResult returns audio_data bytes; split_to_stems and build_stems_zip are filesystem-free

docs/plans/2026-03-13-stem-blob-storage-implementation.md task: StemResult, _read_wav_to_bytes, split_to_stems, build_stems_zip | opencode | gpt-5.1-codex-max

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: `BassAnalysisStemResult` returns `audio_data: bytes`

**Files:**
- Modify: `backend/app/stems.py`
- Modify: `backend/tests/test_stems.py`

**Context:** `BassAnalysisStemResult.path: Path` → `audio_data: bytes`. All return points in `build_bass_analysis_stem` call `path.read_bytes()` before returning and delete the temp file. The caller in `main.py` (`_regenerate_song_tabs`) will be updated in Task 6.

- [ ] **Step 1: Write failing test**

Add to `backend/tests/test_stems.py`:

```python
def test_build_bass_analysis_stem_returns_bytes(tmp_path: Path):
    """build_bass_analysis_stem must return audio_data bytes, not a path."""
    import numpy as np
    from scipy.io import wavfile as scipy_wav
    from app.stems import build_bass_analysis_stem, BassAnalysisStemResult

    sample_rate = 22050
    audio = (np.sin(2 * np.pi * 55 * np.linspace(0, 1, sample_rate)) * 32767).astype(np.int16)

    def write_wav(p: Path) -> Path:
        p.parent.mkdir(parents=True, exist_ok=True)
        scipy_wav.write(str(p), sample_rate, audio)
        return p

    bass_path = write_wav(tmp_path / "bass.wav")
    other_path = write_wav(tmp_path / "other.wav")
    drums_path = write_wav(tmp_path / "drums.wav")

    config = stems_mod.StemAnalysisConfig(
        demucs_model="htdemucs_ft",
        demucs_fallback_model="htdemucs",
        enable_bass_refinement=True,
        analysis_highpass_hz=35.0,
        analysis_lowpass_hz=300.0,
        analysis_sample_rate=22050,
        enable_model_ensemble=False,
        candidate_models=["htdemucs_ft"],
    )

    result = build_bass_analysis_stem(
        stems={"bass": bass_path, "other": other_path, "drums": drums_path},
        output_dir=tmp_path / "analysis",
        analysis_config=config,
    )

    assert isinstance(result, BassAnalysisStemResult)
    assert isinstance(result.audio_data, bytes)
    assert len(result.audio_data) > 0
    assert not hasattr(result, "path") or result.path is None
```

- [ ] **Step 2: Run to verify it fails**

```bash
cd /Users/wojciechgula/Projects/DeChord/backend
uv run pytest tests/test_stems.py::test_build_bass_analysis_stem_returns_bytes -v
```
Expected: FAIL — `BassAnalysisStemResult` has no `audio_data`

- [ ] **Step 3: Update `BassAnalysisStemResult` dataclass**

```python
@dataclass(frozen=True)
class BassAnalysisStemResult:
    audio_data: bytes       # replaces path: Path
    source_model: str
    diagnostics: dict[str, object]
```

- [ ] **Step 4: Update all return points in `build_bass_analysis_stem`**

There are multiple `return BassAnalysisStemResult(path=..., ...)` sites. For each, replace `path=output_path` with `audio_data=output_path.read_bytes()`. Then delete the output file after reading. Pattern:

```python
# Before:
return BassAnalysisStemResult(path=output_path, source_model=..., diagnostics=...)

# After:
_audio_data = output_path.read_bytes()
output_path.unlink(missing_ok=True)
return BassAnalysisStemResult(audio_data=_audio_data, source_model=..., diagnostics=...)
```

Apply this to every `return BassAnalysisStemResult(` in `build_bass_analysis_stem`. Use grep to find all occurrences:
```bash
grep -n "return BassAnalysisStemResult" backend/app/stems.py
```

- [ ] **Step 5: Fix existing test that checks `result.path`**

Find in `test_stems.py`:
```python
assert result.path.exists()
assert result.path.name == "bass_analysis.wav"
```
Replace with:
```python
assert isinstance(result.audio_data, bytes)
assert len(result.audio_data) > 0
```

- [ ] **Step 6: Run stems tests**

```bash
cd /Users/wojciechgula/Projects/DeChord/backend
uv run pytest tests/test_stems.py -v
```
Expected: all PASS

- [ ] **Step 7: Commit**

```bash
cd /Users/wojciechgula/Projects/DeChord
git add backend/app/stems.py backend/tests/test_stems.py
git commit -m "$(cat <<'EOF'
feat: BassAnalysisStemResult returns audio_data bytes instead of path

docs/plans/2026-03-13-stem-blob-storage-implementation.md task: BassAnalysisStemResult returns audio_data bytes | opencode | gpt-5.1-codex-max

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Chunk 3: `main.py` — DB Helpers & Persistence

### Task 4: Replace stem DB helpers with blob-aware versions

**Files:**
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_api.py`

**Context:** Remove `_replace_song_stem`, `_persist_generated_stems`, `_is_user_uploaded_stem_path`, `STEMS_DIR`. Update `_build_stem_display_name`, `_serialize_song_stem`, `_load_song_stems`, `_load_active_song_stem`. Add `_insert_stem_blob`, `_load_stem_by_id`, `_persist_generated_stems_blobs`.

- [ ] **Step 1: Write failing tests**

Add to `backend/tests/test_api.py`:

```python
def test_stem_generation_is_additive(tmp_path, monkeypatch):
    """Two stem generation runs for the same song must produce 2 rows per stem_key, not 1."""
    import asyncio, uuid
    from pathlib import Path
    client = _build_client(tmp_path, monkeypatch)
    import app.main as main

    # Upload a song
    resp = client.post(
        "/api/songs",
        files={"file": ("song.mp3", b"\xff\xfb\x90\x00" * 100, "audio/mpeg")},
    )
    assert resp.status_code == 200
    song_id = resp.json()["id"]

    # Patch split_to_stems to return fake stems twice
    from app.stems import StemResult
    fake_audio = b"fake-wav-data"

    def fake_split(*args, **kwargs):
        return [StemResult(stem_key="bass", audio_data=fake_audio, mime_type="audio/wav")]

    monkeypatch.setattr(main, "split_to_stems", fake_split)

    # Trigger stem generation twice
    client.post(f"/api/songs/{song_id}/stems/generate")
    client.post(f"/api/songs/{song_id}/stems/generate")

    # List stems — must have 2 bass rows
    resp = client.get(f"/api/songs/{song_id}/stems")
    assert resp.status_code == 200
    stems = resp.json()
    bass_stems = [s for s in stems if s["stem_key"] == "bass"]
    assert len(bass_stems) == 2, f"Expected 2 bass stems, got {len(bass_stems)}"


def test_stem_audio_endpoint_returns_blob(tmp_path, monkeypatch):
    """GET /api/stems/{stem_id}/audio returns the stored audio bytes."""
    import asyncio
    client = _build_client(tmp_path, monkeypatch)
    import app.main as main
    from app.stems import StemResult

    resp = client.post(
        "/api/songs",
        files={"file": ("song.mp3", b"\xff\xfb\x90\x00" * 100, "audio/mpeg")},
    )
    song_id = resp.json()["id"]

    fake_audio = b"real-wav-bytes-here"
    monkeypatch.setattr(main, "split_to_stems", lambda *a, **k: [
        StemResult(stem_key="bass", audio_data=fake_audio, mime_type="audio/wav")
    ])
    client.post(f"/api/songs/{song_id}/stems/generate")

    stems_resp = client.get(f"/api/songs/{song_id}/stems")
    stem_id = stems_resp.json()[0]["id"]

    audio_resp = client.get(f"/api/stems/{stem_id}/audio")
    assert audio_resp.status_code == 200
    assert audio_resp.content == fake_audio
    assert "audio" in audio_resp.headers["content-type"]


def test_stem_audio_endpoint_legacy_row_returns_404(tmp_path, monkeypatch):
    """GET /api/stems/{stem_id}/audio returns 404 for a legacy row with empty blob."""
    import asyncio
    client = _build_client(tmp_path, monkeypatch)
    import app.db as db_mod

    # Insert a legacy-style stem row with empty blob
    async def insert_legacy():
        await db_mod.init_db()
        rs = await db_mod.execute("SELECT id FROM songs LIMIT 1")
        if not rs.rows:
            await db_mod.execute(
                "INSERT INTO songs (user_id, title, audio_blob) SELECT id, 'Legacy', X'' FROM users LIMIT 1"
            )
            rs = await db_mod.execute("SELECT id FROM songs LIMIT 1")
        song_id = int(rs.rows[0][0])
        insert_rs = await db_mod.execute(
            "INSERT INTO song_stems (song_id, stem_key, audio_blob, mime_type, source_type, display_name, version_label) "
            "VALUES (?, 'bass', X'', 'audio/wav', 'system', 'Bass', 'legacy') RETURNING id",
            [song_id],
        )
        return int(insert_rs.rows[0][0])

    stem_id = asyncio.run(insert_legacy())

    resp = client.get(f"/api/stems/{stem_id}/audio")
    assert resp.status_code == 404
    assert "legacy" in resp.json()["detail"].lower()
```

- [ ] **Step 2: Run to verify they fail**

```bash
cd /Users/wojciechgula/Projects/DeChord/backend
uv run pytest tests/test_api.py::test_stem_generation_is_additive tests/test_api.py::test_stem_audio_endpoint_returns_blob tests/test_api.py::test_stem_audio_endpoint_legacy_row_returns_404 -v
```
Expected: FAIL

- [ ] **Step 3: Remove obsolete symbols from `main.py`**

Remove these functions entirely:
- `_is_user_uploaded_stem_path()`
- `_replace_song_stem()`
- `_persist_generated_stems()`
- `_persist_stems()` (wrapper)
- `STEMS_DIR` module-level variable

- [ ] **Step 4: Update `_build_stem_display_name`**

```python
def _build_stem_display_name(stem_key: str, source_type: str) -> str:
    return stem_key.replace("_", " ").title()
```

- [ ] **Step 5: Update `_serialize_song_stem`**

New SELECT column order (used consistently in all queries going forward):
`id(0), stem_key(1), mime_type(2), duration(3), source_type(4), display_name(5), description(6), version_label(7), generation_id(8), uploaded_by_name(9), created_by_name(10), created_at(11), updated_at(12)`

```python
def _serialize_song_stem(row) -> dict:
    source_type = str(row[4] or "system")
    display_name = str(row[5]) if row[5] else _build_stem_display_name(str(row[1]), source_type)
    return {
        "id": int(row[0]),
        "stem_key": str(row[1]),
        "mime_type": str(row[2]) if row[2] else "audio/wav",
        "duration": row[3],
        "source_type": source_type,
        "display_name": display_name,
        "description": row[6],
        "version_label": str(row[7]) if row[7] else "legacy",
        "generation_id": row[8],
        "uploaded_by_name": row[9],
        "created_by_name": row[10],
        "created_at": row[11],
        "updated_at": row[12],
    }
```

Note: `_serialize_song_stem` is now sync (no `async`).

- [ ] **Step 6: Update `_load_song_stems` and `_load_active_song_stem`**

```python
_STEM_SELECT = """
    SELECT id, stem_key, mime_type, duration, source_type, display_name, description,
           version_label, generation_id, uploaded_by_name, created_by_name, created_at, updated_at
    FROM song_stems
"""

async def _load_song_stems(song_id: int) -> list[dict]:
    rs = await execute(
        _STEM_SELECT + "WHERE song_id = ? ORDER BY created_at ASC, id ASC",
        [song_id],
    )
    return [_serialize_song_stem(row) for row in rs.rows]


async def _load_stem_by_id(stem_id: int) -> dict | None:
    rs = await execute(
        _STEM_SELECT + "WHERE id = ? LIMIT 1",
        [stem_id],
    )
    if not rs.rows:
        return None
    return _serialize_song_stem(rs.rows[0])


async def _load_latest_stem_for_key(song_id: int, stem_key: str) -> dict | None:
    """Returns the most recently created stem for a given key."""
    rs = await execute(
        _STEM_SELECT + "WHERE song_id = ? AND stem_key = ? ORDER BY created_at DESC, id DESC LIMIT 1",
        [song_id, stem_key],
    )
    if not rs.rows:
        return None
    return _serialize_song_stem(rs.rows[0])
```

Replace `_load_active_song_stem` calls throughout `main.py` with `_load_latest_stem_for_key`.

- [ ] **Step 7: Add `_insert_stem_blob`**

```python
async def _insert_stem_blob(
    song_id: int,
    *,
    stem_key: str,
    audio_data: bytes,
    mime_type: str,
    duration: float | None,
    source_type: str,
    display_name: str,
    description: str | None = None,
    version_label: str,
    generation_id: str,
    created_by_user_id: int | None = None,
    created_by_name: str | None = None,
    uploaded_by_name: str | None = None,
) -> int:
    rs = await execute(
        """
        INSERT INTO song_stems (
            song_id, stem_key, audio_blob, mime_type, duration, source_type,
            display_name, description, version_label, generation_id,
            created_by_user_id, created_by_name, uploaded_by_name
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        RETURNING id
        """,
        [
            song_id, stem_key, audio_data, mime_type, duration, source_type,
            display_name, description, version_label, generation_id,
            created_by_user_id, created_by_name, uploaded_by_name,
        ],
    )
    return int(rs.rows[0][0])
```

- [ ] **Step 8: Add `_persist_generated_stems_blobs`**

```python
async def _persist_generated_stems_blobs(
    song_id: int,
    stems: list[StemResult],
    *,
    actor_user: dict,
    version_label: str | None = None,
) -> str:
    """INSERT all stems as new rows (additive). Returns the generation_id."""
    import uuid as _uuid
    gen_id = str(_uuid.uuid4())
    label = version_label or _build_version_label("gen")
    for stem in stems:
        display_name = _build_stem_display_name(stem.stem_key, "system")
        await _insert_stem_blob(
            song_id,
            stem_key=stem.stem_key,
            audio_data=stem.audio_data,
            mime_type=stem.mime_type or "audio/wav",
            duration=stem.duration,
            source_type="system",
            display_name=display_name,
            version_label=label,
            generation_id=gen_id,
            created_by_user_id=int(actor_user["id"]),
            created_by_name=str(actor_user["display_name"]),
        )
    return gen_id
```

- [ ] **Step 9: Run the new tests**

```bash
cd /Users/wojciechgula/Projects/DeChord/backend
uv run pytest tests/test_api.py::test_stem_generation_is_additive tests/test_api.py::test_stem_audio_endpoint_returns_blob tests/test_api.py::test_stem_audio_endpoint_legacy_row_returns_404 -v
```
Expected: the additive test may still fail until Task 5 wires up the generate endpoint. The helper unit logic should pass.

- [ ] **Step 10: Commit**

```bash
cd /Users/wojciechgula/Projects/DeChord/backend && cd ..
git add backend/app/main.py
git commit -m "$(cat <<'EOF'
feat: replace stem DB helpers with blob-aware _insert_stem_blob and _persist_generated_stems_blobs

docs/plans/2026-03-13-stem-blob-storage-implementation.md task: Replace stem DB helpers with blob-aware versions | opencode | gpt-5.1-codex-max

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Chunk 4: Endpoints & Activity Feed

### Task 4b: Audit and remove all `relative_path` access sites in `main.py` and `test_api.py`

**Files:**
- Modify: `backend/app/main.py`
- Modify: `backend/tests/test_api.py`

**Context:** There are ~20 `relative_path` access sites in `main.py` beyond the ones already removed in Task 4. Run the audit before implementing anything to find them all.

- [ ] **Step 1: Enumerate all remaining sites**

```bash
grep -n 'relative_path' backend/app/main.py
```

Key sites to address (in addition to those removed in Task 4):

| Line range | Site | Action |
|---|---|---|
| ~757 | `SELECT ... relative_path ... FROM song_stems` (user upload serve) | Replace SELECT with blob-based SELECT; serve via `_load_stem_audio_blob` |
| ~830 | `stems_by_key = {stem["stem_key"]: Path(stem["relative_path"]) ...}` | Covered in Task 5 |
| ~955 | `stem.relative_path` in another stem-processing context | Replace with `stem.audio_data` |
| ~981 | `Path(drums_stem.relative_path)` | Replace with temp-file write from blob |
| ~1764 | `relative_path=str(stored_path)` in user upload handler | Replace with `audio_blob=stored_bytes`, remove path arg |
| ~1816–1828 | `SELECT ... relative_path ... FROM song_stems` + `FileResponse(path)` | Replace with streaming from blob |
| ~1858–1868 | `SELECT stem_key, relative_path, ...` + `StemResult(relative_path=row[1], ...)` | Update StemResult init |
| ~2011 | `SELECT relative_path, mime_type` | Replace with blob-based endpoint |

- [ ] **Step 2: Fix user stem upload handler (~line 1764)**

Find the handler that stores an uploaded stem file to disk (`stored_path`) and inserts `relative_path`. Replace disk write with blob:

```python
# Before:
stored_path = STEMS_DIR / str(song_id) / "user" / filename
stored_path.parent.mkdir(parents=True, exist_ok=True)
stored_path.write_bytes(audio_bytes)
await _replace_song_stem(song_id, stem_key=stem_key, relative_path=str(stored_path), ...)

# After:
stem_id = await _insert_stem_blob(
    song_id,
    stem_key=stem_key,
    audio_data=audio_bytes,
    mime_type=mime_type,
    duration=duration,
    source_type="user",
    display_name=display_name,
    version_label=_build_version_label("user"),
    generation_id=str(uuid.uuid4()),
    created_by_user_id=current_user["id"],
    created_by_name=current_user["display_name"],
    uploaded_by_name=current_user["display_name"],
)
```

- [ ] **Step 3: Fix individual stem serve endpoint (~line 1816)**

Find the endpoint that serves a single stem by `stem_key`. Replace:

```python
# Before:
rs = await execute("SELECT s.title, ss.relative_path, ss.mime_type FROM ...")
path = Path(relative_path)
return FileResponse(path, media_type=mime_type)

# After:
stem = await _load_latest_stem_for_key(song_id, stem_key)
if stem is None:
    raise HTTPException(404, "Stem not found.")
audio_blob = await _load_stem_audio_blob(int(stem["id"]))
if not audio_blob:
    raise HTTPException(404, "Stem audio not available — legacy row.")
from fastapi.responses import Response
return Response(content=audio_blob, media_type=stem["mime_type"] or "audio/wav")
```

- [ ] **Step 4: Fix any remaining `StemResult(relative_path=...)` construction sites (~line 1858)**

These are in code that rebuilds `StemResult` objects from DB rows. Replace:
```python
# Before:
StemResult(stem_key=row[0], relative_path=row[1], mime_type=row[2], duration=row[3])

# After (load blob separately or pass audio_data=b""):
# Note: if this code path is unused after the refactor, remove it entirely.
```

- [ ] **Step 5: Fix `test_api.py` — update all `StemResult(relative_path=...)` in test fakes**

All test monkeypatches that construct `StemResult` with `relative_path=str(some_path)` must change to `audio_data=some_path.read_bytes()`. Find and update:

```bash
grep -n 'relative_path' backend/tests/test_api.py | head -50
```

Pattern:
```python
# Before:
StemResult(stem_key="bass", relative_path=str(bass), mime_type="audio/x-wav")

# After:
StemResult(stem_key="bass", audio_data=bass.read_bytes(), mime_type="audio/wav")
```

- [ ] **Step 6: Fix `test_api.py` — update assertions that read `stem["relative_path"]`**

Find tests that assert on `stem["relative_path"]` or call `Path(stem["relative_path"]).read_bytes()`:

```bash
grep -n '"relative_path"' backend/tests/test_api.py
```

Replace with blob-based assertions. Pattern:
```python
# Before:
assert first_stem["relative_path"] != second_stem["relative_path"]
assert Path(first_stem["relative_path"]).read_bytes() == b"first-bass"

# After:
assert first_stem["id"] != second_stem["id"]
assert client.get(f"/api/stems/{first_stem['id']}/audio").content == b"first-bass"
```

- [ ] **Step 7: Fix `test_api.py` — update raw SQL inserts that reference `relative_path`**

Tests that do `INSERT INTO song_stems (... relative_path ...)` directly must be updated. Since `relative_path` is now nullable, change to insert `NULL` or remove the column from the INSERT:
```python
# Before:
"INSERT INTO song_stems (song_id, stem_key, relative_path, mime_type, ...) VALUES (?, ?, ?, ?, ...)"

# After:
"INSERT INTO song_stems (song_id, stem_key, audio_blob, mime_type, ...) VALUES (?, ?, X'', ?, ...)"
```

- [ ] **Step 8: Run full test suite and fix any remaining failures**

```bash
cd /Users/wojciechgula/Projects/DeChord/backend
uv run pytest tests/test_api.py -v --tb=short 2>&1 | tail -60
```

- [ ] **Step 9: Commit**

```bash
cd /Users/wojciechgula/Projects/DeChord
git add backend/app/main.py backend/tests/test_api.py
git commit -m "$(cat <<'EOF'
feat: remove all relative_path access sites from main.py and test_api.py

docs/plans/2026-03-13-stem-blob-storage-implementation.md task: Audit and remove all relative_path access sites | opencode | gpt-5.1-codex-max

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: Update generate endpoint + `_regenerate_song_tabs`

**Files:**
- Modify: `backend/app/main.py`

**Context:** The stem generation route calls `split_to_stems` and then persists. Currently it writes to `STEMS_DIR` and calls `_persist_stems`. Update to pass a tmpdir to `split_to_stems`, call `_persist_generated_stems_blobs`, fire `stem_generated` activity. `_regenerate_song_tabs` builds `stems_by_key` from `stem["relative_path"]` — replace with blob→tmpfile pattern.

- [ ] **Step 1: Find the stem generate route**

```bash
grep -n "stems/generate\|split_to_stems\|_persist_stems\|_persist_generated" backend/app/main.py
```

- [ ] **Step 2: Update the generate route**

Replace the body that calls `split_to_stems` + `_persist_stems`. New pattern (adapt to actual route signature):

```python
import tempfile as _tempfile

# Inside the generate route handler:
tmp_dir = Path(_tempfile.mkdtemp(prefix=f"dechord-sep-{song_id}-"))
try:
    stems = split_to_stems(
        audio_path=str(audio_path),
        output_dir=tmp_dir,
        on_progress=on_progress,
    )
finally:
    import shutil as _shutil
    _shutil.rmtree(tmp_dir, ignore_errors=True)

gen_id = await _persist_generated_stems_blobs(
    song_id, stems, actor_user=current_user
)

stem_keys = ", ".join(sorted({s.stem_key for s in stems}))
await _record_song_project_activity(
    song_id,
    actor_user=current_user,
    event_type="stem_generated",
    message=f"{current_user['display_name']} generated stems for {song_title} ({stem_keys})",
)
```

- [ ] **Step 3: Update `_regenerate_song_tabs` to use blobs**

The function currently does:
```python
stems_by_key = {str(stem["stem_key"]): Path(str(stem["relative_path"])) for stem in stems}
```

Replace with a temp-file pattern:

```python
async def _regenerate_song_tabs(song_id: int, source_stem_key: str) -> dict:
    import tempfile as _tempfile, shutil as _shutil
    stems = await _load_song_stems(song_id)

    # Write blobs to temp files for pipeline processing
    tmp_dir = Path(_tempfile.mkdtemp(prefix=f"dechord-tabs-{song_id}-"))
    try:
        stems_by_key: dict[str, Path] = {}
        for stem in stems:
            # Use latest stem per key (stems are ordered ASC, so last wins)
            stem_key = str(stem["stem_key"])
            if stem["id"] > (stems_by_key.get(stem_key + "_id", -1)):  # track latest by id
                pass
        # Rebuild: take the latest stem per key
        latest: dict[str, dict] = {}
        for stem in stems:
            key = str(stem["stem_key"])
            if key not in latest or int(stem["id"]) > int(latest[key]["id"]):
                latest[key] = stem

        for stem_key, stem in latest.items():
            audio_blob = await _load_stem_audio_blob(int(stem["id"]))
            if not audio_blob:
                continue
            p = tmp_dir / f"{stem_key}.wav"
            p.write_bytes(audio_blob)
            stems_by_key[stem_key] = p

        if source_stem_key not in stems_by_key:
            raise HTTPException(404, "Requested source stem not found.")
        drums_path = stems_by_key.get("drums")
        if drums_path is None:
            raise HTTPException(422, "Drums stem missing; cannot build rhythm grid.")

        analysis_stems = dict(stems_by_key)
        analysis_stems["bass"] = stems_by_key[source_stem_key]
        analysis_output_dir = tmp_dir / "analysis"
        analysis_output_dir.mkdir()

        analysis_stem_result = build_bass_analysis_stem(
            stems=analysis_stems,
            output_dir=analysis_output_dir,
            analysis_config=_get_uploaded_stems_analysis_config("standard"),
            source_audio_path=None,
        )
        # Write audio_data bytes to temp file for tab_pipeline
        analysis_wav_path = tmp_dir / "bass_analysis.wav"
        analysis_wav_path.write_bytes(analysis_stem_result.audio_data)

        tab_result = tab_pipeline.run(
            analysis_wav_path,
            drums_path,
            bpm_hint=None,
            time_signature=(4, 4),
            subdivision=16,
            max_fret=24,
            sync_every_bars=8,
            tab_generation_quality_mode="standard",
            onset_recovery=None,
        )
        # ... rest of function (persist midi/tab) unchanged ...
    finally:
        _shutil.rmtree(tmp_dir, ignore_errors=True)
```

Add helper to load raw blob:
```python
async def _load_stem_audio_blob(stem_id: int) -> bytes | None:
    rs = await execute("SELECT audio_blob FROM song_stems WHERE id = ?", [stem_id])
    if not rs.rows:
        return None
    return bytes(rs.rows[0][0]) if rs.rows[0][0] else None
```

- [ ] **Step 4: Run stem generation tests**

```bash
cd /Users/wojciechgula/Projects/DeChord/backend
uv run pytest tests/test_api.py::test_stem_generation_is_additive tests/test_api.py::test_stem_audio_endpoint_returns_blob -v
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/wojciechgula/Projects/DeChord
git add backend/app/main.py
git commit -m "$(cat <<'EOF'
feat: update stem generate route and _regenerate_song_tabs to use blob storage

docs/plans/2026-03-13-stem-blob-storage-implementation.md task: Update generate endpoint + _regenerate_song_tabs | opencode | gpt-5.1-codex-max

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: New endpoints — audio serve, PATCH, DELETE

**Files:**
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_api.py`

**Context:** Three new endpoints plus update to existing download endpoint.

- [ ] **Step 1: Write failing tests**

Add to `backend/tests/test_api.py`:

```python
def _upload_song_with_stem(client, monkeypatch, main, fake_audio=b"stem-bytes"):
    """Helper: upload song, fake stem generation, return (song_id, stem_id)."""
    from app.stems import StemResult
    resp = client.post(
        "/api/songs",
        files={"file": ("s.mp3", b"\xff\xfb\x90\x00" * 50, "audio/mpeg")},
    )
    song_id = resp.json()["id"]
    monkeypatch.setattr(main, "split_to_stems", lambda *a, **k: [
        StemResult(stem_key="bass", audio_data=fake_audio, mime_type="audio/wav", duration=2.5)
    ])
    client.post(f"/api/songs/{song_id}/stems/generate")
    stems = client.get(f"/api/songs/{song_id}/stems").json()
    stem_id = stems[0]["id"]
    return song_id, stem_id


def test_patch_stem_renames_and_fires_activity(tmp_path, monkeypatch):
    client = _build_client(tmp_path, monkeypatch)
    import app.main as main
    song_id, stem_id = _upload_song_with_stem(client, monkeypatch, main)

    resp = client.patch(f"/api/stems/{stem_id}", json={"display_name": "Clean Bass"})
    assert resp.status_code == 200
    assert resp.json()["display_name"] == "Clean Bass"

    activity = client.get(f"/api/projects/1/activity").json()
    messages = [e["message"] for e in activity.get("activity", [])]
    assert any("Clean Bass" in m for m in messages), f"No rename event found in: {messages}"


def test_patch_stem_description_fires_activity(tmp_path, monkeypatch):
    client = _build_client(tmp_path, monkeypatch)
    import app.main as main
    song_id, stem_id = _upload_song_with_stem(client, monkeypatch, main)

    resp = client.patch(f"/api/stems/{stem_id}", json={"description": "Recorded on Fender Jazz"})
    assert resp.status_code == 200
    assert resp.json()["description"] == "Recorded on Fender Jazz"

    activity = client.get(f"/api/projects/1/activity").json()
    messages = [e["message"] for e in activity.get("activity", [])]
    assert any("description" in m.lower() for m in messages)


def test_delete_stem_removes_row_and_fires_activity(tmp_path, monkeypatch):
    client = _build_client(tmp_path, monkeypatch)
    import app.main as main
    song_id, stem_id = _upload_song_with_stem(client, monkeypatch, main)

    resp = client.delete(f"/api/stems/{stem_id}")
    assert resp.status_code == 204

    # Stem is gone
    audio_resp = client.get(f"/api/stems/{stem_id}/audio")
    assert audio_resp.status_code == 404

    activity = client.get(f"/api/projects/1/activity").json()
    messages = [e["message"] for e in activity.get("activity", [])]
    assert any("deleted" in m.lower() for m in messages)


def test_delete_stem_does_not_remove_other_stems(tmp_path, monkeypatch):
    """Deleting one stem must not cascade to other stems of the same key."""
    client = _build_client(tmp_path, monkeypatch)
    import app.main as main
    from app.stems import StemResult

    resp = client.post("/api/songs", files={"file": ("s.mp3", b"\xff\xfb\x90\x00"*50, "audio/mpeg")})
    song_id = resp.json()["id"]

    # Two generation runs → two bass stems
    monkeypatch.setattr(main, "split_to_stems", lambda *a, **k: [
        StemResult(stem_key="bass", audio_data=b"v1", mime_type="audio/wav")
    ])
    client.post(f"/api/songs/{song_id}/stems/generate")
    client.post(f"/api/songs/{song_id}/stems/generate")

    stems = client.get(f"/api/songs/{song_id}/stems").json()
    assert len(stems) == 2
    stem_id_to_delete = stems[0]["id"]

    client.delete(f"/api/stems/{stem_id_to_delete}")
    remaining = client.get(f"/api/songs/{song_id}/stems").json()
    assert len(remaining) == 1
    assert remaining[0]["id"] != stem_id_to_delete


def test_stems_download_zip_skips_legacy_blobs(tmp_path, monkeypatch):
    """Download zip must skip stems with empty audio_blob."""
    import asyncio
    client = _build_client(tmp_path, monkeypatch)
    import app.db as db_mod

    async def insert_legacy_stem():
        rs = await db_mod.execute("SELECT id FROM songs LIMIT 1")
        if not rs.rows:
            await db_mod.execute(
                "INSERT INTO songs (user_id, title, audio_blob) SELECT id, 'S', X'' FROM users LIMIT 1"
            )
            rs = await db_mod.execute("SELECT id FROM songs LIMIT 1")
        song_id = int(rs.rows[0][0])
        await db_mod.execute(
            "INSERT INTO song_stems (song_id, stem_key, audio_blob, mime_type, source_type, display_name, version_label) "
            "VALUES (?, 'bass', X'', 'audio/wav', 'system', 'Bass', 'legacy')",
            [song_id],
        )
        return song_id

    song_id = asyncio.run(insert_legacy_stem())
    resp = client.get(f"/api/songs/{song_id}/stems/download")
    # Either 404 (all stems empty) or 200 with an empty zip — both acceptable
    assert resp.status_code in (200, 404)
    if resp.status_code == 200:
        import io, zipfile
        with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
            assert z.namelist() == []
```

- [ ] **Step 2: Run to verify they fail**

```bash
cd /Users/wojciechgula/Projects/DeChord/backend
uv run pytest tests/test_api.py::test_patch_stem_renames_and_fires_activity tests/test_api.py::test_delete_stem_removes_row_and_fires_activity -v
```
Expected: FAIL (endpoints don't exist)

- [ ] **Step 3: Add `GET /api/stems/{stem_id}/audio`**

```python
@app.get("/api/stems/{stem_id}/audio")
async def get_stem_audio(stem_id: int):
    rs = await execute(
        "SELECT audio_blob, mime_type FROM song_stems WHERE id = ?", [stem_id]
    )
    if not rs.rows:
        raise HTTPException(404, "Stem not found.")
    audio_blob = bytes(rs.rows[0][0]) if rs.rows[0][0] else b""
    if not audio_blob:
        raise HTTPException(
            404,
            "Stem audio not available — this stem was stored on disk before the database migration.",
        )
    mime_type = str(rs.rows[0][1]) if rs.rows[0][1] else "audio/wav"
    from fastapi.responses import Response
    return Response(content=audio_blob, media_type=mime_type)
```

- [ ] **Step 4: Add `PATCH /api/stems/{stem_id}`**

```python
class StemUpdateRequest(BaseModel):
    display_name: str | None = None
    description: str | None = None

@app.patch("/api/stems/{stem_id}")
async def patch_stem(stem_id: int, body: StemUpdateRequest, user_id: int = Depends(get_current_user_id)):
    stem = await _load_stem_by_id(stem_id)
    if stem is None:
        raise HTTPException(404, "Stem not found.")
    current_user = await get_user_by_id(user_id)

    updates: dict = {}
    if body.display_name is not None:
        updates["display_name"] = body.display_name
    if body.description is not None:
        updates["description"] = body.description
    if not updates:
        return stem

    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [stem_id]
    await execute(
        f"UPDATE song_stems SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        values,
    )

    # Fire activity event
    old_name = stem["display_name"]
    new_name = updates.get("display_name", old_name)
    if "display_name" in updates and new_name != old_name:
        msg = f"{current_user['display_name']} renamed stem '{old_name}' → '{new_name}'"
    else:
        msg = f"{current_user['display_name']} updated description of stem '{new_name}'"

    # Get song context for activity
    rs = await execute("SELECT song_id FROM song_stems WHERE id = ?", [stem_id])
    if rs.rows:
        await _record_song_project_activity(
            int(rs.rows[0][0]),
            actor_user=current_user,
            event_type="stem_updated",
            message=msg,
        )

    return await _load_stem_by_id(stem_id)
```

- [ ] **Step 5: Add `DELETE /api/stems/{stem_id}`**

```python
@app.delete("/api/stems/{stem_id}", status_code=204)
async def delete_stem(stem_id: int, user_id: int = Depends(get_current_user_id)):
    stem = await _load_stem_by_id(stem_id)
    if stem is None:
        raise HTTPException(404, "Stem not found.")
    current_user = await get_user_by_id(user_id)
    display_name = stem["display_name"]

    rs = await execute("SELECT song_id FROM song_stems WHERE id = ?", [stem_id])
    song_id = int(rs.rows[0][0]) if rs.rows else None

    await execute("DELETE FROM song_stems WHERE id = ?", [stem_id])

    if song_id:
        await _record_song_project_activity(
            song_id,
            actor_user=current_user,
            event_type="stem_deleted",
            message=f"{current_user['display_name']} deleted stem '{display_name}'",
        )
```

- [ ] **Step 6: Update `GET /api/songs/{song_id}/stems/download`**

Find the existing download handler and replace the zip-building logic:

```python
stems = await _load_song_stems(song_id)

# Load blobs and build zip input
zip_stems: list[tuple[str, bytes, str]] = []
for stem in stems:
    blob = await _load_stem_audio_blob(int(stem["id"]))
    if blob:
        zip_stems.append((str(stem["stem_key"]), blob, str(stem["mime_type"] or "audio/wav")))

if not zip_stems:
    raise HTTPException(404, "No audio data available for these stems.")

song_row = await _load_song_row(song_id)
song_title = song_row["title"] if song_row else "song"
archive_bytes, archive_name = build_stems_zip(song_title, zip_stems)
```

- [ ] **Step 7: Run all new tests**

```bash
cd /Users/wojciechgula/Projects/DeChord/backend
uv run pytest tests/test_api.py -k "stem" -v
```
Expected: all stem-related tests PASS

- [ ] **Step 8: Run the full test suite**

```bash
cd /Users/wojciechgula/Projects/DeChord/backend
uv run pytest tests/ -v --tb=short 2>&1 | tail -40
```
Fix any failures before committing.

- [ ] **Step 9: Commit**

```bash
cd /Users/wojciechgula/Projects/DeChord
git add backend/app/main.py
git commit -m "$(cat <<'EOF'
feat: add GET /api/stems/{id}/audio, PATCH, DELETE endpoints with activity events

docs/plans/2026-03-13-stem-blob-storage-implementation.md task: New endpoints — audio serve, PATCH, DELETE | opencode | gpt-5.1-codex-max

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Chunk 5: Portability Rule + Verification

### Task 7: Add portability rule to `CLAUDE.md`

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Add rule to `<section id="architecture">`**

In `CLAUDE.md`, inside `<section id="architecture">`, add as the last `<rule>`:

```xml
<rule>Never persist binary assets (audio, stems, MIDI, tabs) to the local filesystem. All blobs must be stored in LibSQL. Temporary files during processing are allowed only in OS temp dirs and must be deleted immediately after reading into memory.</rule>
```

- [ ] **Step 2: Commit**

```bash
cd /Users/wojciechgula/Projects/DeChord
git add CLAUDE.md
git commit -m "$(cat <<'EOF'
docs: add filesystem-free portability rule to CLAUDE.md architecture section

docs/plans/2026-03-13-stem-blob-storage-implementation.md task: Add portability rule to CLAUDE.md | opencode | gpt-5.1-codex-max

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

### Task 8: Final verification

- [ ] **Step 1: Reset and run full test suite**

```bash
cd /Users/wojciechgula/Projects/DeChord
make reset 2>/dev/null || true
cd backend
uv run pytest tests/ -v --tb=short 2>&1 | tail -60
```
Expected: all tests pass (or only pre-existing failures)

- [ ] **Step 2: Verify no filesystem stem writes remain**

```bash
grep -rn "STEMS_DIR\|relative_path.*wav\|stem_path.*write\|FileResponse.*stem" backend/app/main.py backend/app/stems.py
```
Expected: zero matches (only comments if any)

- [ ] **Step 3: Verify `relative_path` is not in API responses**

```bash
grep -n '"relative_path"' backend/app/main.py
```
Expected: zero matches

- [ ] **Step 4: Mark plan complete and commit**

```bash
cd /Users/wojciechgula/Projects/DeChord
git add docs/plans/2026-03-13-stem-blob-storage-implementation.md
git commit -m "$(cat <<'EOF'
docs: mark stem blob storage plan complete after full verification

docs/plans/2026-03-13-stem-blob-storage-implementation.md task: Final verification | opencode | gpt-5.1-codex-max

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```
