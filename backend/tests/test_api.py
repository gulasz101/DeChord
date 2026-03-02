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
    response = client.post("/api/analyze", files=files, data={"process_mode": "analysis_only"})
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


def test_analyze_with_stems_reports_split_stage(tmp_path, monkeypatch):
    client = _build_client(tmp_path, monkeypatch)

    import app.main as main

    def fake_split_to_stems(audio_path, output_dir, on_progress=None, separate_fn=None):
        if on_progress:
            on_progress(10, "warmup")
            on_progress(100, "done")
        return []

    monkeypatch.setattr(main, "split_to_stems", fake_split_to_stems)

    files = {"file": ("demo.mp3", b"audio-bytes", "audio/mpeg")}
    response = client.post("/api/analyze", files=files, data={"process_mode": "analysis_and_stems"})
    assert response.status_code == 200
    job_id = response.json()["job_id"]

    status = client.get(f"/api/status/{job_id}")
    assert status.status_code == 200
    payload = status.json()
    assert payload["status"] == "complete"
    assert payload["stage"] == "complete"
    assert payload["stems_status"] == "complete"
    assert "splitting_stems" in payload["stage_history"]


def test_analyze_with_stems_failure_keeps_analysis_complete(tmp_path, monkeypatch):
    client = _build_client(tmp_path, monkeypatch)

    import app.main as main

    def fake_split_to_stems(audio_path, output_dir, on_progress=None, separate_fn=None):
        raise RuntimeError("stem split failed")

    monkeypatch.setattr(main, "split_to_stems", fake_split_to_stems)

    files = {"file": ("demo.mp3", b"audio-bytes", "audio/mpeg")}
    response = client.post("/api/analyze", files=files, data={"process_mode": "analysis_and_stems"})
    assert response.status_code == 200
    job_id = response.json()["job_id"]

    status = client.get(f"/api/status/{job_id}")
    assert status.status_code == 200
    payload = status.json()
    assert payload["status"] == "complete"
    assert payload["stems_status"] == "failed"
    assert payload["error"] is None

    result = client.get(f"/api/result/{job_id}")
    assert result.status_code == 200
    assert result.json()["tempo"] == 120


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
            StemResult(stem_key="drums", relative_path=str(drums), mime_type="audio/x-wav"),
            StemResult(stem_key="vocals", relative_path=str(vocals), mime_type="audio/x-wav"),
        ]

    monkeypatch.setattr(main, "split_to_stems", fake_split_to_stems)

    files = {"file": ("demo.mp3", b"audio-bytes", "audio/mpeg")}
    response = client.post("/api/analyze", files=files, data={"process_mode": "analysis_and_stems"})
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
