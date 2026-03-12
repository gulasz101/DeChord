import importlib
import asyncio
import threading
import sys
import types
import io
import sqlite3
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


def _build_client(tmp_path: Path, monkeypatch):
    db_path = tmp_path / "api-test.db"
    monkeypatch.setenv("DECHORD_DB_URL", f"file:{db_path}")
    if "torch" not in sys.modules:

        class _FakeTorchTensor:
            pass

        sys.modules["torch"] = types.SimpleNamespace(
            Tensor=_FakeTorchTensor,
            backends=types.SimpleNamespace(
                mps=types.SimpleNamespace(is_available=lambda: False)
            ),
            cuda=types.SimpleNamespace(is_available=lambda: False),
        )

    import app.main as main_mod

    main = importlib.reload(main_mod)

    def immediate_submit(fn, *args, **kwargs):
        thread = threading.Thread(target=fn, args=args, kwargs=kwargs)
        thread.start()
        thread.join()

    from app.analysis import AnalysisResult, Chord

    def fake_analyze_audio(_audio_path: str):
        return AnalysisResult(
            key="C major",
            tempo=120,
            duration=4.0,
            chords=[
                Chord(start=0.0, end=2.0, label="C"),
                Chord(start=2.0, end=4.0, label="G"),
            ],
        )

    monkeypatch.setattr(main, "analyze_audio", fake_analyze_audio)
    monkeypatch.setattr(main.executor, "submit", immediate_submit)
    asyncio.run(main.init_db())

    client = TestClient(main.app)
    return client


def test_health(tmp_path, monkeypatch):
    client = _build_client(tmp_path, monkeypatch)
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_identity_resolve_creates_guest_user(tmp_path, monkeypatch):
    client = _build_client(tmp_path, monkeypatch)

    response = client.post(
        "/api/identity/resolve",
        json={"fingerprint_token": "fp-browser-123"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["user"]["id"] > 0
    assert payload["user"]["fingerprint_token"] == "fp-browser-123"
    assert payload["user"]["is_claimed"] is False
    assert isinstance(payload["user"]["display_name"], str)
    assert len(payload["user"]["display_name"]) > 0


def test_identity_resolve_bootstraps_truthful_default_band_access(
    tmp_path, monkeypatch
):
    client = _build_client(tmp_path, monkeypatch)
    import app.main as main

    created_band = client.post(
        "/api/bands",
        json={"name": f"Private Band {tmp_path.name}"},
    )
    assert created_band.status_code == 200

    resolved = client.post(
        "/api/identity/resolve",
        json={"fingerprint_token": f"fp-bootstrap-{tmp_path.name}"},
    )
    assert resolved.status_code == 200
    user_id = resolved.json()["user"]["id"]

    bands_response = client.get(
        "/api/bands",
        headers={"X-DeChord-User-Id": str(user_id)},
    )
    assert bands_response.status_code == 200
    assert bands_response.json() == {
        "bands": [
            {
                "id": 1,
                "name": "Default Band",
                "owner_user_id": 1,
                "created_at": bands_response.json()["bands"][0]["created_at"],
                "project_count": 1,
            }
        ]
    }

    members_response = client.get(
        "/api/bands/1/members",
        headers={"X-DeChord-User-Id": str(user_id)},
    )
    assert members_response.status_code == 200
    assert any(
        member["id"] == str(user_id) for member in members_response.json()["members"]
    )

    projects_response = client.get(
        "/api/bands/1/projects",
        headers={"X-DeChord-User-Id": str(user_id)},
    )
    assert projects_response.status_code == 200
    assert [project["name"] for project in projects_response.json()["projects"]] == [
        "Default Project"
    ]

    membership_rs = asyncio.run(
        main.execute(
            "SELECT role FROM band_memberships WHERE band_id = 1 AND user_id = ?",
            [user_id],
        )
    )
    assert [tuple(row) for row in membership_rs.rows] == [("member",)]


def test_identity_claim_sets_username_and_password_hash(tmp_path, monkeypatch):
    client = _build_client(tmp_path, monkeypatch)

    created = client.post(
        "/api/identity/resolve",
        json={"fingerprint_token": "fp-claim-1"},
    )
    assert created.status_code == 200
    user_id = created.json()["user"]["id"]

    claim = client.post(
        "/api/identity/claim",
        json={
            "user_id": user_id,
            "username": "bassbot",
            "password": "secret-pass",
        },
    )
    assert claim.status_code == 200
    claim_payload = claim.json()
    assert claim_payload["user"]["id"] == user_id
    assert claim_payload["user"]["is_claimed"] is True
    assert claim_payload["user"]["username"] == "bassbot"


def test_create_band_creates_owned_band_and_membership(tmp_path, monkeypatch):
    client = _build_client(tmp_path, monkeypatch)
    import app.main as main

    band_name = f"My Band {tmp_path.name}"

    response = client.post("/api/bands", json={"name": band_name})

    assert response.status_code == 200
    payload = response.json()
    assert payload["band"]["name"] == band_name

    membership_rs = asyncio.run(
        main.execute(
            """
            SELECT role
            FROM band_memberships
            WHERE band_id = ? AND user_id = 1
            """,
            [payload["band"]["id"]],
        )
    )
    assert membership_rs.rows[0][0] == "owner"


def test_create_band_uses_request_identity_for_owner_membership(tmp_path, monkeypatch):
    client = _build_client(tmp_path, monkeypatch)
    import app.main as main

    inserted_user = asyncio.run(
        main.execute(
            "INSERT INTO users (display_name, fingerprint_token) VALUES ('Alicja Band Owner', 'fp-band-owner') RETURNING id"
        )
    )
    user_id = int(inserted_user.rows[0][0])

    response = client.post(
        "/api/bands",
        json={"name": f"Request Owned {tmp_path.name}"},
        headers={"X-DeChord-User-Id": str(user_id)},
    )

    assert response.status_code == 200
    band_id = response.json()["band"]["id"]
    assert response.json()["band"]["owner_user_id"] == user_id

    membership_rs = asyncio.run(
        main.execute(
            "SELECT user_id, role FROM band_memberships WHERE band_id = ?",
            [band_id],
        )
    )
    assert [tuple(row) for row in membership_rs.rows] == [(user_id, "owner")]


def test_create_project_creates_project_under_selected_band(tmp_path, monkeypatch):
    client = _build_client(tmp_path, monkeypatch)
    import app.main as main

    band_name = f"My Band {tmp_path.name}"

    created_band = client.post("/api/bands", json={"name": band_name})
    band_id = created_band.json()["band"]["id"]

    response = client.post(
        f"/api/bands/{band_id}/projects",
        json={"name": "Album Prep", "description": "Spring set"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["project"]["band_id"] == band_id
    assert payload["project"]["name"] == "Album Prep"
    assert payload["project"]["description"] == "Spring set"

    project_rs = asyncio.run(
        main.execute(
            "SELECT band_id, name, description FROM projects WHERE id = ?",
            [payload["project"]["id"]],
        )
    )
    assert tuple(project_rs.rows[0]) == (band_id, "Album Prep", "Spring set")


def test_list_bands_projects_and_project_songs(tmp_path, monkeypatch):
    client = _build_client(tmp_path, monkeypatch)

    files = {"file": ("demo.mp3", b"audio-bytes", "audio/mpeg")}
    created = client.post(
        "/api/analyze", files=files, data={"process_mode": "analysis_only"}
    )
    assert created.status_code == 200
    created_song_id = created.json()["song_id"]

    bands_response = client.get("/api/bands")
    assert bands_response.status_code == 200
    bands = bands_response.json()["bands"]
    assert len(bands) >= 1
    band_id = bands[0]["id"]

    projects_response = client.get(f"/api/bands/{band_id}/projects")
    assert projects_response.status_code == 200
    projects = projects_response.json()["projects"]
    assert len(projects) >= 1
    project_id = projects[0]["id"]

    songs_response = client.get(f"/api/projects/{project_id}/songs")
    assert songs_response.status_code == 200
    songs = songs_response.json()["songs"]
    assert any(song["id"] == created_song_id for song in songs)


def test_band_members_and_project_unread_counts_are_backed_by_memberships_and_reads(
    tmp_path, monkeypatch
):
    client = _build_client(tmp_path, monkeypatch)
    import app.main as main

    band = client.post("/api/bands", json={"name": f"Band {tmp_path.name}"}).json()[
        "band"
    ]
    project = client.post(
        f"/api/bands/{band['id']}/projects",
        json={"name": "Collab", "description": ""},
    ).json()["project"]

    inserted_user = asyncio.run(
        main.execute(
            "INSERT INTO users (display_name, fingerprint_token) VALUES (?, 'fp-a') RETURNING id",
            [f"Alicja {tmp_path.name}"],
        )
    )
    user_id = int(inserted_user.rows[0][0])
    asyncio.run(
        main.execute(
            "INSERT INTO band_memberships (band_id, user_id, role) VALUES (?, ?, 'member')",
            [band["id"], user_id],
        )
    )

    members = client.get(
        f"/api/bands/{band['id']}/members", headers={"X-DeChord-User-Id": "1"}
    )
    assert members.status_code == 200
    assert [row["name"] for row in members.json()["members"]] == [
        "Wojtek",
        f"Alicja {tmp_path.name}",
    ]
    assert [row["presence_state"] for row in members.json()["members"]] == [
        "not_live",
        "not_live",
    ]

    song = client.post(
        "/api/analyze",
        files={"file": ("demo.mp3", b"audio-bytes", "audio/mpeg")},
        data={"process_mode": "analysis_only", "project_id": str(project["id"])},
        headers={"X-DeChord-User-Id": "1"},
    )
    assert song.status_code == 200

    note = client.post(
        f"/api/songs/{song.json()['song_id']}/notes",
        json={"type": "chord", "text": "Tighten verse", "chord_index": 0},
        headers={"X-DeChord-User-Id": "1"},
    )
    assert note.status_code == 200

    projects = client.get(
        f"/api/bands/{band['id']}/projects", headers={"X-DeChord-User-Id": str(user_id)}
    )
    assert projects.status_code == 200
    assert projects.json()["projects"][0]["unread_count"] == 2

    activity = client.get(
        f"/api/projects/{project['id']}/activity",
        headers={"X-DeChord-User-Id": str(user_id)},
    )
    assert activity.status_code == 200
    assert activity.json()["unread_count"] == 2

    marked = client.post(
        f"/api/projects/{project['id']}/activity/read",
        headers={"X-DeChord-User-Id": str(user_id)},
    )
    assert marked.status_code == 200
    assert marked.json() == {"project_id": project["id"], "unread_count": 0}


def test_project_activity_and_mark_read_use_acting_user_identity(tmp_path, monkeypatch):
    client = _build_client(tmp_path, monkeypatch)
    import app.main as main

    band = client.post("/api/bands", json={"name": f"Band {tmp_path.name}"}).json()[
        "band"
    ]
    project = client.post(
        f"/api/bands/{band['id']}/projects",
        json={"name": "Collab", "description": ""},
    ).json()["project"]

    inserted_user = asyncio.run(
        main.execute(
            "INSERT INTO users (display_name, fingerprint_token) VALUES (?, 'fp-a2') RETURNING id",
            [f"Alicja {tmp_path.name}"],
        )
    )
    user_id = int(inserted_user.rows[0][0])
    asyncio.run(
        main.execute(
            "INSERT INTO band_memberships (band_id, user_id, role) VALUES (?, ?, 'member')",
            [band["id"], user_id],
        )
    )

    created_song = client.post(
        "/api/analyze",
        files={"file": ("demo.mp3", b"audio-bytes", "audio/mpeg")},
        data={"process_mode": "analysis_only", "project_id": str(project["id"])},
        headers={"X-DeChord-User-Id": str(user_id)},
    )
    assert created_song.status_code == 200
    song_id = created_song.json()["song_id"]

    created = client.post(
        f"/api/songs/{song_id}/notes",
        json={"type": "chord", "text": "Tighten verse", "chord_index": 0},
        headers={"X-DeChord-User-Id": str(user_id)},
    )
    assert created.status_code == 200
    note_id = created.json()["id"]

    resolved = client.patch(
        f"/api/notes/{note_id}/resolve",
        json={"resolved": True},
        headers={"X-DeChord-User-Id": "1"},
    )
    assert resolved.status_code == 200

    unresolved = client.patch(
        f"/api/notes/{note_id}/resolve",
        json={"resolved": False},
        headers={"X-DeChord-User-Id": str(user_id)},
    )
    assert unresolved.status_code == 200

    stem_upload = client.post(
        f"/api/songs/{song_id}/stems/upload",
        data={"stem_key": "bass"},
        files={"file": ("bass.wav", b"bass-audio", "audio/wav")},
        headers={"X-DeChord-User-Id": str(user_id)},
    )
    assert stem_upload.status_code == 200

    feed = client.get(
        f"/api/projects/{project['id']}/activity", headers={"X-DeChord-User-Id": "1"}
    )
    assert feed.status_code == 200
    payload = feed.json()
    assert payload["unread_count"] == 4
    assert payload["presence_state"] == "not_live"
    assert payload["activity"][0]["author_name"] == f"Alicja {tmp_path.name}"
    assert {item["event_type"] for item in payload["activity"]} == {
        "song_created",
        "note_created",
        "note_resolved",
        "note_unresolved",
        "stem_uploaded",
    }
    assert [item["author_name"] for item in payload["activity"][:3]] == [
        f"Alicja {tmp_path.name}",
        f"Alicja {tmp_path.name}",
        "Wojtek",
    ]

    marked = client.post(
        f"/api/projects/{project['id']}/activity/read",
        headers={"X-DeChord-User-Id": "1"},
    )
    assert marked.status_code == 200
    assert marked.json()["unread_count"] == 0

    after_read = client.post(
        f"/api/songs/{song_id}/notes",
        json={"type": "time", "text": "Count in", "timestamp_sec": 1.0},
        headers={"X-DeChord-User-Id": str(user_id)},
    )
    assert after_read.status_code == 200

    latest_event_id = int(
        asyncio.run(
            main.execute(
                "SELECT MAX(id) FROM project_activity_events WHERE project_id = ?",
                [project["id"]],
            )
        ).rows[0][0]
    )
    asyncio.run(
        main.execute(
            "UPDATE project_activity_events SET created_at = '2001-01-01 00:00:00' WHERE id = ?",
            [latest_event_id],
        )
    )

    refreshed = client.get(
        f"/api/projects/{project['id']}/activity", headers={"X-DeChord-User-Id": "1"}
    )
    assert refreshed.status_code == 200
    assert refreshed.json()["unread_count"] == 1
    assert refreshed.json()["activity"][0]["author_name"] == f"Alicja {tmp_path.name}"


def test_collaboration_routes_reject_users_who_are_not_band_members(
    tmp_path, monkeypatch
):
    client = _build_client(tmp_path, monkeypatch)
    import app.main as main

    band = client.post("/api/bands", json={"name": f"Band {tmp_path.name}"}).json()[
        "band"
    ]
    project = client.post(
        f"/api/bands/{band['id']}/projects",
        json={"name": "Restricted", "description": ""},
    ).json()["project"]

    outsider = asyncio.run(
        main.execute(
            "INSERT INTO users (display_name, fingerprint_token) VALUES ('Outsider', 'fp-outsider') RETURNING id"
        )
    )
    outsider_id = int(outsider.rows[0][0])

    for method, path in (
        (client.get, f"/api/bands/{band['id']}/members"),
        (client.get, f"/api/bands/{band['id']}/projects"),
        (client.get, f"/api/projects/{project['id']}/activity"),
        (client.post, f"/api/projects/{project['id']}/activity/read"),
    ):
        response = method(path, headers={"X-DeChord-User-Id": str(outsider_id)})
        assert response.status_code == 403


def test_tab_from_demucs_stems_uses_request_identity_and_records_activity_when_creating_song(
    tmp_path, monkeypatch
):
    client = _build_client(tmp_path, monkeypatch)
    import app.main as main
    from app.services.alphatex_exporter import SyncPoint
    from app.services.rhythm_grid import Bar
    from app.services.tab_pipeline import TabPipelineResult

    band = client.post("/api/bands", json={"name": f"Band {tmp_path.name}"}).json()[
        "band"
    ]
    project = client.post(
        f"/api/bands/{band['id']}/projects",
        json={"name": "Demucs", "description": ""},
    ).json()["project"]

    inserted_user = asyncio.run(
        main.execute(
            "INSERT INTO users (display_name, fingerprint_token) VALUES ('Stem User', 'fp-stem-user') RETURNING id"
        )
    )
    user_id = int(inserted_user.rows[0][0])
    asyncio.run(
        main.execute(
            "INSERT INTO band_memberships (band_id, user_id, role) VALUES (?, ?, 'member')",
            [band["id"], user_id],
        )
    )

    def fake_run(*_args, **_kwargs):
        return TabPipelineResult(
            alphatex="\\tempo 120\n\\sync(0 0 0 0)",
            tempo_used=120.0,
            bars=[
                Bar(index=0, start_sec=0.0, end_sec=2.0, beats_sec=[0.0, 0.5, 1.0, 1.5])
            ],
            sync_points=[SyncPoint(bar_index=0, millisecond_offset=0)],
            midi_bytes=b"MThd\x00\x00\x00\x06",
            fingered_notes=[],
            debug_info={"rhythm_source": "madmom"},
        )

    monkeypatch.setattr(main.tab_pipeline, "run", fake_run)

    response = client.post(
        "/api/tab/from-demucs-stems",
        data={"project_id": str(project["id"]), "bpm": "120"},
        files={
            "bass": ("bass.wav", b"bass-bytes", "audio/wav"),
            "drums": ("drums.wav", b"drums-bytes", "audio/wav"),
        },
        headers={"X-DeChord-User-Id": str(user_id)},
    )

    assert response.status_code == 200
    song_id = response.json()["song_id"]

    song_rs = asyncio.run(
        main.execute("SELECT user_id, project_id FROM songs WHERE id = ?", [song_id])
    )
    assert tuple(song_rs.rows[0]) == (user_id, project["id"])

    activity = client.get(
        f"/api/projects/{project['id']}/activity", headers={"X-DeChord-User-Id": "1"}
    )
    assert activity.status_code == 200
    assert activity.json()["activity"][0]["event_type"] == "song_created"
    assert activity.json()["activity"][0]["author_name"] == "Stem User"


def test_project_activity_reads_reject_cross_project_event_pointers(
    tmp_path, monkeypatch
):
    client = _build_client(tmp_path, monkeypatch)
    import app.main as main

    band = client.post("/api/bands", json={"name": f"Band {tmp_path.name}"}).json()[
        "band"
    ]
    first_project = client.post(
        f"/api/bands/{band['id']}/projects",
        json={"name": "One", "description": ""},
    ).json()["project"]
    second_project = client.post(
        f"/api/bands/{band['id']}/projects",
        json={"name": "Two", "description": ""},
    ).json()["project"]

    second_project_event_id = int(
        asyncio.run(
            main.execute(
                """
                INSERT INTO project_activity_events (
                    project_id, actor_user_id, actor_name, actor_avatar, event_type, song_id, song_title, message
                ) VALUES (?, 1, 'Wojtek', 'W', 'song_created', NULL, NULL, 'made event')
                RETURNING id
                """,
                [second_project["id"]],
            )
        ).rows[0][0]
    )
    foreign_project_event_id = int(
        asyncio.run(
            main.execute(
                """
                INSERT INTO project_activity_events (
                    project_id, actor_user_id, actor_name, actor_avatar, event_type, song_id, song_title, message
                ) VALUES (?, 1, 'Wojtek', 'W', 'song_created', NULL, NULL, 'foreign event')
                RETURNING id
                """,
                [first_project["id"]],
            )
        ).rows[0][0]
    )
    assert foreign_project_event_id > second_project_event_id

    asyncio.run(
        main.execute(
            "INSERT INTO project_activity_reads (project_id, user_id, last_read_event_id) VALUES (?, 1, ?)",
            [second_project["id"], foreign_project_event_id],
        )
    )

    collaborator = asyncio.run(
        main.execute(
            "INSERT INTO users (display_name, fingerprint_token) VALUES ('Cursor User', 'fp-cursor-user') RETURNING id"
        )
    )
    collaborator_id = int(collaborator.rows[0][0])
    asyncio.run(
        main.execute(
            "INSERT INTO band_memberships (band_id, user_id, role) VALUES (?, ?, 'member')",
            [band["id"], collaborator_id],
        )
    )

    song = client.post(
        "/api/analyze",
        files={"file": ("demo.mp3", b"audio-bytes", "audio/mpeg")},
        data={"process_mode": "analysis_only", "project_id": str(second_project["id"])},
        headers={"X-DeChord-User-Id": str(collaborator_id)},
    )
    assert song.status_code == 200

    guarded = client.get(
        f"/api/projects/{second_project['id']}/activity",
        headers={"X-DeChord-User-Id": "1"},
    )
    assert guarded.status_code == 200
    assert guarded.json()["unread_count"] == 1


def test_outsider_write_routes_cannot_mutate_project_collaboration_state(
    tmp_path, monkeypatch
):
    client = _build_client(tmp_path, monkeypatch)
    import app.main as main

    band = client.post("/api/bands", json={"name": f"Band {tmp_path.name}"}).json()[
        "band"
    ]
    project = client.post(
        f"/api/bands/{band['id']}/projects",
        json={"name": "Protected", "description": ""},
    ).json()["project"]

    outsider = asyncio.run(
        main.execute(
            "INSERT INTO users (display_name, fingerprint_token) VALUES ('Outsider Writer', 'fp-outsider-writer') RETURNING id"
        )
    )
    outsider_id = int(outsider.rows[0][0])

    blocked_song = client.post(
        "/api/analyze",
        files={"file": ("demo.mp3", b"audio-bytes", "audio/mpeg")},
        data={"process_mode": "analysis_only", "project_id": str(project["id"])},
        headers={"X-DeChord-User-Id": str(outsider_id)},
    )
    assert blocked_song.status_code == 403

    songs_in_project = asyncio.run(
        main.execute("SELECT COUNT(*) FROM songs WHERE project_id = ?", [project["id"]])
    )
    assert songs_in_project.rows[0][0] == 0

    owner_song = client.post(
        "/api/analyze",
        files={"file": ("demo.mp3", b"audio-bytes", "audio/mpeg")},
        data={"process_mode": "analysis_only", "project_id": str(project["id"])},
        headers={"X-DeChord-User-Id": "1"},
    )
    assert owner_song.status_code == 200
    song_id = owner_song.json()["song_id"]

    blocked_note = client.post(
        f"/api/songs/{song_id}/notes",
        json={"type": "chord", "text": "Sneaky note", "chord_index": 0},
        headers={"X-DeChord-User-Id": str(outsider_id)},
    )
    assert blocked_note.status_code == 403

    note = client.post(
        f"/api/songs/{song_id}/notes",
        json={"type": "chord", "text": "Owner note", "chord_index": 0},
        headers={"X-DeChord-User-Id": "1"},
    )
    assert note.status_code == 200
    note_id = note.json()["id"]

    blocked_update = client.patch(
        f"/api/notes/{note_id}",
        json={"text": "Hijacked"},
        headers={"X-DeChord-User-Id": str(outsider_id)},
    )
    assert blocked_update.status_code == 403

    blocked_resolve = client.patch(
        f"/api/notes/{note_id}/resolve",
        json={"resolved": True},
        headers={"X-DeChord-User-Id": str(outsider_id)},
    )
    assert blocked_resolve.status_code == 403

    blocked_delete = client.delete(
        f"/api/notes/{note_id}", headers={"X-DeChord-User-Id": str(outsider_id)}
    )
    assert blocked_delete.status_code == 403

    blocked_stem = client.post(
        f"/api/songs/{song_id}/stems/upload",
        data={"stem_key": "bass"},
        files={"file": ("bass.wav", b"bass-audio", "audio/wav")},
        headers={"X-DeChord-User-Id": str(outsider_id)},
    )
    assert blocked_stem.status_code == 403

    note_rs = asyncio.run(
        main.execute("SELECT text, resolved FROM notes WHERE id = ?", [note_id])
    )
    assert tuple(note_rs.rows[0]) == ("Owner note", 0)

    activity_rs = asyncio.run(
        main.execute(
            "SELECT event_type, message FROM project_activity_events WHERE project_id = ? ORDER BY id ASC",
            [project["id"]],
        )
    )
    assert [tuple(row) for row in activity_rs.rows] == [
        ("song_created", "uploaded a song"),
        ("note_created", "left a note"),
    ]


def test_analyze_persists_song_in_requested_project(tmp_path, monkeypatch):
    client = _build_client(tmp_path, monkeypatch)
    band_name = f"My Band {tmp_path.name}"

    created_band = client.post("/api/bands", json={"name": band_name})
    band_id = created_band.json()["band"]["id"]
    created_project = client.post(
        f"/api/bands/{band_id}/projects",
        json={"name": "Project B", "description": ""},
    )
    project_id = created_project.json()["project"]["id"]

    files = {"file": ("demo.mp3", b"audio-bytes", "audio/mpeg")}
    response = client.post(
        "/api/analyze",
        files=files,
        data={"process_mode": "analysis_only", "project_id": str(project_id)},
    )

    assert response.status_code == 200
    song_id = response.json()["song_id"]

    song = client.get(f"/api/songs/{song_id}")
    assert song.status_code == 200
    assert song.json()["song"]["id"] == song_id

    project_songs = client.get(f"/api/projects/{project_id}/songs")
    assert project_songs.status_code == 200
    assert [row["id"] for row in project_songs.json()["songs"]] == [song_id]


def test_stem_download_endpoints_support_single_and_zip(tmp_path, monkeypatch):
    client = _build_client(tmp_path, monkeypatch)

    import app.main as main
    from app.services.alphatex_exporter import SyncPoint
    from app.services.rhythm_grid import Bar
    from app.services.tab_pipeline import TabPipelineResult
    from app.stems import StemResult

    def fake_split_to_stems(audio_path, output_dir, on_progress=None, separate_fn=None):
        output_dir.mkdir(parents=True, exist_ok=True)
        bass = output_dir / "bass.wav"
        drums = output_dir / "drums.wav"
        bass.write_bytes(b"bass-bytes")
        drums.write_bytes(b"drums-bytes")
        return [
            StemResult(
                stem_key="bass", relative_path=str(bass), mime_type="audio/x-wav"
            ),
            StemResult(
                stem_key="drums", relative_path=str(drums), mime_type="audio/x-wav"
            ),
        ]

    def fake_run(*_args, **_kwargs):
        return TabPipelineResult(
            alphatex="\\tempo 120\n\\sync(0 0 0 0)",
            tempo_used=120.0,
            bars=[
                Bar(index=0, start_sec=0.0, end_sec=2.0, beats_sec=[0.0, 0.5, 1.0, 1.5])
            ],
            sync_points=[SyncPoint(bar_index=0, millisecond_offset=0)],
            midi_bytes=b"MThd\x00\x00\x00\x06",
            fingered_notes=[],
            debug_info={"rhythm_source": "madmom"},
        )

    monkeypatch.setattr(main, "split_to_stems", fake_split_to_stems)
    monkeypatch.setattr(main.tab_pipeline, "run", fake_run)

    files = {"file": ("demo.mp3", b"audio-bytes", "audio/mpeg")}
    created = client.post(
        "/api/analyze", files=files, data={"process_mode": "analysis_and_stems"}
    )
    assert created.status_code == 200
    song_id = created.json()["song_id"]

    single = client.get(f"/api/songs/{song_id}/stems/bass/download")
    assert single.status_code == 200
    assert single.content == b"bass-bytes"
    assert "attachment;" in single.headers.get("content-disposition", "")

    bundled = client.get(f"/api/songs/{song_id}/stems/download")
    assert bundled.status_code == 200
    assert "attachment;" in bundled.headers.get("content-disposition", "")
    with zipfile.ZipFile(io.BytesIO(bundled.content), "r") as archive:
        assert sorted(archive.namelist()) == ["bass.wav", "drums.wav"]


def test_analyze_persists_song_and_analysis(tmp_path, monkeypatch):
    client = _build_client(tmp_path, monkeypatch)

    files = {"file": ("demo.mp3", b"audio-bytes", "audio/mpeg")}
    response = client.post(
        "/api/analyze", files=files, data={"process_mode": "analysis_only"}
    )
    assert response.status_code == 200
    body = response.json()
    assert "job_id" in body
    assert "song_id" in body

    status = client.get(f"/api/status/{body['job_id']}")
    assert status.status_code == 200
    status_payload = status.json()
    assert status_payload["status"] == "complete"
    assert status_payload["stage"] == "complete"
    assert isinstance(status_payload["progress_pct"], (int, float))
    assert status_payload["progress_pct"] == 100
    assert isinstance(status_payload["stage_progress_pct"], (int, float))
    assert status_payload["stage_progress_pct"] == 100
    assert isinstance(status_payload["message"], str)

    result = client.get(f"/api/result/{body['job_id']}")
    assert result.status_code == 200
    payload = result.json()
    assert payload["song_id"] == body["song_id"]
    assert payload["key"] == "C major"
    assert payload["tempo"] == 120
    assert len(payload["chords"]) == 2

    songs = client.get("/api/songs")
    assert songs.status_code == 200
    assert songs.json()["songs"][0]["id"] == body["song_id"]

    song = client.get(f"/api/songs/{body['song_id']}")
    assert song.status_code == 200
    song_payload = song.json()
    assert song_payload["song"]["title"] == "demo"
    assert song_payload["analysis"]["tempo"] == 120
    assert song_payload["notes"] == []
    assert song_payload["playback_prefs"]["speed_percent"] == 100

    audio = client.get(f"/api/audio/{body['song_id']}")
    assert audio.status_code == 200
    assert audio.content == b"audio-bytes"

    tabs_meta = client.get(f"/api/songs/{body['song_id']}/tabs")
    assert tabs_meta.status_code == 200
    assert tabs_meta.json() == {"tab": None}


def test_notes_and_playback_prefs_crud(tmp_path, monkeypatch):
    client = _build_client(tmp_path, monkeypatch)
    files = {"file": ("demo.mp3", b"audio-bytes", "audio/mpeg")}
    create = client.post("/api/analyze", files=files)
    song_id = create.json()["song_id"]

    note = client.post(
        f"/api/songs/{song_id}/notes",
        json={
            "type": "time",
            "text": "Watch this transition",
            "timestamp_sec": 1.5,
            "toast_duration_sec": 2.0,
        },
    )
    assert note.status_code == 200
    note_id = note.json()["id"]

    updated = client.patch(
        f"/api/notes/{note_id}",
        json={"text": "Updated", "toast_duration_sec": 3.0},
    )
    assert updated.status_code == 200
    assert updated.json()["text"] == "Updated"

    prefs = client.put(
        f"/api/songs/{song_id}/playback-prefs",
        json={
            "speed_percent": 80,
            "volume": 0.6,
            "loop_start_index": 0,
            "loop_end_index": 1,
        },
    )
    assert prefs.status_code == 200
    assert prefs.json()["speed_percent"] == 80

    song = client.get(f"/api/songs/{song_id}")
    song_payload = song.json()
    assert len(song_payload["notes"]) == 1
    assert song_payload["notes"][0]["text"] == "Updated"
    assert song_payload["playback_prefs"]["speed_percent"] == 80

    deleted = client.delete(f"/api/notes/{note_id}")
    assert deleted.status_code == 200


def test_song_notes_support_resolve_and_truthful_payloads(tmp_path, monkeypatch):
    client = _build_client(tmp_path, monkeypatch)
    import app.main as main

    expected_author = asyncio.run(main.get_default_user())
    expected_avatar = main._build_author_avatar(str(expected_author["display_name"]))

    create = client.post(
        "/api/analyze",
        files={"file": ("demo.mp3", b"audio", "audio/mpeg")},
    )
    song_id = create.json()["song_id"]

    created = client.post(
        f"/api/songs/{song_id}/notes",
        json={"type": "chord", "text": "Tighten the verse lock", "chord_index": 1},
    )
    assert created.status_code == 200
    note_id = created.json()["id"]

    author_rs = asyncio.run(
        main.execute(
            "SELECT author_user_id, author_name, author_avatar, resolved FROM notes WHERE id = ?",
            [note_id],
        )
    )
    assert tuple(author_rs.rows[0]) == (
        expected_author["id"],
        expected_author["display_name"],
        expected_avatar,
        0,
    )

    resolved = client.patch(f"/api/notes/{note_id}/resolve", json={"resolved": True})
    assert resolved.status_code == 200
    assert resolved.json() == {"id": note_id, "resolved": True}

    asyncio.run(
        main.execute(
            "UPDATE notes SET updated_at = '2001-01-01 00:00:00' WHERE id = ?",
            [note_id],
        )
    )
    before_repeat = asyncio.run(
        main.execute("SELECT updated_at FROM notes WHERE id = ?", [note_id])
    ).rows[0][0]

    resolved_again = client.patch(
        f"/api/notes/{note_id}/resolve", json={"resolved": True}
    )
    assert resolved_again.status_code == 200
    assert resolved_again.json() == {"id": note_id, "resolved": True}
    after_repeat = asyncio.run(
        main.execute("SELECT updated_at FROM notes WHERE id = ?", [note_id])
    ).rows[0][0]
    assert after_repeat == before_repeat

    unresolved = client.patch(f"/api/notes/{note_id}/resolve", json={"resolved": False})
    assert unresolved.status_code == 200
    assert unresolved.json() == {"id": note_id, "resolved": False}

    song = client.get(f"/api/songs/{song_id}")
    payload = song.json()["notes"][0]
    assert payload["resolved"] is False
    assert payload["author_name"] == "Wojtek"
    assert payload["author_avatar"] == "W"
    assert payload["created_at"]
    assert payload["updated_at"]

    missing = client.patch("/api/notes/999999/resolve", json={"resolved": True})
    assert missing.status_code == 404


def test_notes_schema_includes_resolved_and_persisted_author_columns(
    tmp_path, monkeypatch
):
    _build_client(tmp_path, monkeypatch)
    import app.main as main

    columns_rs = asyncio.run(main.execute("PRAGMA table_info(notes)"))
    columns = {str(row[1]): row for row in columns_rs.rows}

    assert "resolved" in columns
    assert columns["resolved"][4] == "0"
    assert "author_user_id" in columns
    assert "author_name" in columns
    assert "author_avatar" in columns


def test_notes_backfill_uses_actual_default_user_and_derived_avatar(
    tmp_path, monkeypatch
):
    db_path = tmp_path / "legacy-notes.db"
    monkeypatch.setenv("DECHORD_DB_URL", f"file:{db_path}")

    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            display_name TEXT NOT NULL UNIQUE,
            fingerprint_token TEXT UNIQUE,
            username TEXT UNIQUE,
            is_claimed INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE songs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            project_id INTEGER,
            title TEXT NOT NULL,
            original_filename TEXT,
            mime_type TEXT,
            audio_blob BLOB NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            song_id INTEGER NOT NULL,
            type TEXT NOT NULL CHECK(type IN ('time', 'chord')),
            timestamp_sec REAL,
            chord_index INTEGER,
            text TEXT NOT NULL,
            toast_duration_sec REAL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    conn.execute("INSERT INTO users (display_name) VALUES ('Existing User')")
    conn.execute(
        "INSERT INTO songs (user_id, project_id, title, original_filename, mime_type, audio_blob) VALUES (1, NULL, 'legacy-note-song', 'legacy.mp3', 'audio/mpeg', x'00')"
    )
    conn.execute(
        "INSERT INTO notes (song_id, type, timestamp_sec, chord_index, text, toast_duration_sec) VALUES (1, 'time', 1.0, NULL, 'legacy', NULL)"
    )
    conn.commit()
    conn.close()

    import app.db as db_mod
    import app.main as main

    asyncio.run(db_mod.reset_db_client_for_tests())
    importlib.reload(db_mod)
    main = importlib.reload(main)
    asyncio.run(main.init_db())

    default_user = asyncio.run(main.get_default_user())
    expected_avatar = main._build_author_avatar(str(default_user["display_name"]))
    assert default_user["id"] != 1

    backfilled = asyncio.run(
        main.execute(
            "SELECT author_user_id, author_name, author_avatar FROM notes WHERE id = 1"
        )
    )
    assert tuple(backfilled.rows[0]) == (
        default_user["id"],
        default_user["display_name"],
        expected_avatar,
    )


def test_create_time_note_requires_timestamp_sec(tmp_path, monkeypatch):
    client = _build_client(tmp_path, monkeypatch)

    create = client.post(
        "/api/analyze",
        files={"file": ("demo.mp3", b"audio", "audio/mpeg")},
    )
    song_id = create.json()["song_id"]

    response = client.post(
        f"/api/songs/{song_id}/notes",
        json={"type": "time", "text": "Needs an actual timestamp"},
    )

    assert response.status_code == 400


def test_create_chord_note_requires_chord_index(tmp_path, monkeypatch):
    client = _build_client(tmp_path, monkeypatch)

    create = client.post(
        "/api/analyze",
        files={"file": ("demo.mp3", b"audio", "audio/mpeg")},
    )
    song_id = create.json()["song_id"]

    response = client.post(
        f"/api/songs/{song_id}/notes",
        json={"type": "chord", "text": "Needs a chord reference"},
    )

    assert response.status_code == 400


def test_status_not_found(tmp_path, monkeypatch):
    client = _build_client(tmp_path, monkeypatch)
    response = client.get("/api/status/nonexistent")
    assert response.status_code == 404


def test_result_not_found(tmp_path, monkeypatch):
    client = _build_client(tmp_path, monkeypatch)
    response = client.get("/api/result/nonexistent")
    assert response.status_code == 404


def test_analyze_with_stems_reports_split_stage(tmp_path, monkeypatch):
    client = _build_client(tmp_path, monkeypatch)

    import app.main as main
    from app.services.alphatex_exporter import SyncPoint
    from app.services.rhythm_grid import Bar
    from app.services.tab_pipeline import TabPipelineResult
    from app.stems import StemResult

    def fake_split_to_stems(audio_path, output_dir, on_progress=None, separate_fn=None):
        output_dir.mkdir(parents=True, exist_ok=True)
        bass = output_dir / "bass.wav"
        drums = output_dir / "drums.wav"
        bass.write_bytes(b"bass-bytes")
        drums.write_bytes(b"drums-bytes")
        if on_progress:
            on_progress(10, "warmup")
            on_progress(100, "done")
        return [
            StemResult(
                stem_key="bass", relative_path=str(bass), mime_type="audio/x-wav"
            ),
            StemResult(
                stem_key="drums", relative_path=str(drums), mime_type="audio/x-wav"
            ),
        ]

    def fake_run(*_args, **_kwargs):
        return TabPipelineResult(
            alphatex="\\tempo 120\n\\sync(0 0 0 0)",
            tempo_used=120.0,
            bars=[
                Bar(index=0, start_sec=0.0, end_sec=2.0, beats_sec=[0.0, 0.5, 1.0, 1.5])
            ],
            sync_points=[SyncPoint(bar_index=0, millisecond_offset=0)],
            midi_bytes=b"MThd\x00\x00\x00\x06",
            fingered_notes=[],
            debug_info={"rhythm_source": "madmom"},
        )

    monkeypatch.setattr(main, "split_to_stems", fake_split_to_stems)
    monkeypatch.setattr(main.tab_pipeline, "run", fake_run)

    files = {"file": ("demo.mp3", b"audio-bytes", "audio/mpeg")}
    response = client.post(
        "/api/analyze", files=files, data={"process_mode": "analysis_and_stems"}
    )
    assert response.status_code == 200
    song_id = response.json()["song_id"]
    job_id = response.json()["job_id"]

    status = client.get(f"/api/status/{job_id}")
    assert status.status_code == 200
    payload = status.json()
    assert payload["status"] == "complete"
    assert payload["stage"] == "complete"
    assert payload["stems_status"] == "complete"
    assert payload["midi_status"] == "complete"
    assert payload["midi_error"] is None
    assert payload["tab_status"] == "complete"
    assert payload["tab_error"] is None
    assert "splitting_stems" in payload["stage_history"]
    assert "transcribing_bass_midi" in payload["stage_history"]
    assert "generating_tabs" in payload["stage_history"]

    persisted = asyncio.run(
        main.execute("SELECT COUNT(*) FROM song_midis WHERE song_id = ?", [song_id])
    )
    assert persisted.rows[0][0] == 1

    midi_file = client.get(f"/api/songs/{song_id}/midi/file")
    assert midi_file.status_code == 200
    assert midi_file.content.startswith(b"MThd")

    tab_file = client.get(f"/api/songs/{song_id}/tabs/file")
    assert tab_file.status_code == 200
    assert tab_file.content.startswith(b"\\tempo")


def test_analyze_with_stems_failure_keeps_analysis_complete(tmp_path, monkeypatch):
    client = _build_client(tmp_path, monkeypatch)

    import app.main as main

    def fake_split_to_stems(audio_path, output_dir, on_progress=None, separate_fn=None):
        raise RuntimeError("stem split failed")

    monkeypatch.setattr(main, "split_to_stems", fake_split_to_stems)

    files = {"file": ("demo.mp3", b"audio-bytes", "audio/mpeg")}
    response = client.post(
        "/api/analyze", files=files, data={"process_mode": "analysis_and_stems"}
    )
    assert response.status_code == 200
    job_id = response.json()["job_id"]

    status = client.get(f"/api/status/{job_id}")
    assert status.status_code == 200
    payload = status.json()
    assert payload["status"] == "complete"
    assert payload["stems_status"] == "failed"
    assert payload["midi_status"] == "not_requested"
    assert payload["midi_error"] is None
    assert payload["tab_status"] == "not_requested"
    assert payload["tab_error"] is None
    assert payload["error"] is None
    assert payload["stems_error"] == "stem split failed"

    result = client.get(f"/api/result/{job_id}")
    assert result.status_code == 200
    assert result.json()["tempo"] == 120


def test_analyze_with_stems_routes_bass_analysis_wav_into_tab_pipeline(
    tmp_path, monkeypatch
):
    client = _build_client(tmp_path, monkeypatch)

    import app.main as main
    from app.services.alphatex_exporter import SyncPoint
    from app.services.rhythm_grid import Bar
    from app.services.tab_pipeline import TabPipelineResult
    from app.stems import StemResult

    pipeline_call: dict[str, str] = {}

    def fake_split_to_stems(audio_path, output_dir, on_progress=None, separate_fn=None):
        output_dir.mkdir(parents=True, exist_ok=True)
        bass = output_dir / "bass.wav"
        drums = output_dir / "drums.wav"
        other = output_dir / "other.wav"
        bass.write_bytes(b"bass-bytes")
        drums.write_bytes(b"drums-bytes")
        other.write_bytes(b"other-bytes")
        return [
            StemResult(
                stem_key="bass", relative_path=str(bass), mime_type="audio/x-wav"
            ),
            StemResult(
                stem_key="drums", relative_path=str(drums), mime_type="audio/x-wav"
            ),
            StemResult(
                stem_key="other", relative_path=str(other), mime_type="audio/x-wav"
            ),
        ]

    def fake_build_bass_analysis_stem(
        *,
        stems,
        output_dir,
        source_audio_path=None,
        analysis_config=None,
        separate_fn=None,
    ):
        assert stems["bass"].name == "bass.wav"
        assert source_audio_path is not None
        analysis_path = output_dir / "bass_analysis.wav"
        analysis_path.write_bytes(b"analysis-bass")
        return main.BassAnalysisStemResult(
            path=analysis_path,
            source_model="htdemucs_ft",
            diagnostics={"selected_model": "htdemucs_ft"},
        )

    def fake_run(bass_wav, drums_wav, **_kwargs):
        pipeline_call["bass_wav"] = str(bass_wav)
        pipeline_call["drums_wav"] = str(drums_wav)
        return TabPipelineResult(
            alphatex="\\tempo 120\n\\sync(0 0 0 0)",
            tempo_used=120.0,
            bars=[
                Bar(index=0, start_sec=0.0, end_sec=2.0, beats_sec=[0.0, 0.5, 1.0, 1.5])
            ],
            sync_points=[SyncPoint(bar_index=0, millisecond_offset=0)],
            midi_bytes=b"MThd\x00\x00\x00\x06",
            debug_info={"rhythm_source": "madmom"},
        )

    monkeypatch.setattr(main, "split_to_stems", fake_split_to_stems)
    monkeypatch.setattr(main, "build_bass_analysis_stem", fake_build_bass_analysis_stem)
    monkeypatch.setattr(main.tab_pipeline, "run", fake_run)

    files = {"file": ("demo.mp3", b"audio-bytes", "audio/mpeg")}
    response = client.post(
        "/api/analyze", files=files, data={"process_mode": "analysis_and_stems"}
    )

    assert response.status_code == 200
    assert pipeline_call["bass_wav"].endswith("bass_analysis.wav")
    assert pipeline_call["drums_wav"].endswith("drums.wav")


def test_analyze_high_accuracy_enables_ensemble_analysis_config(tmp_path, monkeypatch):
    client = _build_client(tmp_path, monkeypatch)

    import app.main as main
    from app.services.alphatex_exporter import SyncPoint
    from app.services.rhythm_grid import Bar
    from app.services.tab_pipeline import TabPipelineResult
    from app.stems import StemResult

    captured: dict[str, object] = {}

    def fake_split_to_stems(audio_path, output_dir, on_progress=None, separate_fn=None):
        output_dir.mkdir(parents=True, exist_ok=True)
        bass = output_dir / "bass.wav"
        drums = output_dir / "drums.wav"
        bass.write_bytes(b"RIFFfakebass")
        drums.write_bytes(b"RIFFfakedrum")
        return [
            StemResult(
                stem_key="bass", relative_path=str(bass), mime_type="audio/x-wav"
            ),
            StemResult(
                stem_key="drums", relative_path=str(drums), mime_type="audio/x-wav"
            ),
        ]

    def fake_build_bass_analysis_stem(
        *,
        stems,
        output_dir,
        source_audio_path=None,
        analysis_config=None,
        separate_fn=None,
    ):
        captured["analysis_config"] = analysis_config
        analysis_path = output_dir / "bass_analysis.wav"
        analysis_path.write_bytes(b"analysis-bass")
        return main.BassAnalysisStemResult(
            path=analysis_path,
            source_model="htdemucs_6s",
            diagnostics={"selected_model": "htdemucs_6s"},
        )

    def fake_run(*_args, **_kwargs):
        return TabPipelineResult(
            alphatex="\\tempo 120\n\\sync(0 0 0 0)",
            tempo_used=120.0,
            bars=[
                Bar(index=0, start_sec=0.0, end_sec=2.0, beats_sec=[0.0, 0.5, 1.0, 1.5])
            ],
            sync_points=[SyncPoint(bar_index=0, millisecond_offset=0)],
            midi_bytes=b"MThd\x00\x00\x00\x06",
            debug_info={"rhythm_source": "madmom"},
        )

    monkeypatch.setattr(main, "split_to_stems", fake_split_to_stems)
    monkeypatch.setattr(main, "build_bass_analysis_stem", fake_build_bass_analysis_stem)
    monkeypatch.setattr(main.tab_pipeline, "run", fake_run)

    files = {"file": ("demo.mp3", b"audio-bytes", "audio/mpeg")}
    response = client.post(
        "/api/analyze",
        files=files,
        data={
            "process_mode": "analysis_and_stems",
            "tabGenerationQuality": "high_accuracy",
        },
    )

    assert response.status_code == 200
    assert captured["analysis_config"] is not None
    assert captured["analysis_config"].enable_model_ensemble is True


def test_analyze_standard_keeps_single_model_analysis_config(tmp_path, monkeypatch):
    client = _build_client(tmp_path, monkeypatch)

    import app.main as main
    from app.services.alphatex_exporter import SyncPoint
    from app.services.rhythm_grid import Bar
    from app.services.tab_pipeline import TabPipelineResult
    from app.stems import StemResult

    captured: dict[str, object] = {}

    def fake_split_to_stems(audio_path, output_dir, on_progress=None, separate_fn=None):
        output_dir.mkdir(parents=True, exist_ok=True)
        bass = output_dir / "bass.wav"
        drums = output_dir / "drums.wav"
        bass.write_bytes(b"RIFFfakebass")
        drums.write_bytes(b"RIFFfakedrum")
        return [
            StemResult(
                stem_key="bass", relative_path=str(bass), mime_type="audio/x-wav"
            ),
            StemResult(
                stem_key="drums", relative_path=str(drums), mime_type="audio/x-wav"
            ),
        ]

    def fake_build_bass_analysis_stem(
        *,
        stems,
        output_dir,
        source_audio_path=None,
        analysis_config=None,
        separate_fn=None,
    ):
        captured["analysis_config"] = analysis_config
        analysis_path = output_dir / "bass_analysis.wav"
        analysis_path.write_bytes(b"analysis-bass")
        return main.BassAnalysisStemResult(
            path=analysis_path,
            source_model="htdemucs_ft",
            diagnostics={"selected_model": "htdemucs_ft"},
        )

    def fake_run(*_args, **_kwargs):
        return TabPipelineResult(
            alphatex="\\tempo 120\n\\sync(0 0 0 0)",
            tempo_used=120.0,
            bars=[
                Bar(index=0, start_sec=0.0, end_sec=2.0, beats_sec=[0.0, 0.5, 1.0, 1.5])
            ],
            sync_points=[SyncPoint(bar_index=0, millisecond_offset=0)],
            midi_bytes=b"MThd\x00\x00\x00\x06",
            debug_info={"rhythm_source": "madmom"},
        )

    monkeypatch.setattr(main, "split_to_stems", fake_split_to_stems)
    monkeypatch.setattr(main, "build_bass_analysis_stem", fake_build_bass_analysis_stem)
    monkeypatch.setattr(main.tab_pipeline, "run", fake_run)

    files = {"file": ("demo.mp3", b"audio-bytes", "audio/mpeg")}
    response = client.post(
        "/api/analyze", files=files, data={"process_mode": "analysis_and_stems"}
    )

    assert response.status_code == 200
    assert captured["analysis_config"] is not None
    assert captured["analysis_config"].enable_model_ensemble is False


def test_stems_are_persisted_and_streamed(tmp_path, monkeypatch):
    client = _build_client(tmp_path, monkeypatch)

    import app.main as main
    from app.stems import StemResult

    def fake_split_to_stems(audio_path, output_dir, on_progress=None, separate_fn=None):
        output_dir.mkdir(parents=True, exist_ok=True)
        drums = output_dir / "drums.wav"
        vocals = output_dir / "vocals.wav"
        drums.write_bytes(b"drums-bytes")
        vocals.write_bytes(b"vocals-bytes")
        return [
            StemResult(
                stem_key="drums", relative_path=str(drums), mime_type="audio/x-wav"
            ),
            StemResult(
                stem_key="vocals", relative_path=str(vocals), mime_type="audio/x-wav"
            ),
        ]

    monkeypatch.setattr(main, "split_to_stems", fake_split_to_stems)

    files = {"file": ("demo.mp3", b"audio-bytes", "audio/mpeg")}
    response = client.post(
        "/api/analyze", files=files, data={"process_mode": "analysis_and_stems"}
    )
    assert response.status_code == 200
    song_id = response.json()["song_id"]

    stems_response = client.get(f"/api/songs/{song_id}/stems")
    assert stems_response.status_code == 200
    stems = stems_response.json()["stems"]
    assert len(stems) == 2
    assert {s["stem_key"] for s in stems} == {"drums", "vocals"}

    drums_audio = client.get(f"/api/audio/{song_id}/stems/drums")
    assert drums_audio.status_code == 200
    assert drums_audio.content == b"drums-bytes"


def test_upload_song_stem_persists_user_asset_and_returns_provenance(
    tmp_path, monkeypatch
):
    client = _build_client(tmp_path, monkeypatch)
    import app.main as main

    inserted = asyncio.run(
        main.execute(
            """
            INSERT INTO songs (user_id, title, original_filename, mime_type, audio_blob)
            VALUES (1, 'Demo Song', 'demo.mp3', 'audio/mpeg', x'00')
            RETURNING id
            """
        )
    )
    song_id = int(inserted.rows[0][0])

    stale_dir = tmp_path / "stale"
    stale_dir.mkdir(parents=True, exist_ok=True)
    stale_bass = stale_dir / "bass.wav"
    stale_bass.write_bytes(b"old-system-bass")
    asyncio.run(
        main.execute(
            """
            INSERT INTO song_stems (song_id, stem_key, relative_path, mime_type, duration)
            VALUES (?, 'bass', ?, 'audio/x-wav', 1.0)
            """,
            [song_id, str(stale_bass)],
        )
    )

    response = client.post(
        f"/api/songs/{song_id}/stems/upload",
        data={"stem_key": "bass"},
        files={"file": ("bass.wav", b"bass-audio", "audio/wav")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert [stem["stem_key"] for stem in payload["stems"]] == ["bass"]
    assert payload["stems"][0]["source_type"] == "user"
    assert payload["stems"][0]["display_name"] == "bass.wav"
    assert payload["stems"][0]["uploaded_by_name"] is not None
    assert payload["stems"][0]["version_label"].startswith("upload-")
    assert payload["stems"][0]["is_archived"] is False

    persisted = asyncio.run(
        main.execute(
            "SELECT stem_key, relative_path, source_type, display_name, version_label, uploaded_by_name FROM song_stems WHERE song_id = ? ORDER BY stem_key ASC",
            [song_id],
        )
    )
    assert len(persisted.rows) == 1
    assert tuple(persisted.rows[0])[0] == "bass"
    assert tuple(persisted.rows[0])[1] != str(stale_bass)
    assert tuple(persisted.rows[0])[2:] == (
        "user",
        "bass.wav",
        payload["stems"][0]["version_label"],
        payload["stems"][0]["uploaded_by_name"],
    )


def test_upload_song_stem_same_filename_creates_distinct_storage_and_versions(
    tmp_path, monkeypatch
):
    client = _build_client(tmp_path, monkeypatch)
    import app.main as main

    inserted = asyncio.run(
        main.execute(
            """
            INSERT INTO songs (user_id, title, original_filename, mime_type, audio_blob)
            VALUES (1, 'Demo Song', 'demo.mp3', 'audio/mpeg', x'00')
            RETURNING id
            """
        )
    )
    song_id = int(inserted.rows[0][0])

    first = client.post(
        f"/api/songs/{song_id}/stems/upload",
        data={"stem_key": "bass"},
        files={"file": ("bass.wav", b"first-bass", "audio/wav")},
    )
    assert first.status_code == 200
    first_stem = first.json()["stems"][0]

    second = client.post(
        f"/api/songs/{song_id}/stems/upload",
        data={"stem_key": "bass"},
        files={"file": ("bass.wav", b"second-bass", "audio/wav")},
    )
    assert second.status_code == 200
    second_stem = second.json()["stems"][0]

    assert first_stem["display_name"] == "bass.wav"
    assert second_stem["display_name"] == "bass.wav"
    assert first_stem["relative_path"] != second_stem["relative_path"]
    assert first_stem["version_label"] != second_stem["version_label"]
    assert Path(first_stem["relative_path"]).read_bytes() == b"first-bass"
    assert Path(second_stem["relative_path"]).read_bytes() == b"second-bass"


def test_tabs_metadata_endpoint_returns_latest_tab(tmp_path, monkeypatch):
    client = _build_client(tmp_path, monkeypatch)
    import app.main as main

    inserted = asyncio.run(
        main.execute(
            """
            INSERT INTO songs (user_id, title, original_filename, mime_type, audio_blob)
            VALUES (1, 'demo', 'demo.mp3', 'audio/mpeg', x'00')
            RETURNING id
            """
        )
    )
    song_id = int(inserted.rows[0][0])
    midi_inserted = asyncio.run(
        main.execute(
            """
            INSERT INTO song_midis (song_id, source_stem_key, midi_blob, midi_format, engine, status, error_message)
            VALUES (?, 'bass', x'4D546864', 'mid', 'test', 'complete', NULL)
            RETURNING id
            """,
            [song_id],
        )
    )
    midi_id = int(midi_inserted.rows[0][0])
    asyncio.run(
        main.execute(
            """
            INSERT INTO song_tabs (song_id, source_midi_id, tab_blob, tab_format, tuning, strings, generator_version, status, error_message)
            VALUES (?, ?, ?, 'alphatex', 'E1,A1,D2,G2', 4, 'v2-rhythm-grid', 'complete', NULL)
            """,
            [song_id, midi_id, b"\\tempo 120\n\\sync(0 0 0 0)"],
        )
    )

    tabs_meta = client.get(f"/api/songs/{song_id}/tabs")
    assert tabs_meta.status_code == 200
    payload = tabs_meta.json()
    assert payload["tab"] is not None
    assert payload["tab"]["tab_format"] == "alphatex"
    assert payload["tab"]["strings"] == 4


def test_song_tabs_metadata_includes_source_provenance_fields(tmp_path, monkeypatch):
    client = _build_client(tmp_path, monkeypatch)
    import app.main as main

    inserted = asyncio.run(
        main.execute(
            """
            INSERT INTO songs (user_id, title, original_filename, mime_type, audio_blob)
            VALUES (1, 'Demo Song', 'demo.mp3', 'audio/mpeg', x'00')
            RETURNING id
            """
        )
    )
    song_id = int(inserted.rows[0][0])

    stem_dir = tmp_path / "uploaded" / str(song_id)
    stem_dir.mkdir(parents=True, exist_ok=True)
    bass = stem_dir / "bass.wav"
    bass.write_bytes(b"user-bass")
    stem_inserted = asyncio.run(
        main.execute(
            """
            INSERT INTO song_stems (song_id, stem_key, relative_path, mime_type, duration, source_type, display_name, version_label, uploaded_by_name)
            VALUES (?, 'bass', ?, 'audio/x-wav', 2.0, 'user', 'bass.wav', 'upload-1', 'Groove Bassline')
            RETURNING id
            """,
            [song_id, str(bass)],
        )
    )
    stem_id = int(stem_inserted.rows[0][0])
    midi_inserted = asyncio.run(
        main.execute(
            """
            INSERT INTO song_midis (
                song_id,
                source_stem_key,
                source_stem_id,
                source_stem_source_type,
                source_stem_display_name,
                source_stem_version_label,
                midi_blob,
                midi_format,
                engine,
                status,
                error_message
            )
            VALUES (?, 'bass', ?, 'user', 'bass.wav', 'upload-1', x'4D546864', 'mid', 'test', 'complete', NULL)
            RETURNING id
            """,
            [song_id, stem_id],
        )
    )
    midi_id = int(midi_inserted.rows[0][0])
    asyncio.run(
        main.execute(
            """
            INSERT INTO song_tabs (song_id, source_midi_id, tab_blob, tab_format, tuning, strings, generator_version, status, error_message)
            VALUES (?, ?, ?, 'alphatex', 'E1,A1,D2,G2', 4, 'v2-rhythm-grid', 'complete', NULL)
            """,
            [song_id, midi_id, b"\\tempo 120\n\\sync(0 0 0 0)"],
        )
    )

    tabs_meta = client.get(f"/api/songs/{song_id}/tabs")

    assert tabs_meta.status_code == 200
    payload = tabs_meta.json()["tab"]
    assert payload["source_stem_key"] == "bass"
    assert payload["source_type"] == "user"
    assert payload["source_display_name"] == "bass.wav"
    assert payload["source_stem_id"] == stem_id
    assert payload["source_version_label"] == "upload-1"


def test_song_tabs_provenance_stays_tied_to_generated_source_after_later_replacement(
    tmp_path, monkeypatch
):
    client = _build_client(tmp_path, monkeypatch)
    import app.main as main
    from app.services.alphatex_exporter import SyncPoint
    from app.services.rhythm_grid import Bar
    from app.services.tab_pipeline import TabPipelineResult

    inserted = asyncio.run(
        main.execute(
            """
            INSERT INTO songs (user_id, title, original_filename, mime_type, audio_blob)
            VALUES (1, 'Demo Song', 'demo.mp3', 'audio/mpeg', x'00')
            RETURNING id
            """
        )
    )
    song_id = int(inserted.rows[0][0])

    stem_dir = tmp_path / "stems" / str(song_id)
    stem_dir.mkdir(parents=True, exist_ok=True)
    drums = stem_dir / "drums.wav"
    drums.write_bytes(b"drums-audio")
    asyncio.run(
        main.execute(
            """
            INSERT INTO song_stems (song_id, stem_key, relative_path, mime_type, duration, source_type, display_name, version_label)
            VALUES (?, 'drums', ?, 'audio/x-wav', 2.0, 'system', 'Drums', 'regen-drums-1')
            """,
            [song_id, str(drums)],
        )
    )

    def fake_build_bass_analysis_stem(
        *,
        stems,
        output_dir,
        source_audio_path=None,
        analysis_config=None,
        separate_fn=None,
    ):
        analysis_path = output_dir / "bass_analysis.wav"
        analysis_path.parent.mkdir(parents=True, exist_ok=True)
        analysis_path.write_bytes(b"analysis-bass")
        return main.BassAnalysisStemResult(
            path=analysis_path,
            source_model="test-model",
            diagnostics={"selected_model": "test-model"},
        )

    def fake_run(*_args, **_kwargs):
        return TabPipelineResult(
            alphatex="\\tempo 120\n\\sync(0 0 0 0)",
            tempo_used=120.0,
            bars=[
                Bar(index=0, start_sec=0.0, end_sec=2.0, beats_sec=[0.0, 0.5, 1.0, 1.5])
            ],
            sync_points=[SyncPoint(bar_index=0, millisecond_offset=0)],
            midi_bytes=b"MThd\x00\x00\x00\x06",
            fingered_notes=[],
            debug_info={"rhythm_source": "madmom"},
        )

    monkeypatch.setattr(main, "build_bass_analysis_stem", fake_build_bass_analysis_stem)
    monkeypatch.setattr(main.tab_pipeline, "run", fake_run)

    first_upload = client.post(
        f"/api/songs/{song_id}/stems/upload",
        data={"stem_key": "bass"},
        files={"file": ("bass.wav", b"first-bass", "audio/wav")},
    )
    assert first_upload.status_code == 200
    first_bass = first_upload.json()["stems"][0]

    regenerate = client.post(
        f"/api/songs/{song_id}/tabs/regenerate",
        json={"source_stem_key": "bass"},
    )
    assert regenerate.status_code == 200

    second_upload = client.post(
        f"/api/songs/{song_id}/stems/upload",
        data={"stem_key": "bass"},
        files={"file": ("bass.wav", b"second-bass", "audio/wav")},
    )
    assert second_upload.status_code == 200
    second_bass = second_upload.json()["stems"][0]
    assert second_bass["id"] != first_bass["id"]

    tabs_meta = client.get(f"/api/songs/{song_id}/tabs")

    assert tabs_meta.status_code == 200
    payload = tabs_meta.json()["tab"]
    assert payload["source_stem_key"] == "bass"
    assert payload["source_stem_id"] == first_bass["id"]
    assert payload["source_display_name"] == "bass.wav"
    assert payload["source_type"] == "user"
    assert payload["source_version_label"] == first_bass["version_label"]


def test_regenerate_song_stems_preserves_active_user_upload_for_same_key(
    tmp_path, monkeypatch
):
    client = _build_client(tmp_path, monkeypatch)
    import app.main as main
    from app.stems import StemResult

    inserted = asyncio.run(
        main.execute(
            """
            INSERT INTO songs (user_id, title, original_filename, mime_type, audio_blob)
            VALUES (1, 'Demo Song', 'demo.mp3', 'audio/mpeg', ?)
            RETURNING id
            """,
            [b"song-audio"],
        )
    )
    song_id = int(inserted.rows[0][0])

    uploaded = client.post(
        f"/api/songs/{song_id}/stems/upload",
        data={"stem_key": "bass"},
        files={"file": ("bass.wav", b"manual-bass", "audio/wav")},
    )
    assert uploaded.status_code == 200
    manual_bass = uploaded.json()["stems"][0]

    def fake_split_to_stems(audio_path, output_dir, on_progress=None, separate_fn=None):
        output_dir.mkdir(parents=True, exist_ok=True)
        bass = output_dir / "bass.wav"
        drums = output_dir / "drums.wav"
        bass.write_bytes(b"generated-bass")
        drums.write_bytes(b"generated-drums")
        return [
            StemResult(
                stem_key="bass",
                relative_path=str(bass),
                mime_type="audio/x-wav",
                duration=2.5,
            ),
            StemResult(
                stem_key="drums",
                relative_path=str(drums),
                mime_type="audio/x-wav",
                duration=2.5,
            ),
        ]

    monkeypatch.setattr(main, "split_to_stems", fake_split_to_stems)

    response = client.post(f"/api/songs/{song_id}/stems/regenerate")

    assert response.status_code == 200
    stems = {stem["stem_key"]: stem for stem in response.json()["stems"]}
    assert stems["bass"]["id"] == manual_bass["id"]
    assert stems["bass"]["source_type"] == "user"
    assert stems["bass"]["version_label"] == manual_bass["version_label"]
    assert Path(stems["bass"]["relative_path"]).read_bytes() == b"manual-bass"
    assert stems["drums"]["source_type"] == "system"
    assert stems["drums"]["version_label"].startswith("regen-")


def test_regenerate_song_stems_prunes_obsolete_system_rows_but_keeps_user_rows(
    tmp_path, monkeypatch
):
    client = _build_client(tmp_path, monkeypatch)
    import app.main as main
    from app.stems import StemResult

    inserted = asyncio.run(
        main.execute(
            """
            INSERT INTO songs (user_id, title, original_filename, mime_type, audio_blob)
            VALUES (1, 'Demo Song', 'demo.mp3', 'audio/mpeg', ?)
            RETURNING id
            """,
            [b"song-audio"],
        )
    )
    song_id = int(inserted.rows[0][0])

    stale_dir = tmp_path / "stale" / str(song_id)
    stale_dir.mkdir(parents=True, exist_ok=True)
    old_bass = stale_dir / "bass.wav"
    old_drums = stale_dir / "drums.wav"
    old_vocals = stale_dir / "vocals.wav"
    user_other = stale_dir / "other.wav"
    old_bass.write_bytes(b"old-bass")
    old_drums.write_bytes(b"old-drums")
    old_vocals.write_bytes(b"old-vocals")
    user_other.write_bytes(b"user-other")

    for stem_key, path, source_type, display_name, version_label in (
        ("bass", old_bass, "system", "Bass", "regen-old"),
        ("drums", old_drums, "system", "Drums", "regen-old"),
        ("vocals", old_vocals, "system", "Vocals", "regen-old"),
        ("other", user_other, "user", "other.wav", "upload-old"),
    ):
        asyncio.run(
            main.execute(
                """
                INSERT INTO song_stems (
                    song_id, stem_key, relative_path, mime_type, duration, source_type, display_name, version_label, uploaded_by_name
                )
                VALUES (?, ?, ?, 'audio/x-wav', 2.0, ?, ?, ?, ?)
                """,
                [
                    song_id,
                    stem_key,
                    str(path),
                    source_type,
                    display_name,
                    version_label,
                    "Wojtek" if source_type == "user" else None,
                ],
            )
        )

    def fake_split_to_stems(audio_path, output_dir, on_progress=None, separate_fn=None):
        output_dir.mkdir(parents=True, exist_ok=True)
        bass = output_dir / "bass.wav"
        drums = output_dir / "drums.wav"
        bass.write_bytes(b"new-bass")
        drums.write_bytes(b"new-drums")
        return [
            StemResult(
                stem_key="bass",
                relative_path=str(bass),
                mime_type="audio/x-wav",
                duration=2.5,
            ),
            StemResult(
                stem_key="drums",
                relative_path=str(drums),
                mime_type="audio/x-wav",
                duration=2.5,
            ),
        ]

    monkeypatch.setattr(main, "split_to_stems", fake_split_to_stems)

    response = client.post(f"/api/songs/{song_id}/stems/regenerate")

    assert response.status_code == 200
    stems = {stem["stem_key"]: stem for stem in response.json()["stems"]}
    assert set(stems) == {"bass", "drums", "other"}
    assert stems["bass"]["source_type"] == "system"
    assert stems["drums"]["source_type"] == "system"
    assert stems["other"]["source_type"] == "user"

    persisted = asyncio.run(
        main.execute(
            "SELECT stem_key, source_type FROM song_stems WHERE song_id = ? ORDER BY stem_key ASC",
            [song_id],
        )
    )
    assert [tuple(row) for row in persisted.rows] == [
        ("bass", "system"),
        ("drums", "system"),
        ("other", "user"),
    ]


def test_tabs_download_endpoint_returns_attachment(tmp_path, monkeypatch):
    client = _build_client(tmp_path, monkeypatch)
    import app.main as main

    inserted = asyncio.run(
        main.execute(
            """
            INSERT INTO songs (user_id, title, original_filename, mime_type, audio_blob)
            VALUES (1, 'Demo Song', 'demo.mp3', 'audio/mpeg', x'00')
            RETURNING id
            """
        )
    )
    song_id = int(inserted.rows[0][0])
    midi_inserted = asyncio.run(
        main.execute(
            """
            INSERT INTO song_midis (song_id, source_stem_key, midi_blob, midi_format, engine, status, error_message)
            VALUES (?, 'bass', x'4D546864', 'mid', 'test', 'complete', NULL)
            RETURNING id
            """,
            [song_id],
        )
    )
    midi_id = int(midi_inserted.rows[0][0])
    asyncio.run(
        main.execute(
            """
            INSERT INTO song_tabs (song_id, source_midi_id, tab_blob, tab_format, tuning, strings, generator_version, status, error_message)
            VALUES (?, ?, ?, 'alphatex', 'E1,A1,D2,G2', 4, 'v2-rhythm-grid', 'complete', NULL)
            """,
            [song_id, midi_id, b"\\tempo 120\n\\sync(0 0 0 0)"],
        )
    )

    download = client.get(f"/api/songs/{song_id}/tabs/download")
    assert download.status_code == 200
    assert download.content.startswith(b"\\tempo")
    assert "attachment" in (download.headers.get("content-disposition") or "")
    assert (download.headers.get("content-disposition") or "").endswith('.alphatex"')
    assert download.headers.get("content-length") == str(len(download.content))


def test_generate_tab_from_demucs_stems_endpoint_persists_midi_and_alphatex(
    tmp_path, monkeypatch
):
    client = _build_client(tmp_path, monkeypatch)
    import app.main as main
    from app.services.alphatex_exporter import SyncPoint
    from app.services.rhythm_grid import Bar
    from app.services.tab_pipeline import TabPipelineResult

    inserted = asyncio.run(
        main.execute(
            """
            INSERT INTO songs (user_id, title, original_filename, mime_type, audio_blob)
            VALUES (1, 'Demo Song', 'demo.mp3', 'audio/mpeg', x'00')
            RETURNING id
            """
        )
    )
    song_id = int(inserted.rows[0][0])

    def fake_run(*_args, **_kwargs):
        return TabPipelineResult(
            alphatex="\\tempo 120\n\\sync(0 0 0 0)",
            tempo_used=120.0,
            bars=[
                Bar(index=0, start_sec=0.0, end_sec=2.0, beats_sec=[0.0, 0.5, 1.0, 1.5])
            ],
            sync_points=[SyncPoint(bar_index=0, millisecond_offset=0)],
            midi_bytes=b"MThd\x00\x00\x00\x06",
            fingered_notes=[],
            debug_info={"rhythm_source": "madmom"},
        )

    monkeypatch.setattr(main.tab_pipeline, "run", fake_run)

    files = {
        "bass": ("bass.wav", b"bass-bytes", "audio/wav"),
        "drums": ("drums.wav", b"drums-bytes", "audio/wav"),
    }
    response = client.post(
        "/api/tab/from-demucs-stems",
        data={
            "song_id": song_id,
            "bpm": "120",
            "time_signature": "4/4",
            "subdivision": "16",
            "max_fret": "24",
        },
        files=files,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["tempo_used"] == 120.0
    assert payload["alphatex"].startswith("\\tempo")
    assert payload["sync_points"][0]["bar_index"] == 0

    midi_rs = asyncio.run(
        main.execute(
            "SELECT midi_blob FROM song_midis WHERE song_id = ? ORDER BY id DESC LIMIT 1",
            [song_id],
        )
    )
    assert midi_rs.rows[0][0].startswith(b"MThd")

    tab_rs = asyncio.run(
        main.execute(
            "SELECT tab_blob, tab_format FROM song_tabs WHERE song_id = ? ORDER BY id DESC LIMIT 1",
            [song_id],
        )
    )
    assert tab_rs.rows[0][0].startswith(b"\\tempo")
    assert tab_rs.rows[0][1] == "alphatex"


def test_generate_tab_from_demucs_stems_persists_transient_uploaded_provenance_for_existing_song(
    tmp_path, monkeypatch
):
    client = _build_client(tmp_path, monkeypatch)
    import app.main as main
    from app.services.alphatex_exporter import SyncPoint
    from app.services.rhythm_grid import Bar
    from app.services.tab_pipeline import TabPipelineResult

    inserted = asyncio.run(
        main.execute(
            """
            INSERT INTO songs (user_id, title, original_filename, mime_type, audio_blob)
            VALUES (1, 'Demo Song', 'demo.mp3', 'audio/mpeg', x'00')
            RETURNING id
            """
        )
    )
    song_id = int(inserted.rows[0][0])

    saved_stem_path = tmp_path / "saved-bass.wav"
    saved_stem_path.write_bytes(b"saved-bass")
    asyncio.run(
        main.execute(
            """
            INSERT INTO song_stems (
                song_id, stem_key, relative_path, mime_type, duration, source_type, display_name, version_label, uploaded_by_name
            )
            VALUES (?, 'bass', ?, 'audio/x-wav', 2.0, 'user', 'saved-bass.wav', 'upload-saved', 'Wojtek')
            """,
            [song_id, str(saved_stem_path)],
        )
    )

    def fake_run(*_args, **_kwargs):
        return TabPipelineResult(
            alphatex="\\tempo 120\n\\sync(0 0 0 0)",
            tempo_used=120.0,
            bars=[
                Bar(index=0, start_sec=0.0, end_sec=2.0, beats_sec=[0.0, 0.5, 1.0, 1.5])
            ],
            sync_points=[SyncPoint(bar_index=0, millisecond_offset=0)],
            midi_bytes=b"MThd\x00\x00\x00\x06",
            fingered_notes=[],
            debug_info={"rhythm_source": "madmom"},
        )

    monkeypatch.setattr(main.tab_pipeline, "run", fake_run)

    response = client.post(
        "/api/tab/from-demucs-stems",
        data={
            "song_id": song_id,
            "bpm": "120",
            "time_signature": "4/4",
            "subdivision": "16",
            "max_fret": "24",
        },
        files={
            "bass": ("transient-bass.wav", b"transient-bass", "audio/wav"),
            "drums": ("drums.wav", b"drums-bytes", "audio/wav"),
        },
    )

    assert response.status_code == 200

    midi_rs = asyncio.run(
        main.execute(
            "SELECT source_stem_id, source_stem_source_type, source_stem_display_name, source_stem_version_label FROM song_midis WHERE song_id = ? ORDER BY id DESC LIMIT 1",
            [song_id],
        )
    )
    assert tuple(midi_rs.rows[0])[0] is None
    assert tuple(midi_rs.rows[0])[1] == "user"
    assert tuple(midi_rs.rows[0])[2] == "transient-bass.wav"
    assert str(tuple(midi_rs.rows[0])[3]).startswith("transient-")

    tab_meta = client.get(f"/api/songs/{song_id}/tabs")
    assert tab_meta.status_code == 200
    payload = tab_meta.json()["tab"]
    assert payload["source_stem_id"] is None
    assert payload["source_type"] == "user"
    assert payload["source_display_name"] == "transient-bass.wav"
    assert str(payload["source_version_label"]).startswith("transient-")


def test_generate_tab_from_demucs_stems_routes_analysis_bass_into_tab_pipeline(
    tmp_path, monkeypatch
):
    client = _build_client(tmp_path, monkeypatch)
    import app.main as main
    from app.services.alphatex_exporter import SyncPoint
    from app.services.rhythm_grid import Bar
    from app.services.tab_pipeline import TabPipelineResult

    captured: dict[str, object] = {}

    def fake_build_bass_analysis_stem(
        *,
        stems,
        output_dir,
        source_audio_path=None,
        analysis_config=None,
        separate_fn=None,
    ):
        captured["stems"] = stems
        captured["analysis_config"] = analysis_config
        captured["source_audio_path"] = source_audio_path
        analysis_path = output_dir / "bass_analysis.wav"
        analysis_path.parent.mkdir(parents=True, exist_ok=True)
        analysis_path.write_bytes(b"analysis-bass")
        return main.BassAnalysisStemResult(
            path=analysis_path,
            source_model="uploaded_refined",
            diagnostics={"selected_model": "uploaded_refined"},
        )

    def fake_run(bass_wav, drums_wav, **_kwargs):
        captured["bass_wav"] = str(bass_wav)
        captured["drums_wav"] = str(drums_wav)
        return TabPipelineResult(
            alphatex="\\tempo 120\n\\sync(0 0 0 0)",
            tempo_used=120.0,
            bars=[
                Bar(index=0, start_sec=0.0, end_sec=2.0, beats_sec=[0.0, 0.5, 1.0, 1.5])
            ],
            sync_points=[SyncPoint(bar_index=0, millisecond_offset=0)],
            midi_bytes=b"MThd\x00\x00\x00\x06",
            debug_info={"rhythm_source": "madmom"},
        )

    monkeypatch.setattr(main, "build_bass_analysis_stem", fake_build_bass_analysis_stem)
    monkeypatch.setattr(main.tab_pipeline, "run", fake_run)

    files = {
        "bass": ("bass.wav", b"bass-bytes", "audio/wav"),
        "drums": ("drums.wav", b"drums-bytes", "audio/wav"),
    }
    response = client.post(
        "/api/tab/from-demucs-stems",
        data={"tabGenerationQuality": "high_accuracy"},
        files=files,
    )

    assert response.status_code == 200
    assert captured["stems"]["bass"].name == "bass.wav"
    assert captured["stems"]["drums"].name == "drums.wav"
    assert captured["source_audio_path"] is None
    assert captured["analysis_config"] is not None
    assert captured["bass_wav"].endswith("bass_analysis.wav")
    assert captured["drums_wav"].endswith("drums.wav")


def test_generate_tab_from_demucs_stems_returns_structured_debug_on_fingering_collapse(
    tmp_path, monkeypatch
):
    client = _build_client(tmp_path, monkeypatch)
    import app.main as main
    from app.services.tab_pipeline import FingeringCollapseError

    def fake_run(*_args, **_kwargs):
        raise FingeringCollapseError(
            "fingering dropped all quantized notes",
            debug_info={
                "stage_counts": {"quantized": 4, "fingered": 0, "exported": 0},
                "fingering": {
                    "dropped_reasons": {"no_fingering_candidate": 4},
                    "tuning_midi": {4: 28, 3: 33, 2: 38, 1: 43},
                    "max_fret": 24,
                },
            },
        )

    monkeypatch.setattr(main.tab_pipeline, "run", fake_run)

    files = {
        "bass": ("bass.wav", b"bass-bytes", "audio/wav"),
        "drums": ("drums.wav", b"drums-bytes", "audio/wav"),
    }
    response = client.post("/api/tab/from-demucs-stems", files=files)

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["error"] == "fingering_collapse"
    assert detail["debug_info"]["stage_counts"]["quantized"] == 4
    assert detail["debug_info"]["stage_counts"]["fingered"] == 0
    assert detail["debug_info"]["fingering"]["dropped_reasons"] == {
        "no_fingering_candidate": 4
    }
    assert detail["debug_info"]["fingering"]["tuning_midi"] == {
        "4": 28,
        "3": 33,
        "2": 38,
        "1": 43,
    }


def test_generate_tab_from_demucs_stems_requires_both_files(tmp_path, monkeypatch):
    client = _build_client(tmp_path, monkeypatch)
    response = client.post(
        "/api/tab/from-demucs-stems",
        files={"bass": ("bass.wav", b"bass-bytes", "audio/wav")},
    )
    assert response.status_code == 422


def test_generate_tab_from_demucs_stems_forwards_onset_recovery_flag(
    tmp_path, monkeypatch
):
    client = _build_client(tmp_path, monkeypatch)
    import app.main as main
    from app.services.alphatex_exporter import SyncPoint
    from app.services.rhythm_grid import Bar
    from app.services.tab_pipeline import TabPipelineResult

    captured: list[object] = []

    def fake_run(*_args, **kwargs):
        captured.append(kwargs.get("onset_recovery"))
        return TabPipelineResult(
            alphatex="\\tempo 120\n\\sync(0 0 0 0)",
            tempo_used=120.0,
            bars=[
                Bar(index=0, start_sec=0.0, end_sec=2.0, beats_sec=[0.0, 0.5, 1.0, 1.5])
            ],
            sync_points=[SyncPoint(bar_index=0, millisecond_offset=0)],
            midi_bytes=b"MThd\x00\x00\x00\x06",
            debug_info={"rhythm_source": "madmom"},
        )

    monkeypatch.setattr(main.tab_pipeline, "run", fake_run)

    files = {
        "bass": ("bass.wav", b"bass-bytes", "audio/wav"),
        "drums": ("drums.wav", b"drums-bytes", "audio/wav"),
    }
    response = client.post(
        "/api/tab/from-demucs-stems",
        data={"onset_recovery": "true"},
        files=files,
    )

    assert response.status_code == 200
    assert captured == [True]


def test_analyze_defaults_tab_generation_quality_to_standard(tmp_path, monkeypatch):
    client = _build_client(tmp_path, monkeypatch)

    import app.main as main
    from app.services.alphatex_exporter import SyncPoint
    from app.services.rhythm_grid import Bar
    from app.services.tab_pipeline import TabPipelineResult
    from app.stems import StemResult

    captured_modes: list[str] = []

    def fake_split_to_stems(audio_path, output_dir, on_progress=None, separate_fn=None):
        output_dir.mkdir(parents=True, exist_ok=True)
        bass = output_dir / "bass.wav"
        drums = output_dir / "drums.wav"
        bass.write_bytes(b"bass-bytes")
        drums.write_bytes(b"drums-bytes")
        return [
            StemResult(
                stem_key="bass", relative_path=str(bass), mime_type="audio/x-wav"
            ),
            StemResult(
                stem_key="drums", relative_path=str(drums), mime_type="audio/x-wav"
            ),
        ]

    def fake_run(*_args, **kwargs):
        captured_modes.append(kwargs.get("tab_generation_quality_mode"))
        return TabPipelineResult(
            alphatex="\\tempo 120\n\\sync(0 0 0 0)",
            tempo_used=120.0,
            bars=[
                Bar(index=0, start_sec=0.0, end_sec=2.0, beats_sec=[0.0, 0.5, 1.0, 1.5])
            ],
            sync_points=[SyncPoint(bar_index=0, millisecond_offset=0)],
            midi_bytes=b"MThd\x00\x00\x00\x06",
            fingered_notes=[],
            debug_info={"rhythm_source": "madmom"},
        )

    monkeypatch.setattr(main, "split_to_stems", fake_split_to_stems)
    monkeypatch.setattr(main.tab_pipeline, "run", fake_run)

    files = {"file": ("demo.mp3", b"audio-bytes", "audio/mpeg")}
    response = client.post(
        "/api/analyze", files=files, data={"process_mode": "analysis_and_stems"}
    )
    assert response.status_code == 200
    assert captured_modes == ["standard"]


def test_analyze_accepts_high_accuracy_tab_generation_quality(tmp_path, monkeypatch):
    client = _build_client(tmp_path, monkeypatch)

    import app.main as main
    from app.services.alphatex_exporter import SyncPoint
    from app.services.rhythm_grid import Bar
    from app.services.tab_pipeline import TabPipelineResult
    from app.stems import StemResult

    captured_modes: list[str] = []

    def fake_split_to_stems(audio_path, output_dir, on_progress=None, separate_fn=None):
        output_dir.mkdir(parents=True, exist_ok=True)
        bass = output_dir / "bass.wav"
        drums = output_dir / "drums.wav"
        bass.write_bytes(b"bass-bytes")
        drums.write_bytes(b"drums-bytes")
        return [
            StemResult(
                stem_key="bass", relative_path=str(bass), mime_type="audio/x-wav"
            ),
            StemResult(
                stem_key="drums", relative_path=str(drums), mime_type="audio/x-wav"
            ),
        ]

    def fake_run(*_args, **kwargs):
        captured_modes.append(kwargs.get("tab_generation_quality_mode"))
        return TabPipelineResult(
            alphatex="\\tempo 120\n\\sync(0 0 0 0)",
            tempo_used=120.0,
            bars=[
                Bar(index=0, start_sec=0.0, end_sec=2.0, beats_sec=[0.0, 0.5, 1.0, 1.5])
            ],
            sync_points=[SyncPoint(bar_index=0, millisecond_offset=0)],
            midi_bytes=b"MThd\x00\x00\x00\x06",
            fingered_notes=[],
            debug_info={"rhythm_source": "madmom"},
        )

    monkeypatch.setattr(main, "split_to_stems", fake_split_to_stems)
    monkeypatch.setattr(main.tab_pipeline, "run", fake_run)

    files = {"file": ("demo.mp3", b"audio-bytes", "audio/mpeg")}
    response = client.post(
        "/api/analyze",
        files=files,
        data={
            "process_mode": "analysis_and_stems",
            "tabGenerationQuality": "high_accuracy",
        },
    )
    assert response.status_code == 200
    assert captured_modes == ["high_accuracy"]


def test_analyze_accepts_high_accuracy_aggressive_tab_generation_quality(
    tmp_path, monkeypatch
):
    client = _build_client(tmp_path, monkeypatch)

    import app.main as main
    from app.services.alphatex_exporter import SyncPoint
    from app.services.rhythm_grid import Bar
    from app.services.tab_pipeline import TabPipelineResult
    from app.stems import StemResult

    captured_modes: list[str] = []

    def fake_split_to_stems(audio_path, output_dir, on_progress=None, separate_fn=None):
        output_dir.mkdir(parents=True, exist_ok=True)
        bass = output_dir / "bass.wav"
        drums = output_dir / "drums.wav"
        bass.write_bytes(b"bass-bytes")
        drums.write_bytes(b"drums-bytes")
        return [
            StemResult(
                stem_key="bass", relative_path=str(bass), mime_type="audio/x-wav"
            ),
            StemResult(
                stem_key="drums", relative_path=str(drums), mime_type="audio/x-wav"
            ),
        ]

    def fake_run(*_args, **kwargs):
        captured_modes.append(kwargs.get("tab_generation_quality_mode"))
        return TabPipelineResult(
            alphatex="\\tempo 120\n\\sync(0 0 0 0)",
            tempo_used=120.0,
            bars=[
                Bar(index=0, start_sec=0.0, end_sec=2.0, beats_sec=[0.0, 0.5, 1.0, 1.5])
            ],
            sync_points=[SyncPoint(bar_index=0, millisecond_offset=0)],
            midi_bytes=b"MThd\x00\x00\x00\x06",
            fingered_notes=[],
            debug_info={"rhythm_source": "madmom"},
        )

    monkeypatch.setattr(main, "split_to_stems", fake_split_to_stems)
    monkeypatch.setattr(main.tab_pipeline, "run", fake_run)

    files = {"file": ("demo.mp3", b"audio-bytes", "audio/mpeg")}
    response = client.post(
        "/api/analyze",
        files=files,
        data={
            "process_mode": "analysis_and_stems",
            "tabGenerationQuality": "high_accuracy_aggressive",
        },
    )
    assert response.status_code == 200
    assert captured_modes == ["high_accuracy_aggressive"]


def test_analyze_forwards_optional_onset_recovery_flag(tmp_path, monkeypatch):
    client = _build_client(tmp_path, monkeypatch)

    import app.main as main
    from app.services.alphatex_exporter import SyncPoint
    from app.services.rhythm_grid import Bar
    from app.services.tab_pipeline import TabPipelineResult
    from app.stems import StemResult

    captured_onset: list[object] = []

    def fake_split_to_stems(audio_path, output_dir, on_progress=None, separate_fn=None):
        output_dir.mkdir(parents=True, exist_ok=True)
        bass = output_dir / "bass.wav"
        drums = output_dir / "drums.wav"
        bass.write_bytes(b"bass-bytes")
        drums.write_bytes(b"drums-bytes")
        return [
            StemResult(
                stem_key="bass", relative_path=str(bass), mime_type="audio/x-wav"
            ),
            StemResult(
                stem_key="drums", relative_path=str(drums), mime_type="audio/x-wav"
            ),
        ]

    def fake_run(*_args, **kwargs):
        captured_onset.append(kwargs.get("onset_recovery"))
        return TabPipelineResult(
            alphatex="\\tempo 120\n\\sync(0 0 0 0)",
            tempo_used=120.0,
            bars=[
                Bar(index=0, start_sec=0.0, end_sec=2.0, beats_sec=[0.0, 0.5, 1.0, 1.5])
            ],
            sync_points=[SyncPoint(bar_index=0, millisecond_offset=0)],
            midi_bytes=b"MThd\x00\x00\x00\x06",
            debug_info={"rhythm_source": "madmom"},
        )

    monkeypatch.setattr(main, "split_to_stems", fake_split_to_stems)
    monkeypatch.setattr(main.tab_pipeline, "run", fake_run)

    files = {"file": ("demo.mp3", b"audio-bytes", "audio/mpeg")}
    response = client.post(
        "/api/analyze",
        files=files,
        data={
            "process_mode": "analysis_and_stems",
            "tabGenerationQuality": "high_accuracy",
            "onset_recovery": "true",
        },
    )
    assert response.status_code == 200
    assert captured_onset == [True]


def test_regenerate_song_stems_reuses_original_mix_and_persists_refreshed_stems(
    tmp_path, monkeypatch
):
    client = _build_client(tmp_path, monkeypatch)
    import app.main as main
    from app.stems import StemResult

    inserted = asyncio.run(
        main.execute(
            """
            INSERT INTO songs (user_id, title, original_filename, mime_type, audio_blob)
            VALUES (1, 'Demo Song', 'demo.mp3', 'audio/mpeg', ?)
            RETURNING id
            """,
            [b"song-audio"],
        )
    )
    song_id = int(inserted.rows[0][0])

    stale_dir = tmp_path / "stale"
    stale_dir.mkdir(parents=True, exist_ok=True)
    stale_bass = stale_dir / "bass.wav"
    stale_bass.write_bytes(b"old-bass")
    asyncio.run(
        main.execute(
            """
            INSERT INTO song_stems (song_id, stem_key, relative_path, mime_type, duration)
            VALUES (?, 'bass', ?, 'audio/x-wav', 1.0)
            """,
            [song_id, str(stale_bass)],
        )
    )

    captured: dict[str, object] = {}

    def fake_split_to_stems(audio_path, output_dir, on_progress=None, separate_fn=None):
        captured["audio_path"] = str(audio_path)
        captured["output_dir"] = str(output_dir)
        captured["audio_bytes"] = Path(audio_path).read_bytes()
        output_dir.mkdir(parents=True, exist_ok=True)
        bass = output_dir / "bass.wav"
        drums = output_dir / "drums.wav"
        bass.write_bytes(b"new-bass")
        drums.write_bytes(b"new-drums")
        return [
            StemResult(
                stem_key="bass",
                relative_path=str(bass),
                mime_type="audio/x-wav",
                duration=2.5,
            ),
            StemResult(
                stem_key="drums",
                relative_path=str(drums),
                mime_type="audio/x-wav",
                duration=2.5,
            ),
        ]

    monkeypatch.setattr(main, "split_to_stems", fake_split_to_stems)

    response = client.post(f"/api/songs/{song_id}/stems/regenerate")

    assert response.status_code == 200
    payload = response.json()
    assert [stem["stem_key"] for stem in payload["stems"]] == ["bass", "drums"]
    assert str(captured["audio_path"]).endswith(".mp3")
    assert captured["audio_bytes"] == b"song-audio"
    assert str(captured["output_dir"]).endswith(f"stems/{song_id}")

    refreshed = asyncio.run(
        main.execute(
            "SELECT stem_key, relative_path FROM song_stems WHERE song_id = ? ORDER BY stem_key ASC",
            [song_id],
        )
    )
    assert [tuple(row) for row in refreshed.rows] == [
        ("bass", str(Path(captured["output_dir"]) / "bass.wav")),
        ("drums", str(Path(captured["output_dir"]) / "drums.wav")),
    ]


def test_regenerate_song_tabs_uses_selected_stem_and_persists_new_tab(
    tmp_path, monkeypatch
):
    client = _build_client(tmp_path, monkeypatch)
    import app.main as main
    from app.services.alphatex_exporter import SyncPoint
    from app.services.rhythm_grid import Bar
    from app.services.tab_pipeline import TabPipelineResult

    inserted = asyncio.run(
        main.execute(
            """
            INSERT INTO songs (user_id, title, original_filename, mime_type, audio_blob)
            VALUES (1, 'Demo Song', 'demo.mp3', 'audio/mpeg', x'00')
            RETURNING id
            """
        )
    )
    song_id = int(inserted.rows[0][0])

    stem_dir = tmp_path / "stems" / str(song_id)
    stem_dir.mkdir(parents=True, exist_ok=True)
    bass = stem_dir / "bass.wav"
    drums = stem_dir / "drums.wav"
    bass.write_bytes(b"bass-audio")
    drums.write_bytes(b"drums-audio")
    for stem_key, path in (("bass", bass), ("drums", drums)):
        asyncio.run(
            main.execute(
                """
                INSERT INTO song_stems (song_id, stem_key, relative_path, mime_type, duration)
                VALUES (?, ?, ?, 'audio/x-wav', 2.0)
                """,
                [song_id, stem_key, str(path)],
            )
        )

    captured: dict[str, object] = {}

    def fake_build_bass_analysis_stem(
        *,
        stems,
        output_dir,
        source_audio_path=None,
        analysis_config=None,
        separate_fn=None,
    ):
        captured["stems"] = stems
        captured["output_dir"] = str(output_dir)
        analysis_path = output_dir / "bass_analysis.wav"
        analysis_path.parent.mkdir(parents=True, exist_ok=True)
        analysis_path.write_bytes(b"analysis-bass")
        return main.BassAnalysisStemResult(
            path=analysis_path,
            source_model="test-model",
            diagnostics={"selected_model": "test-model"},
        )

    def fake_run(bass_wav, drums_wav, **kwargs):
        captured["bass_wav"] = str(bass_wav)
        captured["drums_wav"] = str(drums_wav)
        captured["kwargs"] = kwargs
        return TabPipelineResult(
            alphatex="\\tempo 120\n\\sync(0 0 0 0)",
            tempo_used=120.0,
            bars=[
                Bar(index=0, start_sec=0.0, end_sec=2.0, beats_sec=[0.0, 0.5, 1.0, 1.5])
            ],
            sync_points=[SyncPoint(bar_index=0, millisecond_offset=0)],
            midi_bytes=b"MThd\x00\x00\x00\x06",
            fingered_notes=[],
            debug_info={"rhythm_source": "madmom"},
        )

    monkeypatch.setattr(main, "build_bass_analysis_stem", fake_build_bass_analysis_stem)
    monkeypatch.setattr(main.tab_pipeline, "run", fake_run)

    response = client.post(
        f"/api/songs/{song_id}/tabs/regenerate",
        json={"source_stem_key": "bass"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["tab"]["tab_format"] == "alphatex"
    assert payload["tab"]["source_stem_key"] == "bass"
    assert str(captured["stems"]["bass"]).endswith("bass.wav")
    assert str(captured["stems"]["drums"]).endswith("drums.wav")
    assert str(captured["bass_wav"]).endswith("bass_analysis.wav")
    assert str(captured["drums_wav"]).endswith("drums.wav")

    midi_rs = asyncio.run(
        main.execute(
            "SELECT source_stem_key, midi_blob FROM song_midis WHERE song_id = ? ORDER BY id DESC LIMIT 1",
            [song_id],
        )
    )
    assert tuple(midi_rs.rows[0]) == ("bass", b"MThd\x00\x00\x00\x06")

    tab_rs = asyncio.run(
        main.execute(
            """
            SELECT t.tab_blob, t.tab_format, m.source_stem_key
            FROM song_tabs t
            JOIN song_midis m ON m.id = t.source_midi_id
            WHERE t.song_id = ?
            ORDER BY t.id DESC
            LIMIT 1
            """,
            [song_id],
        )
    )
    assert tuple(tab_rs.rows[0]) == (
        b"\\tempo 120\n\\sync(0 0 0 0)",
        "alphatex",
        "bass",
    )


def test_regenerate_song_tabs_requires_drums_stem_for_rhythm_grid(
    tmp_path, monkeypatch
):
    client = _build_client(tmp_path, monkeypatch)
    import app.main as main

    inserted = asyncio.run(
        main.execute(
            """
            INSERT INTO songs (user_id, title, original_filename, mime_type, audio_blob)
            VALUES (1, 'Demo Song', 'demo.mp3', 'audio/mpeg', x'00')
            RETURNING id
            """
        )
    )
    song_id = int(inserted.rows[0][0])

    bass = tmp_path / "bass.wav"
    bass.write_bytes(b"bass-audio")
    asyncio.run(
        main.execute(
            """
            INSERT INTO song_stems (song_id, stem_key, relative_path, mime_type, duration)
            VALUES (?, 'bass', ?, 'audio/x-wav', 2.0)
            """,
            [song_id, str(bass)],
        )
    )

    response = client.post(
        f"/api/songs/{song_id}/tabs/regenerate",
        json={"source_stem_key": "bass"},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Drums stem missing; cannot build rhythm grid."


def test_regenerate_song_tabs_uses_selected_non_bass_stem_as_analysis_source(
    tmp_path, monkeypatch
):
    client = _build_client(tmp_path, monkeypatch)
    import app.main as main
    from app.services.alphatex_exporter import SyncPoint
    from app.services.rhythm_grid import Bar
    from app.services.tab_pipeline import TabPipelineResult

    inserted = asyncio.run(
        main.execute(
            """
            INSERT INTO songs (user_id, title, original_filename, mime_type, audio_blob)
            VALUES (1, 'Demo Song', 'demo.mp3', 'audio/mpeg', x'00')
            RETURNING id
            """
        )
    )
    song_id = int(inserted.rows[0][0])

    stem_dir = tmp_path / "stems" / str(song_id)
    stem_dir.mkdir(parents=True, exist_ok=True)
    guitar = stem_dir / "guitar.wav"
    drums = stem_dir / "drums.wav"
    guitar.write_bytes(b"guitar-audio")
    drums.write_bytes(b"drums-audio")
    for stem_key, path in (("guitar", guitar), ("drums", drums)):
        asyncio.run(
            main.execute(
                """
                INSERT INTO song_stems (song_id, stem_key, relative_path, mime_type, duration)
                VALUES (?, ?, ?, 'audio/x-wav', 2.0)
                """,
                [song_id, stem_key, str(path)],
            )
        )

    captured: dict[str, object] = {}

    def fake_build_bass_analysis_stem(
        *,
        stems,
        output_dir,
        source_audio_path=None,
        analysis_config=None,
        separate_fn=None,
    ):
        captured["bass_path"] = str(stems["bass"])
        captured["drums_path"] = str(stems["drums"])
        analysis_path = output_dir / "bass_analysis.wav"
        analysis_path.parent.mkdir(parents=True, exist_ok=True)
        analysis_path.write_bytes(b"analysis-bass")
        return main.BassAnalysisStemResult(
            path=analysis_path,
            source_model="test-model",
            diagnostics={"selected_model": "test-model"},
        )

    def fake_run(*_args, **_kwargs):
        return TabPipelineResult(
            alphatex="\\tempo 120\n\\sync(0 0 0 0)",
            tempo_used=120.0,
            bars=[
                Bar(index=0, start_sec=0.0, end_sec=2.0, beats_sec=[0.0, 0.5, 1.0, 1.5])
            ],
            sync_points=[SyncPoint(bar_index=0, millisecond_offset=0)],
            midi_bytes=b"MThd\x00\x00\x00\x06",
            fingered_notes=[],
            debug_info={"rhythm_source": "madmom"},
        )

    monkeypatch.setattr(main, "build_bass_analysis_stem", fake_build_bass_analysis_stem)
    monkeypatch.setattr(main.tab_pipeline, "run", fake_run)

    response = client.post(
        f"/api/songs/{song_id}/tabs/regenerate",
        json={"source_stem_key": "guitar"},
    )

    assert response.status_code == 200
    assert captured["bass_path"].endswith("guitar.wav")
    assert captured["drums_path"].endswith("drums.wav")
