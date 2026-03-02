import os
from pathlib import Path

import pytest

import app.stems as stems_mod
from app.stems import check_stem_runtime_ready, split_to_stems, StemResult


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

    monkeypatch.setenv("DECHORD_STEM_FALLBACK_ON_ERROR", "1")
    monkeypatch.delenv("DECHORD_STEM_ENGINE", raising=False)

    stems = split_to_stems(audio_path=str(audio_path), output_dir=out_dir)

    assert len(stems) == 1
    assert stems[0].stem_key == "drums"


def test_split_to_stems_raises_when_demucs_fails_without_fallback_opt_in(tmp_path: Path, monkeypatch):
    audio_path = tmp_path / "track.wav"
    audio_path.write_bytes(b"fake-audio")
    out_dir = tmp_path / "stems"

    def fake_demucs(_input_audio: str, _output_dir: Path, _progress_callback):
        raise RuntimeError("model download failed")

    monkeypatch.setattr(stems_mod, "_separate_with_demucs", fake_demucs)
    monkeypatch.delenv("DECHORD_STEM_FALLBACK_ON_ERROR", raising=False)
    monkeypatch.delenv("DECHORD_STEM_ENGINE", raising=False)

    with pytest.raises(RuntimeError, match="Demucs stem separation failed"):
        split_to_stems(audio_path=str(audio_path), output_dir=out_dir)


def test_detect_device_returns_valid_string():
    """Device detection must return a valid device string."""
    from app.stems import _detect_device
    device = _detect_device()
    assert device in ("mps", "cuda", "cpu")


def test_get_model_params_returns_expected_keys():
    """Model params must include overlap and shifts."""
    from app.stems import _get_model_params
    params = _get_model_params("htdemucs_ft")
    assert "overlap" in params
    assert "shifts" in params
    assert params["overlap"] == 0.25
    assert params["shifts"] >= 1


def test_split_to_stems_with_injected_separator(tmp_path):
    """split_to_stems with injected separate_fn skips real demucs."""
    audio_file = tmp_path / "test.mp3"
    audio_file.write_bytes(b"fake-audio")
    output_dir = tmp_path / "stems"

    def fake_separate(audio_path, out_dir, progress_callback):
        out_dir.mkdir(parents=True, exist_ok=True)
        for stem in ("vocals", "drums", "bass", "other"):
            (out_dir / f"{stem}.wav").write_bytes(b"wav-data")
        progress_callback(1.0, "done")
        return {s: out_dir / f"{s}.wav" for s in ("vocals", "drums", "bass", "other")}

    results = split_to_stems(
        audio_path=str(audio_file),
        output_dir=output_dir,
        separate_fn=fake_separate,
    )
    assert len(results) == 4
    assert all(isinstance(r, StemResult) for r in results)
    keys = {r.stem_key for r in results}
    assert keys == {"vocals", "drums", "bass", "other"}


def test_default_engine_is_demucs(monkeypatch):
    """Default engine should be demucs, not fallback."""
    monkeypatch.delenv("DECHORD_STEM_ENGINE", raising=False)
    assert os.getenv("DECHORD_STEM_ENGINE", "demucs") == "demucs"
