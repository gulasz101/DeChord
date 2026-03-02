from pathlib import Path

import pytest

import app.stems as stems_mod
from app.stems import check_stem_runtime_ready, split_to_stems


def test_split_to_stems_uses_adapter_and_reports_progress(tmp_path: Path):
    audio_path = tmp_path / "track.wav"
    audio_path.write_bytes(b"fake-audio")
    out_dir = tmp_path / "stems"

    progress_events: list[tuple[float, str]] = []

    def fake_separate(
        input_audio: str,
        output_dir: Path,
        progress_callback,
    ) -> dict[str, Path]:
        assert input_audio == str(audio_path)
        output_dir.mkdir(parents=True, exist_ok=True)
        vocals = output_dir / "vocals.wav"
        drums = output_dir / "drums.wav"
        vocals.write_bytes(b"vocals")
        drums.write_bytes(b"drums")
        progress_callback(0.25, "loading model")
        progress_callback(0.75, "running separation")
        return {"vocals": vocals, "drums": drums}

    stems = split_to_stems(
        audio_path=str(audio_path),
        output_dir=out_dir,
        on_progress=lambda pct, msg: progress_events.append((pct, msg)),
        separate_fn=fake_separate,
    )

    assert [stem.stem_key for stem in stems] == ["drums", "vocals"]
    assert all(stem.relative_path.endswith(".wav") for stem in stems)
    assert all(stem.mime_type == "audio/x-wav" for stem in stems)

    assert progress_events[0] == (0.0, "Preparing stem separation...")
    assert progress_events[-1] == (100.0, "Stem separation complete")


def test_check_stem_runtime_ready_reports_missing_dependency():
    def fake_import(_name: str):
        raise ModuleNotFoundError("No module named 'lameenc'")

    with pytest.raises(RuntimeError, match="lameenc"):
        check_stem_runtime_ready(import_module=fake_import)


def test_split_to_stems_wraps_missing_dependency_error(tmp_path: Path):
    audio_path = tmp_path / "track.wav"
    audio_path.write_bytes(b"fake-audio")
    out_dir = tmp_path / "stems"

    def fake_separate(_input_audio: str, _output_dir: Path, _progress_callback):
        raise ModuleNotFoundError("No module named 'lameenc'")

    with pytest.raises(RuntimeError, match="lameenc"):
        split_to_stems(
            audio_path=str(audio_path),
            output_dir=out_dir,
            separate_fn=fake_separate,
        )


def test_split_to_stems_falls_back_when_demucs_runner_fails(tmp_path: Path, monkeypatch):
    audio_path = tmp_path / "track.wav"
    audio_path.write_bytes(b"fake-audio")
    out_dir = tmp_path / "stems"

    def fake_demucs(_input_audio: str, _output_dir: Path, _progress_callback):
        raise RuntimeError("model download failed")

    def fake_fallback(input_audio: str, output_dir: Path, progress_callback):
        assert input_audio == str(audio_path)
        output_dir.mkdir(parents=True, exist_ok=True)
        drums = output_dir / "drums.wav"
        drums.write_bytes(b"drums")
        progress_callback(1.0, "Fallback stem split complete")
        return {"drums": drums}

    monkeypatch.setattr(stems_mod, "_separate_with_demucs", fake_demucs)
    monkeypatch.setattr(stems_mod, "_split_with_ffmpeg_fallback", fake_fallback)

    stems = split_to_stems(
        audio_path=str(audio_path),
        output_dir=out_dir,
    )

    assert len(stems) == 1
    assert stems[0].stem_key == "drums"
