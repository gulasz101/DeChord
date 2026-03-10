import importlib
import asyncio
import threading
import sys
import types
import io
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient


def _build_client(tmp_path: Path, monkeypatch):
    db_path = tmp_path / "api-test.db"
    monkeypatch.setenv("DECHORD_DB_URL", f"file:{db_path}")
    if "torch" not in sys.modules:
        class _FakeTorchTensor:
            pass

        sys.modules["torch"] = types.SimpleNamespace(
            Tensor=_FakeTorchTensor,
            backends=types.SimpleNamespace(mps=types.SimpleNamespace(is_available=lambda: False)),
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


def test_list_bands_projects_and_project_songs(tmp_path, monkeypatch):
    client = _build_client(tmp_path, monkeypatch)

    files = {"file": ("demo.mp3", b"audio-bytes", "audio/mpeg")}
    created = client.post("/api/analyze", files=files, data={"process_mode": "analysis_only"})
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
            StemResult(stem_key="bass", relative_path=str(bass), mime_type="audio/x-wav"),
            StemResult(stem_key="drums", relative_path=str(drums), mime_type="audio/x-wav"),
        ]

    def fake_run(*_args, **_kwargs):
        return TabPipelineResult(
            alphatex="\\tempo 120\n\\sync(0 0 0 0)",
            tempo_used=120.0,
            bars=[Bar(index=0, start_sec=0.0, end_sec=2.0, beats_sec=[0.0, 0.5, 1.0, 1.5])],
            sync_points=[SyncPoint(bar_index=0, millisecond_offset=0)],
            midi_bytes=b"MThd\x00\x00\x00\x06",
            fingered_notes=[],
            debug_info={"rhythm_source": "madmom"},
        )

    monkeypatch.setattr(main, "split_to_stems", fake_split_to_stems)
    monkeypatch.setattr(main.tab_pipeline, "run", fake_run)

    files = {"file": ("demo.mp3", b"audio-bytes", "audio/mpeg")}
    created = client.post("/api/analyze", files=files, data={"process_mode": "analysis_and_stems"})
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
            StemResult(stem_key="bass", relative_path=str(bass), mime_type="audio/x-wav"),
            StemResult(stem_key="drums", relative_path=str(drums), mime_type="audio/x-wav"),
        ]

    def fake_run(*_args, **_kwargs):
        return TabPipelineResult(
            alphatex="\\tempo 120\n\\sync(0 0 0 0)",
            tempo_used=120.0,
            bars=[Bar(index=0, start_sec=0.0, end_sec=2.0, beats_sec=[0.0, 0.5, 1.0, 1.5])],
            sync_points=[SyncPoint(bar_index=0, millisecond_offset=0)],
            midi_bytes=b"MThd\x00\x00\x00\x06",
            fingered_notes=[],
            debug_info={"rhythm_source": "madmom"},
        )

    monkeypatch.setattr(main, "split_to_stems", fake_split_to_stems)
    monkeypatch.setattr(main.tab_pipeline, "run", fake_run)

    files = {"file": ("demo.mp3", b"audio-bytes", "audio/mpeg")}
    response = client.post("/api/analyze", files=files, data={"process_mode": "analysis_and_stems"})
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
    response = client.post("/api/analyze", files=files, data={"process_mode": "analysis_and_stems"})
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


def test_analyze_with_stems_routes_bass_analysis_wav_into_tab_pipeline(tmp_path, monkeypatch):
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
            StemResult(stem_key="bass", relative_path=str(bass), mime_type="audio/x-wav"),
            StemResult(stem_key="drums", relative_path=str(drums), mime_type="audio/x-wav"),
            StemResult(stem_key="other", relative_path=str(other), mime_type="audio/x-wav"),
        ]

    def fake_build_bass_analysis_stem(*, stems, output_dir, source_audio_path=None, analysis_config=None, separate_fn=None):
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
            bars=[Bar(index=0, start_sec=0.0, end_sec=2.0, beats_sec=[0.0, 0.5, 1.0, 1.5])],
            sync_points=[SyncPoint(bar_index=0, millisecond_offset=0)],
            midi_bytes=b"MThd\x00\x00\x00\x06",
            debug_info={"rhythm_source": "madmom"},
        )

    monkeypatch.setattr(main, "split_to_stems", fake_split_to_stems)
    monkeypatch.setattr(main, "build_bass_analysis_stem", fake_build_bass_analysis_stem)
    monkeypatch.setattr(main.tab_pipeline, "run", fake_run)

    files = {"file": ("demo.mp3", b"audio-bytes", "audio/mpeg")}
    response = client.post("/api/analyze", files=files, data={"process_mode": "analysis_and_stems"})

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
            StemResult(stem_key="bass", relative_path=str(bass), mime_type="audio/x-wav"),
            StemResult(stem_key="drums", relative_path=str(drums), mime_type="audio/x-wav"),
        ]

    def fake_build_bass_analysis_stem(*, stems, output_dir, source_audio_path=None, analysis_config=None, separate_fn=None):
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
            bars=[Bar(index=0, start_sec=0.0, end_sec=2.0, beats_sec=[0.0, 0.5, 1.0, 1.5])],
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
        data={"process_mode": "analysis_and_stems", "tabGenerationQuality": "high_accuracy"},
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
            StemResult(stem_key="bass", relative_path=str(bass), mime_type="audio/x-wav"),
            StemResult(stem_key="drums", relative_path=str(drums), mime_type="audio/x-wav"),
        ]

    def fake_build_bass_analysis_stem(*, stems, output_dir, source_audio_path=None, analysis_config=None, separate_fn=None):
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
            bars=[Bar(index=0, start_sec=0.0, end_sec=2.0, beats_sec=[0.0, 0.5, 1.0, 1.5])],
            sync_points=[SyncPoint(bar_index=0, millisecond_offset=0)],
            midi_bytes=b"MThd\x00\x00\x00\x06",
            debug_info={"rhythm_source": "madmom"},
        )

    monkeypatch.setattr(main, "split_to_stems", fake_split_to_stems)
    monkeypatch.setattr(main, "build_bass_analysis_stem", fake_build_bass_analysis_stem)
    monkeypatch.setattr(main.tab_pipeline, "run", fake_run)

    files = {"file": ("demo.mp3", b"audio-bytes", "audio/mpeg")}
    response = client.post("/api/analyze", files=files, data={"process_mode": "analysis_and_stems"})

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


def test_generate_tab_from_demucs_stems_endpoint_persists_midi_and_alphatex(tmp_path, monkeypatch):
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
            bars=[Bar(index=0, start_sec=0.0, end_sec=2.0, beats_sec=[0.0, 0.5, 1.0, 1.5])],
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
        data={"song_id": song_id, "bpm": "120", "time_signature": "4/4", "subdivision": "16", "max_fret": "24"},
        files=files,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["tempo_used"] == 120.0
    assert payload["alphatex"].startswith("\\tempo")
    assert payload["sync_points"][0]["bar_index"] == 0

    midi_rs = asyncio.run(
        main.execute("SELECT midi_blob FROM song_midis WHERE song_id = ? ORDER BY id DESC LIMIT 1", [song_id])
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


def test_generate_tab_from_demucs_stems_routes_analysis_bass_into_tab_pipeline(tmp_path, monkeypatch):
    client = _build_client(tmp_path, monkeypatch)
    import app.main as main
    from app.services.alphatex_exporter import SyncPoint
    from app.services.rhythm_grid import Bar
    from app.services.tab_pipeline import TabPipelineResult

    captured: dict[str, object] = {}

    def fake_build_bass_analysis_stem(*, stems, output_dir, source_audio_path=None, analysis_config=None, separate_fn=None):
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
            bars=[Bar(index=0, start_sec=0.0, end_sec=2.0, beats_sec=[0.0, 0.5, 1.0, 1.5])],
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


def test_generate_tab_from_demucs_stems_returns_structured_debug_on_fingering_collapse(tmp_path, monkeypatch):
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
    assert detail["debug_info"]["fingering"]["dropped_reasons"] == {"no_fingering_candidate": 4}
    assert detail["debug_info"]["fingering"]["tuning_midi"] == {"4": 28, "3": 33, "2": 38, "1": 43}


def test_generate_tab_from_demucs_stems_requires_both_files(tmp_path, monkeypatch):
    client = _build_client(tmp_path, monkeypatch)
    response = client.post(
        "/api/tab/from-demucs-stems",
        files={"bass": ("bass.wav", b"bass-bytes", "audio/wav")},
    )
    assert response.status_code == 422


def test_generate_tab_from_demucs_stems_forwards_onset_recovery_flag(tmp_path, monkeypatch):
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
            bars=[Bar(index=0, start_sec=0.0, end_sec=2.0, beats_sec=[0.0, 0.5, 1.0, 1.5])],
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
            StemResult(stem_key="bass", relative_path=str(bass), mime_type="audio/x-wav"),
            StemResult(stem_key="drums", relative_path=str(drums), mime_type="audio/x-wav"),
        ]

    def fake_run(*_args, **kwargs):
        captured_modes.append(kwargs.get("tab_generation_quality_mode"))
        return TabPipelineResult(
            alphatex="\\tempo 120\n\\sync(0 0 0 0)",
            tempo_used=120.0,
            bars=[Bar(index=0, start_sec=0.0, end_sec=2.0, beats_sec=[0.0, 0.5, 1.0, 1.5])],
            sync_points=[SyncPoint(bar_index=0, millisecond_offset=0)],
            midi_bytes=b"MThd\x00\x00\x00\x06",
            fingered_notes=[],
            debug_info={"rhythm_source": "madmom"},
        )

    monkeypatch.setattr(main, "split_to_stems", fake_split_to_stems)
    monkeypatch.setattr(main.tab_pipeline, "run", fake_run)

    files = {"file": ("demo.mp3", b"audio-bytes", "audio/mpeg")}
    response = client.post("/api/analyze", files=files, data={"process_mode": "analysis_and_stems"})
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
            StemResult(stem_key="bass", relative_path=str(bass), mime_type="audio/x-wav"),
            StemResult(stem_key="drums", relative_path=str(drums), mime_type="audio/x-wav"),
        ]

    def fake_run(*_args, **kwargs):
        captured_modes.append(kwargs.get("tab_generation_quality_mode"))
        return TabPipelineResult(
            alphatex="\\tempo 120\n\\sync(0 0 0 0)",
            tempo_used=120.0,
            bars=[Bar(index=0, start_sec=0.0, end_sec=2.0, beats_sec=[0.0, 0.5, 1.0, 1.5])],
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
        data={"process_mode": "analysis_and_stems", "tabGenerationQuality": "high_accuracy"},
    )
    assert response.status_code == 200
    assert captured_modes == ["high_accuracy"]


def test_analyze_accepts_high_accuracy_aggressive_tab_generation_quality(tmp_path, monkeypatch):
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
            StemResult(stem_key="bass", relative_path=str(bass), mime_type="audio/x-wav"),
            StemResult(stem_key="drums", relative_path=str(drums), mime_type="audio/x-wav"),
        ]

    def fake_run(*_args, **kwargs):
        captured_modes.append(kwargs.get("tab_generation_quality_mode"))
        return TabPipelineResult(
            alphatex="\\tempo 120\n\\sync(0 0 0 0)",
            tempo_used=120.0,
            bars=[Bar(index=0, start_sec=0.0, end_sec=2.0, beats_sec=[0.0, 0.5, 1.0, 1.5])],
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
        data={"process_mode": "analysis_and_stems", "tabGenerationQuality": "high_accuracy_aggressive"},
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
            StemResult(stem_key="bass", relative_path=str(bass), mime_type="audio/x-wav"),
            StemResult(stem_key="drums", relative_path=str(drums), mime_type="audio/x-wav"),
        ]

    def fake_run(*_args, **kwargs):
        captured_onset.append(kwargs.get("onset_recovery"))
        return TabPipelineResult(
            alphatex="\\tempo 120\n\\sync(0 0 0 0)",
            tempo_used=120.0,
            bars=[Bar(index=0, start_sec=0.0, end_sec=2.0, beats_sec=[0.0, 0.5, 1.0, 1.5])],
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


def test_regenerate_song_stems_reuses_original_mix_and_persists_refreshed_stems(tmp_path, monkeypatch):
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
            StemResult(stem_key="bass", relative_path=str(bass), mime_type="audio/x-wav", duration=2.5),
            StemResult(stem_key="drums", relative_path=str(drums), mime_type="audio/x-wav", duration=2.5),
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


def test_regenerate_song_tabs_uses_selected_stem_and_persists_new_tab(tmp_path, monkeypatch):
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

    def fake_build_bass_analysis_stem(*, stems, output_dir, source_audio_path=None, analysis_config=None, separate_fn=None):
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
            bars=[Bar(index=0, start_sec=0.0, end_sec=2.0, beats_sec=[0.0, 0.5, 1.0, 1.5])],
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
    assert tuple(tab_rs.rows[0]) == (b"\\tempo 120\n\\sync(0 0 0 0)", "alphatex", "bass")


def test_regenerate_song_tabs_requires_drums_stem_for_rhythm_grid(tmp_path, monkeypatch):
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


def test_regenerate_song_tabs_uses_selected_non_bass_stem_as_analysis_source(tmp_path, monkeypatch):
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

    def fake_build_bass_analysis_stem(*, stems, output_dir, source_audio_path=None, analysis_config=None, separate_fn=None):
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
            bars=[Bar(index=0, start_sec=0.0, end_sec=2.0, beats_sec=[0.0, 0.5, 1.0, 1.5])],
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
