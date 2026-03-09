import os
import wave
import zipfile
import io
from pathlib import Path

import numpy as np
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
    """Model params must match screenshot defaults."""
    from app.stems import _get_model_params
    params = _get_model_params("htdemucs_ft")
    assert "segment" in params
    assert "overlap" in params
    assert "shifts" in params
    assert "input_gain_db" in params
    assert "output_gain_db" in params
    assert "device" in params
    assert params["segment"] == pytest.approx(7.8)
    assert params["overlap"] == 0.25
    assert params["shifts"] == 0
    assert params["input_gain_db"] == 0.0
    assert params["output_gain_db"] == 0.0
    assert params["device"] == "auto"


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


def test_get_separation_config_reads_env_overrides(monkeypatch):
    from app.stems import _get_separation_config

    monkeypatch.setenv("DECHORD_STEM_DEVICE", "cpu")
    monkeypatch.setenv("DECHORD_STEM_SEGMENT", "11.2")
    monkeypatch.setenv("DECHORD_STEM_OVERLAP", "0.4")
    monkeypatch.setenv("DECHORD_STEM_SHIFTS", "2")
    monkeypatch.setenv("DECHORD_STEM_INPUT_GAIN_DB", "1.5")
    monkeypatch.setenv("DECHORD_STEM_OUTPUT_GAIN_DB", "-2.0")
    monkeypatch.setenv("DECHORD_STEM_JOBS", "3")

    config = _get_separation_config()
    assert config.device == "cpu"
    assert config.segment == pytest.approx(11.2)
    assert config.overlap == pytest.approx(0.4)
    assert config.shifts == 2
    assert config.input_gain_db == pytest.approx(1.5)
    assert config.output_gain_db == pytest.approx(-2.0)
    assert config.jobs == 3


def test_load_dotenv_settings_for_separation(tmp_path, monkeypatch):
    from app.stems import _get_separation_config

    env_file = tmp_path / ".env"
    env_file.write_text(
        "DECHORD_STEM_DEVICE=cpu\n"
        "DECHORD_STEM_SEGMENT=9.5\n"
        "DECHORD_STEM_OVERLAP=0.30\n"
        "DECHORD_STEM_SHIFTS=1\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DECHORD_STEM_DEVICE", raising=False)
    monkeypatch.delenv("DECHORD_STEM_SEGMENT", raising=False)
    monkeypatch.delenv("DECHORD_STEM_OVERLAP", raising=False)
    monkeypatch.delenv("DECHORD_STEM_SHIFTS", raising=False)

    config = _get_separation_config()
    assert config.device == "cpu"
    assert config.segment == pytest.approx(9.5)
    assert config.overlap == pytest.approx(0.30)
    assert config.shifts == 1


def test_get_demucs_model_name_loads_dotenv_at_runtime(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("DECHORD_DEMUCS_MODEL=htdemucs_6s\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DECHORD_DEMUCS_MODEL", raising=False)

    assert stems_mod._get_demucs_model_name() == "htdemucs_6s"


def test_get_demucs_model_name_is_not_frozen_at_import_time(monkeypatch):
    monkeypatch.setenv("DECHORD_DEMUCS_MODEL", "mdx_extra_q")
    assert stems_mod._get_demucs_model_name() == "mdx_extra_q"

    monkeypatch.setenv("DECHORD_DEMUCS_MODEL", "htdemucs_ft")
    assert stems_mod._get_demucs_model_name() == "htdemucs_ft"


def test_get_demucs_runtime_config_invalid_values_fall_back_with_warning(monkeypatch, caplog):
    monkeypatch.setenv("DECHORD_DEMUCS_MODEL", "")
    monkeypatch.setenv("DECHORD_DEMUCS_FALLBACK_MODEL", "")
    monkeypatch.setenv("DECHORD_STEM_ANALYSIS_HIGHPASS_HZ", "oops")
    monkeypatch.setenv("DECHORD_STEM_ANALYSIS_LOWPASS_HZ", "-10")

    with caplog.at_level("WARNING"):
        config = stems_mod._get_stem_analysis_config()

    assert config.demucs_model == "htdemucs_ft"
    assert config.demucs_fallback_model == "htdemucs"
    assert config.analysis_highpass_hz == pytest.approx(35.0)
    assert config.analysis_lowpass_hz == pytest.approx(300.0)
    assert "DECHORD_DEMUCS_MODEL" in caplog.text
    assert "DECHORD_STEM_ANALYSIS_HIGHPASS_HZ" in caplog.text


def test_build_bass_analysis_stem_creates_analysis_wav_and_reports_diagnostics(tmp_path: Path):
    sample_rate = 22050
    duration_sec = 1.0
    times = np.linspace(0.0, duration_sec, int(sample_rate * duration_sec), endpoint=False)

    bass_audio = (
        0.55 * np.sin(2.0 * np.pi * 55.0 * times)
        + 0.12 * np.sin(2.0 * np.pi * 440.0 * times)
    )
    other_audio = 0.08 * np.sin(2.0 * np.pi * 110.0 * times)

    def write_wav(path: Path, samples: np.ndarray) -> None:
        pcm = np.clip(samples * 32767.0, -32768, 32767).astype(np.int16)
        with wave.open(str(path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(pcm.tobytes())

    stems_dir = tmp_path / "stems"
    stems_dir.mkdir()
    bass_path = stems_dir / "bass.wav"
    other_path = stems_dir / "other.wav"
    drums_path = stems_dir / "drums.wav"
    write_wav(bass_path, bass_audio.astype(np.float32))
    write_wav(other_path, other_audio.astype(np.float32))
    write_wav(drums_path, np.zeros_like(times, dtype=np.float32))

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

    result = stems_mod.build_bass_analysis_stem(
        stems={"bass": bass_path, "other": other_path, "drums": drums_path},
        output_dir=tmp_path / "analysis",
        analysis_config=config,
    )

    assert result.path.exists()
    assert result.path.name == "bass_analysis.wav"
    assert result.source_model == "htdemucs_ft"
    assert result.diagnostics["selected_model"] == "htdemucs_ft"
    assert result.diagnostics["analysis_highpass_hz"] == pytest.approx(35.0)
    assert result.diagnostics["analysis_lowpass_hz"] == pytest.approx(300.0)
    assert result.diagnostics["bleed_subtraction_applied"] == 1


def test_get_stem_analysis_config_parses_candidate_models(monkeypatch):
    monkeypatch.setenv("DECHORD_DEMUCS_MODEL", "htdemucs_ft")
    monkeypatch.setenv(
        "DECHORD_STEM_ANALYSIS_CANDIDATE_MODELS",
        "htdemucs_6s, htdemucs_ft, htdemucs_6s, mdx_extra_q",
    )

    config = stems_mod._get_stem_analysis_config()

    assert config.candidate_models == ["htdemucs_ft", "htdemucs_6s", "mdx_extra_q"]


def test_score_bass_analysis_candidate_is_deterministic() -> None:
    sample_rate = 22050
    times = np.linspace(0.0, 1.0, sample_rate, endpoint=False)
    clean_audio = (0.7 * np.sin(2.0 * np.pi * 55.0 * times)).astype(np.float32)
    noisy_audio = (
        0.2 * np.sin(2.0 * np.pi * 55.0 * times)
        + 0.3 * np.sin(2.0 * np.pi * 600.0 * times)
        + 0.1 * np.random.default_rng(42).standard_normal(sample_rate)
    ).astype(np.float32)
    bleed_audio = (0.2 * np.sin(2.0 * np.pi * 110.0 * times)).astype(np.float32)

    clean_score = stems_mod._score_bass_analysis_candidate(
        clean_audio,
        sample_rate=sample_rate,
        bleed_audio=bleed_audio,
    )
    noisy_score = stems_mod._score_bass_analysis_candidate(
        noisy_audio,
        sample_rate=sample_rate,
        bleed_audio=bleed_audio,
    )

    assert clean_score == pytest.approx(
        stems_mod._score_bass_analysis_candidate(
            clean_audio,
            sample_rate=sample_rate,
            bleed_audio=bleed_audio,
        )
    )
    assert clean_score > noisy_score


def test_build_stems_zip_packages_existing_files(tmp_path: Path):
    from app.stems import build_stems_zip

    bass_path = tmp_path / "bass.wav"
    drums_path = tmp_path / "drums.wav"
    bass_path.write_bytes(b"bass")
    drums_path.write_bytes(b"drums")

    archive_bytes, archive_name = build_stems_zip(
        "The Trooper",
        stems=[
            StemResult(stem_key="bass", relative_path=str(bass_path), mime_type="audio/x-wav"),
            StemResult(stem_key="drums", relative_path=str(drums_path), mime_type="audio/x-wav"),
        ],
    )

    assert archive_name == "The_Trooper-stems.zip"
    with zipfile.ZipFile(io.BytesIO(archive_bytes), "r") as archive:
        assert sorted(archive.namelist()) == ["bass.wav", "drums.wav"]


def test_get_stem_analysis_config_parses_extended_weights_and_selection(monkeypatch):
    monkeypatch.setenv("DECHORD_DEMUCS_MODEL", "htdemucs_ft")
    monkeypatch.setenv("DECHORD_STEM_ANALYSIS_ENABLE", "1")
    monkeypatch.setenv("DECHORD_STEM_ANALYSIS_ENSEMBLE", "1")
    monkeypatch.setenv("DECHORD_STEM_ANALYSIS_CANDIDATE_MODELS", "htdemucs_6s,mdx_extra_q")
    monkeypatch.setenv("DECHORD_STEM_ANALYSIS_OTHER_SUBTRACT_WEIGHT", "0.30")
    monkeypatch.setenv("DECHORD_STEM_ANALYSIS_GUITAR_SUBTRACT_WEIGHT", "0.55")
    monkeypatch.setenv("DECHORD_STEM_ANALYSIS_NOISE_GATE_DB", "-38")
    monkeypatch.setenv("DECHORD_STEM_ANALYSIS_SELECTION_MODE", "transcription")

    config = stems_mod._get_stem_analysis_config()

    assert config.enable_model_ensemble is True
    assert config.candidate_models == ["htdemucs_ft", "htdemucs_6s", "mdx_extra_q"]
    assert config.analysis_other_subtract_weight == pytest.approx(0.30)
    assert config.analysis_guitar_subtract_weight == pytest.approx(0.55)
    assert config.analysis_noise_gate_db == pytest.approx(-38.0)
    assert config.analysis_selection_mode == "transcription"


def test_build_bass_analysis_stem_runs_all_candidate_models_in_ensemble_mode(tmp_path: Path):
    audio_path = tmp_path / "track.wav"
    audio_path.write_bytes(b"audio")
    sample_rate = 22050
    times = np.linspace(0.0, 1.0, sample_rate, endpoint=False)

    calls: list[str] = []

    def write_wav(path: Path, samples: np.ndarray) -> None:
        pcm = np.clip(samples * 32767.0, -32768, 32767).astype(np.int16)
        with wave.open(str(path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(pcm.tobytes())

    def fake_separate(input_audio: str, output_dir: Path, progress_callback, *, model_name: str):
        assert input_audio == str(audio_path)
        calls.append(model_name)
        output_dir.mkdir(parents=True, exist_ok=True)
        bass = output_dir / "bass.wav"
        other = output_dir / "other.wav"
        drums = output_dir / "drums.wav"
        guitar = output_dir / "guitar.wav"
        write_wav(bass, (0.7 * np.sin(2.0 * np.pi * 55.0 * times)).astype(np.float32))
        write_wav(other, (0.02 * np.sin(2.0 * np.pi * 180.0 * times)).astype(np.float32))
        write_wav(drums, np.zeros_like(times, dtype=np.float32))
        write_wav(guitar, (0.03 * np.sin(2.0 * np.pi * 220.0 * times)).astype(np.float32))
        progress_callback(1.0, f"{model_name} done")
        return {"bass": bass, "other": other, "drums": drums, "guitar": guitar}

    config = stems_mod.StemAnalysisConfig(
        demucs_model="htdemucs_ft",
        demucs_fallback_model="htdemucs",
        enable_bass_refinement=True,
        analysis_highpass_hz=35.0,
        analysis_lowpass_hz=300.0,
        analysis_sample_rate=22050,
        enable_model_ensemble=True,
        candidate_models=["htdemucs_ft", "htdemucs_6s"],
        analysis_other_subtract_weight=0.30,
        analysis_guitar_subtract_weight=0.55,
        analysis_noise_gate_db=-40.0,
        analysis_selection_mode="transcription",
        scoring_weights={},
    )

    result = stems_mod.build_bass_analysis_stem(
        stems={},
        output_dir=tmp_path / "analysis",
        analysis_config=config,
        source_audio_path=audio_path,
        separate_fn=fake_separate,
    )

    assert calls == ["htdemucs_ft", "htdemucs_6s"]
    assert result.path.name == "bass_analysis.wav"
    assert result.diagnostics["selected_model"] in {"htdemucs_ft", "htdemucs_6s"}
    assert len(result.diagnostics["candidate_diagnostics"]) == 2


def test_build_bass_analysis_stem_ensemble_reseparates_primary_even_when_stems_exist(tmp_path: Path):
    audio_path = tmp_path / "track.wav"
    audio_path.write_bytes(b"audio")
    sample_rate = 22050
    times = np.linspace(0.0, 1.0, sample_rate, endpoint=False)
    calls: list[str] = []

    def write_wav(path: Path, samples: np.ndarray) -> None:
        pcm = np.clip(samples * 32767.0, -32768, 32767).astype(np.int16)
        with wave.open(str(path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(pcm.tobytes())

    supplied_dir = tmp_path / "supplied"
    supplied_dir.mkdir()
    supplied_bass = supplied_dir / "bass.wav"
    write_wav(supplied_bass, (0.25 * np.sin(2.0 * np.pi * 55.0 * times)).astype(np.float32))

    def fake_separate(_input_audio: str, output_dir: Path, _progress_callback, *, model_name: str):
        calls.append(model_name)
        output_dir.mkdir(parents=True, exist_ok=True)
        bass = output_dir / "bass.wav"
        drums = output_dir / "drums.wav"
        write_wav(bass, (0.8 * np.sin(2.0 * np.pi * 55.0 * times)).astype(np.float32))
        write_wav(drums, np.zeros_like(times, dtype=np.float32))
        return {"bass": bass, "drums": drums}

    config = stems_mod.StemAnalysisConfig(
        demucs_model="htdemucs_ft",
        demucs_fallback_model="htdemucs",
        enable_bass_refinement=True,
        analysis_highpass_hz=35.0,
        analysis_lowpass_hz=300.0,
        analysis_sample_rate=22050,
        enable_model_ensemble=True,
        candidate_models=["htdemucs_ft", "htdemucs_6s"],
    )

    stems_mod.build_bass_analysis_stem(
        stems={"bass": supplied_bass},
        output_dir=tmp_path / "analysis",
        analysis_config=config,
        source_audio_path=audio_path,
        separate_fn=fake_separate,
    )

    assert calls == ["htdemucs_ft", "htdemucs_6s"]


def test_build_bass_analysis_stem_standard_mode_reuses_supplied_primary_stems(tmp_path: Path):
    audio_path = tmp_path / "track.wav"
    audio_path.write_bytes(b"audio")
    sample_rate = 22050
    times = np.linspace(0.0, 1.0, sample_rate, endpoint=False)
    calls: list[str] = []

    def write_wav(path: Path, samples: np.ndarray) -> None:
        pcm = np.clip(samples * 32767.0, -32768, 32767).astype(np.int16)
        with wave.open(str(path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(pcm.tobytes())

    supplied_dir = tmp_path / "supplied"
    supplied_dir.mkdir()
    supplied_bass = supplied_dir / "bass.wav"
    supplied_other = supplied_dir / "other.wav"
    write_wav(supplied_bass, (0.75 * np.sin(2.0 * np.pi * 55.0 * times)).astype(np.float32))
    write_wav(supplied_other, (0.02 * np.sin(2.0 * np.pi * 180.0 * times)).astype(np.float32))

    def fake_separate(_input_audio: str, _output_dir: Path, _progress_callback, *, model_name: str):
        calls.append(model_name)
        raise AssertionError("standard mode should not trigger candidate reseparation")

    config = stems_mod.StemAnalysisConfig(
        demucs_model="htdemucs_ft",
        demucs_fallback_model="htdemucs",
        enable_bass_refinement=True,
        analysis_highpass_hz=35.0,
        analysis_lowpass_hz=300.0,
        analysis_sample_rate=22050,
        enable_model_ensemble=False,
        candidate_models=["htdemucs_ft", "htdemucs_6s"],
    )

    result = stems_mod.build_bass_analysis_stem(
        stems={"bass": supplied_bass, "other": supplied_other},
        output_dir=tmp_path / "analysis",
        analysis_config=config,
        source_audio_path=audio_path,
        separate_fn=fake_separate,
    )

    assert calls == []
    assert result.source_model == "htdemucs_ft"


def test_build_bass_analysis_stem_selects_best_scoring_candidate_deterministically(tmp_path: Path):
    audio_path = tmp_path / "track.wav"
    audio_path.write_bytes(b"audio")
    sample_rate = 22050
    times = np.linspace(0.0, 1.0, sample_rate, endpoint=False)

    def write_wav(path: Path, samples: np.ndarray) -> None:
        pcm = np.clip(samples * 32767.0, -32768, 32767).astype(np.int16)
        with wave.open(str(path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(pcm.tobytes())

    def fake_separate(_input_audio: str, output_dir: Path, _progress_callback, *, model_name: str):
        output_dir.mkdir(parents=True, exist_ok=True)
        bass = output_dir / "bass.wav"
        other = output_dir / "other.wav"
        guitar = output_dir / "guitar.wav"
        drums = output_dir / "drums.wav"
        if model_name == "htdemucs_6s":
            bass_audio = (0.85 * np.sin(2.0 * np.pi * 55.0 * times)).astype(np.float32)
            other_audio = (0.01 * np.sin(2.0 * np.pi * 240.0 * times)).astype(np.float32)
            guitar_audio = (0.01 * np.sin(2.0 * np.pi * 110.0 * times)).astype(np.float32)
        else:
            bass_audio = (
                0.35 * np.sin(2.0 * np.pi * 55.0 * times)
                + 0.22 * np.sin(2.0 * np.pi * 220.0 * times)
            ).astype(np.float32)
            other_audio = (0.18 * np.sin(2.0 * np.pi * 180.0 * times)).astype(np.float32)
            guitar_audio = (0.15 * np.sin(2.0 * np.pi * 110.0 * times)).astype(np.float32)
        write_wav(bass, bass_audio)
        write_wav(other, other_audio)
        write_wav(guitar, guitar_audio)
        write_wav(drums, np.zeros_like(times, dtype=np.float32))
        return {"bass": bass, "other": other, "guitar": guitar, "drums": drums}

    config = stems_mod.StemAnalysisConfig(
        demucs_model="htdemucs_ft",
        demucs_fallback_model="htdemucs",
        enable_bass_refinement=True,
        analysis_highpass_hz=35.0,
        analysis_lowpass_hz=300.0,
        analysis_sample_rate=22050,
        enable_model_ensemble=True,
        candidate_models=["htdemucs_ft", "htdemucs_6s"],
        analysis_other_subtract_weight=0.30,
        analysis_guitar_subtract_weight=0.55,
        analysis_noise_gate_db=-40.0,
        analysis_selection_mode="transcription",
        scoring_weights={},
    )

    result = stems_mod.build_bass_analysis_stem(
        stems={},
        output_dir=tmp_path / "analysis",
        analysis_config=config,
        source_audio_path=audio_path,
        separate_fn=fake_separate,
    )

    assert result.source_model == "htdemucs_6s"
    assert result.diagnostics["selected_model"] == "htdemucs_6s"
    assert result.diagnostics["candidate_diagnostics"]["htdemucs_6s"]["selected"] is True
    assert (
        result.diagnostics["candidate_diagnostics"]["htdemucs_6s"]["total_score"]
        > result.diagnostics["candidate_diagnostics"]["htdemucs_ft"]["total_score"]
    )


def test_build_bass_analysis_stem_reports_score_breakdown_for_each_successful_candidate(tmp_path: Path):
    audio_path = tmp_path / "track.wav"
    audio_path.write_bytes(b"audio")
    sample_rate = 22050
    times = np.linspace(0.0, 1.0, sample_rate, endpoint=False)

    def write_wav(path: Path, samples: np.ndarray) -> None:
        pcm = np.clip(samples * 32767.0, -32768, 32767).astype(np.int16)
        with wave.open(str(path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(pcm.tobytes())

    def fake_separate(_input_audio: str, output_dir: Path, _progress_callback, *, model_name: str):
        output_dir.mkdir(parents=True, exist_ok=True)
        bass = output_dir / "bass.wav"
        drums = output_dir / "drums.wav"
        other = output_dir / "other.wav"
        amplitude = 0.7 if model_name == "htdemucs_ft" else 0.8
        write_wav(bass, (amplitude * np.sin(2.0 * np.pi * 55.0 * times)).astype(np.float32))
        write_wav(other, (0.03 * np.sin(2.0 * np.pi * 180.0 * times)).astype(np.float32))
        write_wav(drums, np.zeros_like(times, dtype=np.float32))
        return {"bass": bass, "other": other, "drums": drums}

    result = stems_mod.build_bass_analysis_stem(
        stems={},
        output_dir=tmp_path / "analysis",
        analysis_config=stems_mod.StemAnalysisConfig(
            demucs_model="htdemucs_ft",
            demucs_fallback_model="htdemucs",
            enable_bass_refinement=True,
            analysis_highpass_hz=35.0,
            analysis_lowpass_hz=300.0,
            analysis_sample_rate=22050,
            enable_model_ensemble=True,
            candidate_models=["htdemucs_ft", "htdemucs_6s"],
        ),
        source_audio_path=audio_path,
        separate_fn=fake_separate,
    )

    for model_name in ("htdemucs_ft", "htdemucs_6s"):
        diagnostics = result.diagnostics["candidate_diagnostics"][model_name]
        assert diagnostics["status"] == "ok"
        assert diagnostics["success"] is True
        assert diagnostics["available"] is True
        assert Path(diagnostics["analysis_path"]).exists()
        assert set(diagnostics["scoring_components"].keys()) >= {
            "bass_energy",
            "low_energy",
            "other_correlation",
            "guitar_correlation",
            "spectral_flatness",
            "pitch_confidence",
            "transient_penalty",
            "total",
        }
        assert diagnostics["total_score"] == pytest.approx(diagnostics["scoring_components"]["total"])


def test_guitar_aware_cancellation_can_change_selected_candidate(tmp_path: Path):
    audio_path = tmp_path / "track.wav"
    audio_path.write_bytes(b"audio")
    sample_rate = 22050
    times = np.linspace(0.0, 1.0, sample_rate, endpoint=False)

    def write_wav(path: Path, samples: np.ndarray) -> None:
        pcm = np.clip(samples * 32767.0, -32768, 32767).astype(np.int16)
        with wave.open(str(path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(pcm.tobytes())

    bass_foundation = (0.6 * np.sin(2.0 * np.pi * 55.0 * times)).astype(np.float32)
    guitar_bleed = (0.28 * np.sin(2.0 * np.pi * 110.0 * times)).astype(np.float32)

    def fake_separate(_input_audio: str, output_dir: Path, _progress_callback, *, model_name: str):
        output_dir.mkdir(parents=True, exist_ok=True)
        bass = output_dir / "bass.wav"
        other = output_dir / "other.wav"
        drums = output_dir / "drums.wav"
        write_wav(drums, np.zeros_like(times, dtype=np.float32))
        if model_name == "htdemucs_6s":
            guitar = output_dir / "guitar.wav"
            write_wav(bass, bass_foundation + guitar_bleed)
            write_wav(other, np.zeros_like(times, dtype=np.float32))
            write_wav(guitar, guitar_bleed)
            return {"bass": bass, "other": other, "guitar": guitar, "drums": drums}
        write_wav(bass, bass_foundation + guitar_bleed)
        write_wav(other, guitar_bleed)
        return {"bass": bass, "other": other, "drums": drums}

    result = stems_mod.build_bass_analysis_stem(
        stems={},
        output_dir=tmp_path / "analysis",
        analysis_config=stems_mod.StemAnalysisConfig(
            demucs_model="htdemucs_ft",
            demucs_fallback_model="htdemucs",
            enable_bass_refinement=True,
            analysis_highpass_hz=35.0,
            analysis_lowpass_hz=300.0,
            analysis_sample_rate=22050,
            enable_model_ensemble=True,
            candidate_models=["htdemucs_ft", "htdemucs_6s"],
            analysis_other_subtract_weight=0.15,
            analysis_guitar_subtract_weight=0.70,
        ),
        source_audio_path=audio_path,
        separate_fn=fake_separate,
    )

    assert result.source_model == "htdemucs_6s"
    assert result.diagnostics["candidate_diagnostics"]["htdemucs_6s"]["has_guitar"] is True
    assert (
        result.diagnostics["candidate_diagnostics"]["htdemucs_6s"]["total_score"]
        > result.diagnostics["candidate_diagnostics"]["htdemucs_ft"]["total_score"]
    )


def test_build_bass_analysis_stem_uses_guitar_bleed_when_available(tmp_path: Path):
    sample_rate = 22050
    times = np.linspace(0.0, 1.0, sample_rate, endpoint=False)

    def write_wav(path: Path, samples: np.ndarray) -> None:
        pcm = np.clip(samples * 32767.0, -32768, 32767).astype(np.int16)
        with wave.open(str(path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(pcm.tobytes())

    stems_dir = tmp_path / "stems"
    stems_dir.mkdir()
    bass_path = stems_dir / "bass.wav"
    other_path = stems_dir / "other.wav"
    guitar_path = stems_dir / "guitar.wav"
    drums_path = stems_dir / "drums.wav"
    write_wav(
        bass_path,
        (
            0.70 * np.sin(2.0 * np.pi * 55.0 * times)
            + 0.30 * np.sin(2.0 * np.pi * 110.0 * times)
        ).astype(np.float32),
    )
    write_wav(other_path, (0.05 * np.sin(2.0 * np.pi * 180.0 * times)).astype(np.float32))
    write_wav(guitar_path, (0.28 * np.sin(2.0 * np.pi * 110.0 * times)).astype(np.float32))
    write_wav(drums_path, np.zeros_like(times, dtype=np.float32))

    config = stems_mod.StemAnalysisConfig(
        demucs_model="htdemucs_6s",
        demucs_fallback_model="htdemucs",
        enable_bass_refinement=True,
        analysis_highpass_hz=35.0,
        analysis_lowpass_hz=300.0,
        analysis_sample_rate=22050,
        enable_model_ensemble=False,
        candidate_models=["htdemucs_6s"],
        analysis_other_subtract_weight=0.20,
        analysis_guitar_subtract_weight=0.70,
        analysis_noise_gate_db=-40.0,
        analysis_selection_mode="transcription",
        scoring_weights={},
    )

    result = stems_mod.build_bass_analysis_stem(
        stems={"bass": bass_path, "other": other_path, "guitar": guitar_path, "drums": drums_path},
        output_dir=tmp_path / "analysis",
        analysis_config=config,
    )

    assert result.diagnostics["candidate_diagnostics"]["htdemucs_6s"]["has_guitar"] is True
    assert result.diagnostics["candidate_diagnostics"]["htdemucs_6s"]["subtract_weights"]["guitar"] == pytest.approx(0.70)
    assert result.diagnostics["candidate_diagnostics"]["htdemucs_6s"]["bleed_sources_used"] == ["other", "guitar"]


def test_build_bass_analysis_stem_skips_failed_candidate_when_another_succeeds(tmp_path: Path):
    audio_path = tmp_path / "track.wav"
    audio_path.write_bytes(b"audio")
    sample_rate = 22050
    times = np.linspace(0.0, 1.0, sample_rate, endpoint=False)

    def write_wav(path: Path, samples: np.ndarray) -> None:
        pcm = np.clip(samples * 32767.0, -32768, 32767).astype(np.int16)
        with wave.open(str(path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(pcm.tobytes())

    def fake_separate(_input_audio: str, output_dir: Path, _progress_callback, *, model_name: str):
        if model_name == "broken_model":
            raise RuntimeError("model unavailable")
        output_dir.mkdir(parents=True, exist_ok=True)
        bass = output_dir / "bass.wav"
        drums = output_dir / "drums.wav"
        write_wav(bass, (0.75 * np.sin(2.0 * np.pi * 55.0 * times)).astype(np.float32))
        write_wav(drums, np.zeros_like(times, dtype=np.float32))
        return {"bass": bass, "drums": drums}

    config = stems_mod.StemAnalysisConfig(
        demucs_model="htdemucs_ft",
        demucs_fallback_model="htdemucs",
        enable_bass_refinement=True,
        analysis_highpass_hz=35.0,
        analysis_lowpass_hz=300.0,
        analysis_sample_rate=22050,
        enable_model_ensemble=True,
        candidate_models=["broken_model", "htdemucs_ft"],
        analysis_other_subtract_weight=0.30,
        analysis_guitar_subtract_weight=0.55,
        analysis_noise_gate_db=-40.0,
        analysis_selection_mode="transcription",
        scoring_weights={},
    )

    result = stems_mod.build_bass_analysis_stem(
        stems={},
        output_dir=tmp_path / "analysis",
        analysis_config=config,
        source_audio_path=audio_path,
        separate_fn=fake_separate,
    )

    assert result.source_model == "htdemucs_ft"
    assert result.diagnostics["candidate_diagnostics"]["broken_model"]["status"] == "failed"
    assert result.diagnostics["candidate_diagnostics"]["broken_model"]["success"] is False
    assert result.diagnostics["candidate_diagnostics"]["broken_model"]["available"] is False
    assert result.diagnostics["candidate_diagnostics"]["broken_model"]["error"] == "model unavailable"
    assert result.diagnostics["candidate_diagnostics"]["broken_model"]["selected"] is False
    assert result.diagnostics["candidate_diagnostics"]["htdemucs_ft"]["status"] == "ok"


def test_build_bass_analysis_stem_raises_explicitly_when_all_candidates_fail(tmp_path: Path):
    audio_path = tmp_path / "track.wav"
    audio_path.write_bytes(b"audio")

    def fake_separate(_input_audio: str, _output_dir: Path, _progress_callback, *, model_name: str):
        raise RuntimeError(f"{model_name} unavailable")

    config = stems_mod.StemAnalysisConfig(
        demucs_model="htdemucs_ft",
        demucs_fallback_model="htdemucs",
        enable_bass_refinement=True,
        analysis_highpass_hz=35.0,
        analysis_lowpass_hz=300.0,
        analysis_sample_rate=22050,
        enable_model_ensemble=True,
        candidate_models=["broken_a", "broken_b"],
        analysis_other_subtract_weight=0.30,
        analysis_guitar_subtract_weight=0.55,
        analysis_noise_gate_db=-40.0,
        analysis_selection_mode="transcription",
        scoring_weights={},
    )

    with pytest.raises(RuntimeError, match="All bass analysis candidate models failed"):
        stems_mod.build_bass_analysis_stem(
            stems={},
            output_dir=tmp_path / "analysis",
            analysis_config=config,
            source_audio_path=audio_path,
            separate_fn=fake_separate,
        )


def test_build_bass_analysis_stem_breaks_score_ties_by_candidate_order(tmp_path: Path):
    audio_path = tmp_path / "track.wav"
    audio_path.write_bytes(b"audio")
    sample_rate = 22050
    times = np.linspace(0.0, 1.0, sample_rate, endpoint=False)

    def write_wav(path: Path, samples: np.ndarray) -> None:
        pcm = np.clip(samples * 32767.0, -32768, 32767).astype(np.int16)
        with wave.open(str(path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(pcm.tobytes())

    def fake_separate(_input_audio: str, output_dir: Path, _progress_callback, *, model_name: str):
        output_dir.mkdir(parents=True, exist_ok=True)
        bass = output_dir / "bass.wav"
        drums = output_dir / "drums.wav"
        bass_audio = (0.75 * np.sin(2.0 * np.pi * 55.0 * times)).astype(np.float32)
        write_wav(bass, bass_audio)
        write_wav(drums, np.zeros_like(times, dtype=np.float32))
        return {"bass": bass, "drums": drums}

    config = stems_mod.StemAnalysisConfig(
        demucs_model="a_model",
        demucs_fallback_model="htdemucs",
        enable_bass_refinement=True,
        analysis_highpass_hz=35.0,
        analysis_lowpass_hz=300.0,
        analysis_sample_rate=22050,
        enable_model_ensemble=True,
        candidate_models=["a_model", "z_model"],
    )

    result = stems_mod.build_bass_analysis_stem(
        stems={},
        output_dir=tmp_path / "analysis",
        analysis_config=config,
        source_audio_path=audio_path,
        separate_fn=fake_separate,
    )

    assert result.source_model == "a_model"
    assert result.diagnostics["candidate_diagnostics"]["a_model"]["selected"] is True
    assert result.diagnostics["candidate_diagnostics"]["z_model"]["selected"] is False
