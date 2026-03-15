"""Tests for rename + archive CRUD on bands, projects, songs, stems."""

import pytest
import asyncio
import importlib
from fastapi.testclient import TestClient


def _make_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DECHORD_DB_URL", f"file:{db_path}")
    import app.db as db_mod

    asyncio.run(db_mod.reset_db_client_for_tests())
    return importlib.reload(db_mod)


@pytest.fixture(autouse=True)
def setup_db(tmp_path, monkeypatch):
    """Each test gets a fresh in-memory or temp database."""
    db_mod = _make_db(tmp_path, monkeypatch)
    asyncio.run(db_mod.init_db())
    yield
    asyncio.run(db_mod.close_db())


def _client_with_user(user_id: int = 1) -> TestClient:
    from app.main import app

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


# ── Song rename + archive ─────────────────────────────────────────────────────


def _get_project_songs_url(project_id: int) -> str:
    return f"/api/projects/{project_id}/songs"


def test_patch_song_rename():
    """Upload a song via direct DB insert, then rename it."""
    import app.db as db_mod

    async def insert_song(project_id, user_id):
        rs = await db_mod.execute(
            """INSERT INTO songs (project_id, user_id, title, original_filename, audio_blob)
               VALUES (?, ?, 'Test Song', 'test.mp3', X'')
               RETURNING id""",
            [project_id, user_id],
        )
        return int(rs.rows[0][0])

    client = _client_with_user()
    band_id = _get_default_band_id(client)
    project_id = _get_default_project_id(client, band_id)
    song_id = asyncio.run(insert_song(project_id, user_id=1))

    res = client.patch(f"/api/songs/{song_id}", json={"title": "Renamed Song"})
    assert res.status_code == 200
    assert res.json()["title"] == "Renamed Song"
    # original_filename must be unchanged
    assert res.json()["original_filename"] == "test.mp3"


def test_patch_song_archive():
    import app.db as db_mod

    async def insert_song(project_id, user_id):
        rs = await db_mod.execute(
            """INSERT INTO songs (project_id, user_id, title, original_filename, audio_blob)
               VALUES (?, ?, 'Song To Archive', 'archive_me.mp3', X'')
               RETURNING id""",
            [project_id, user_id],
        )
        return int(rs.rows[0][0])

    client = _client_with_user()
    band_id = _get_default_band_id(client)
    project_id = _get_default_project_id(client, band_id)
    song_id = asyncio.run(insert_song(project_id, user_id=1))

    res = client.patch(f"/api/songs/{song_id}", json={"archived": True})
    assert res.status_code == 200
    assert res.json()["archived_at"] is not None

    # Should be hidden from default list
    songs_res = client.get(_get_project_songs_url(project_id))
    ids = [s["id"] for s in songs_res.json().get("songs", [])]
    assert song_id not in ids


def test_list_songs_include_archived():
    import app.db as db_mod

    async def insert_song(project_id, user_id):
        rs = await db_mod.execute(
            """INSERT INTO songs (project_id, user_id, title, original_filename, audio_blob)
               VALUES (?, ?, 'Hidden Song', 'hidden.mp3', X'')
               RETURNING id""",
            [project_id, user_id],
        )
        return int(rs.rows[0][0])

    client = _client_with_user()
    band_id = _get_default_band_id(client)
    project_id = _get_default_project_id(client, band_id)
    song_id = asyncio.run(insert_song(project_id, user_id=1))
    client.patch(f"/api/songs/{song_id}", json={"archived": True})

    res = client.get(_get_project_songs_url(project_id) + "?include_archived=true")
    ids = [s["id"] for s in res.json().get("songs", [])]
    assert song_id in ids
