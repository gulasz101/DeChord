import importlib
import asyncio
import threading
from pathlib import Path

from fastapi.testclient import TestClient


def _build_client(tmp_path: Path, monkeypatch):
    db_path = tmp_path / "api-test.db"
    monkeypatch.setenv("DECHORD_DB_URL", f"file:{db_path}")

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


def test_analyze_persists_song_and_analysis(tmp_path, monkeypatch):
    client = _build_client(tmp_path, monkeypatch)

    files = {"file": ("demo.mp3", b"audio-bytes", "audio/mpeg")}
    response = client.post("/api/analyze", files=files)
    assert response.status_code == 200
    body = response.json()
    assert "job_id" in body
    assert "song_id" in body

    status = client.get(f"/api/status/{body['job_id']}")
    assert status.status_code == 200
    assert status.json()["status"] == "complete"

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


def test_status_not_found(tmp_path, monkeypatch):
    client = _build_client(tmp_path, monkeypatch)
    response = client.get("/api/status/nonexistent")
    assert response.status_code == 404


def test_result_not_found(tmp_path, monkeypatch):
    client = _build_client(tmp_path, monkeypatch)
    response = client.get("/api/result/nonexistent")
    assert response.status_code == 404
