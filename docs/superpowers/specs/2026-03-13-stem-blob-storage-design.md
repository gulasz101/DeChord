# Stem Blob Storage & Management — Design Spec

**Date:** 2026-03-13
**Status:** Approved
**Scope:** Backend only — `db_schema.sql`, `stems.py`, `main.py`, `CLAUDE.md`

---

## Problem Statement

Stems are currently stored as `.wav` files on the local filesystem with `relative_path` recorded in `song_stems`. This breaks portability: moving the database to another host or container loses all stem audio. All other binary assets (songs, MIDI, tabs) are already stored as BLOBs in LibSQL. Stems must follow the same pattern.

Additionally, stem generation currently deletes and replaces existing stems (enforced via `UNIQUE(song_id, stem_key)`). This prevents users from keeping multiple revisions of the same stem type. Stem mutations (rename, describe, delete) are not recorded in the project activity feed.

---

## Goals

1. Store all stem audio as `BLOB` in LibSQL — no filesystem persistence.
2. Stem generation is always **additive** — new rows are INSERTed, existing rows are never deleted by automation.
3. Stems are deleted **only** by explicit user action via `DELETE /api/stems/{stem_id}`.
4. Users can rename (`display_name`) and describe (`description`) any stem (system- or user-generated).
5. Stem events (`stem_generated`, `stem_updated`, `stem_deleted`) appear in the project activity feed.
6. Portability rule codified in `CLAUDE.md`.

---

## Section 1: Database Schema Changes

### Migration Strategy

SQLite does not support `ALTER TABLE DROP CONSTRAINT` or `ALTER TABLE DROP COLUMN`. The `song_stems` table has `UNIQUE(song_id, stem_key)` and `relative_path TEXT NOT NULL` — both must change. The only correct approach is a **table-rebuild migration**:

```sql
-- Migration: stem_blob_storage (applied once via migration runner in db.py)

-- Step 1: create new table without UNIQUE(song_id, stem_key) and without relative_path NOT NULL
CREATE TABLE IF NOT EXISTS song_stems_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    song_id INTEGER NOT NULL,
    stem_key TEXT NOT NULL,
    relative_path TEXT,                          -- nullable; NULL for all new rows; kept for legacy read reference only
    audio_blob BLOB NOT NULL DEFAULT X'',        -- empty for migrated legacy rows; filled for new rows
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

-- Step 2: copy existing rows (audio_blob stays X'' for legacy rows)
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
FROM song_stems;

-- Step 3: swap
DROP TABLE song_stems;
ALTER TABLE song_stems_new RENAME TO song_stems;

-- Step 4: restore indexes
CREATE INDEX IF NOT EXISTS idx_song_stems_song_id ON song_stems(song_id);
CREATE INDEX IF NOT EXISTS idx_song_stems_generation_id ON song_stems(generation_id);
```

The migration runner in `db.py` checks for the presence of a `audio_blob` column before running — idempotent.

### Legacy rows

Existing rows have `audio_blob = X''` (empty). Any endpoint serving audio for a legacy row returns **404** with body `{"detail": "Stem audio not available — this stem was stored on disk before the database migration."}`.

---

## Section 2: `stems.py` — In-Memory Audio Pipeline

### `StemResult` dataclass

```python
@dataclass
class StemResult:
    stem_key: str
    audio_data: bytes       # replaces relative_path
    mime_type: str
    duration: float
```

### `BassAnalysisStemResult` dataclass

```python
@dataclass
class BassAnalysisStemResult:
    audio_data: bytes       # replaces path: Path
    sample_rate: int
    duration: float
```

Callers of `build_bass_analysis_stem()` that must be updated:
- `_get_bass_analysis_stem_for_transcription()` in `main.py` — currently calls `path.read_bytes()` after the call; update to use `.audio_data` directly.

### Pipeline changes

- `split_to_stems()` — Demucs / FFmpeg still write to `tempfile.NamedTemporaryFile` internally (Demucs requires disk I/O). After separation, each temp `.wav` is read into `bytes` via `_read_wav_to_bytes(path)` and the temp file deleted immediately before returning.
- `build_bass_analysis_stem()` — returns `BassAnalysisStemResult` with `audio_data: bytes` instead of a `Path`.
- `build_stems_zip(stems: list[tuple[str, bytes, str]])` — accepts `(stem_key, audio_data, mime_type)` tuples; no disk access.
- `_write_wav_mono` / `_read_wav_mono` — remain as internal helpers for in-pipeline temp-file operations only.

New helper:

```python
def _read_wav_to_bytes(path: Path) -> bytes:
    data = path.read_bytes()
    path.unlink(missing_ok=True)
    return data
```

---

## Section 3: `main.py` — API & DB Layer

### Symbols removed

| Symbol | Reason |
|--------|--------|
| `_replace_song_stem()` | Enforced DELETE+INSERT one-per-key |
| `_persist_generated_stems()` | Deleted existing system stems |
| `_is_user_uploaded_stem_path()` | Inspected filesystem path |
| `_build_stem_display_name(stem_key, relative_path, source_type)` | Takes `relative_path`; replaced with `_build_stem_display_name(stem_key, source_type)` |
| `STEMS_DIR` | No permanent filesystem stem storage |

### `_serialize_song_stem` changes

Remove `relative_path` from the serialized response. It was an internal implementation detail and must not be exposed. Frontend code that currently reads `stem.relative_path` for audio URL construction is out of scope for this task — the new audio URL is `GET /api/stems/{stem_id}/audio`.

### New DB helpers

**`_insert_stem_blob(...) -> int`** — pure INSERT, returns new stem id:

```python
async def _insert_stem_blob(
    song_id: int,
    stem_key: str,
    audio_data: bytes,
    mime_type: str,
    duration: float,
    source_type: str,
    display_name: str,
    description: str | None,
    version_label: str,
    generation_id: str,
    created_by_user_id: int,
    created_by_name: str,
) -> int
```

**`_load_song_stems(song_id)`** — returns all stems for a song (multiple per key allowed).

**`_load_stem_by_id(stem_id)`** — fetch single stem row by id.

### New/updated endpoints

#### `GET /api/stems/{stem_id}/audio`
- Fetches `audio_blob` from DB via `_load_stem_by_id`
- If `audio_blob` is empty (`len == 0`): return 404 with legacy message
- Returns `StreamingResponse` with `Content-Type` from `mime_type` column (default `audio/wav`)

#### `GET /api/songs/{song_id}/stems/{stem_key}/audio` (updated)
Existing endpoint used to read from `relative_path`. Updated to:
- Load all stems for `song_id` where `stem_key` matches (most recently created first)
- Serve the latest non-empty blob, or 404 if all empty

#### `GET /api/songs/{song_id}/stems/download` (updated)
- Load all stems for song via `_load_song_stems`
- Pass `[(stem.stem_key, stem.audio_blob, stem.mime_type)]` to `build_stems_zip()`
- Skip stems with empty blob (legacy); if all are empty, return 404

#### `PATCH /api/stems/{stem_id}`
- Body: `{ display_name?: str, description?: str }`
- Updates the stem row (`updated_at` bumped)
- Fires `stem_updated` activity event
  - If `display_name` changed: message = `"{actor} renamed stem '{old}' → '{new}' on {song_title}"`
  - If only `description` changed: message = `"{actor} updated description of stem '{display_name}' on {song_title}"`
- Returns updated stem metadata (no blob)

#### `DELETE /api/stems/{stem_id}`
- Explicit user action only; no automated job calls this
- Deletes the row
- Fires `stem_deleted` activity event: `"{actor} deleted stem '{display_name}' from {song_title}"`
- Returns `204 No Content`

### Updated: `_persist_generated_stems_blobs()`

Replaces `_persist_generated_stems()`:
- Iterates `list[StemResult]`
- Calls `_insert_stem_blob()` for each — **no deletes, no existence check**
- All stems in one batch share the same `generation_id` (UUID generated once per call)
- After all inserts, fires one `stem_generated` activity event:
  `"{actor} generated stems for {song_title} ({stem_keys joined})"`

---

## Section 4: Activity Feed Events

New `event_type` values (freeform TEXT in `project_activity_events`):

| event_type | Trigger | Message pattern |
|---|---|---|
| `stem_generated` | Stem separation batch complete | `"{actor} generated stems for {song_title} (bass, drums, vocals, other)"` |
| `stem_updated` | `PATCH /api/stems/{id}` | See PATCH spec above — rename vs description-only |
| `stem_deleted` | `DELETE /api/stems/{id}` | `"{actor} deleted stem '{display_name}' from {song_title}"` |

Existing `stem_upload` event type unchanged (fires on user-uploaded stems).

---

## Section 5: CLAUDE.md Portability Rule

Add to `<section id="architecture">`:

```xml
<rule>Never persist binary assets (audio, stems, MIDI, tabs) to the local filesystem. All blobs must be stored in LibSQL. Temporary files during processing are allowed only in OS temp dirs and must be deleted immediately after reading into memory.</rule>
```

---

## Out of Scope

- Frontend mixer/player UI
- Stem playback controls
- Frontend URL updates to use new `/api/stems/{stem_id}/audio` pattern (separate task)
- Stem selection for transcription pipeline (existing `source_stem_key` logic unchanged)
- User-uploaded stem endpoint changes beyond blob storage

---

## Testing Strategy (TDD)

All new DB helpers and endpoints covered with pytest before implementation:

1. `test_insert_stem_blob_additive` — two inserts for same `stem_key` on same song produce two rows (no UNIQUE violation)
2. `test_stem_audio_endpoint_returns_blob` — `GET /api/stems/{id}/audio` returns correct bytes and content-type
3. `test_stem_audio_endpoint_legacy_404` — `GET /api/stems/{id}/audio` on row with empty blob returns 404 with legacy message
4. `test_patch_stem_rename_fires_event` — rename updates `display_name` and fires `stem_updated` with rename message
5. `test_patch_stem_description_fires_event` — description-only update fires `stem_updated` with description message
6. `test_delete_stem_explicit` — DELETE removes row, fires `stem_deleted`, does not cascade to other stems of same key
7. `test_no_auto_delete_on_generation` — calling `_persist_generated_stems_blobs` twice for same stem_key produces four rows total (two batches × two stems)
8. `test_stems_zip_from_bytes` — zip builder works without filesystem, skips empty-blob stems
9. `test_generation_id_groups_batch` — all stems from one `_persist_generated_stems_blobs` call share `generation_id`
10. `test_download_endpoint_skips_legacy` — `/stems/download` excludes legacy (empty-blob) stems from zip
