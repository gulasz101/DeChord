from pathlib import Path
import wave

import numpy as np
import pytest
import app.midi as midi_mod

from app.midi import _apply_spectral_octave_verification
from app.midi import _estimate_monophonic_notes_from_wav
from app.midi import _estimate_monophonic_notes_legacy_from_audio
from app.midi import _get_pitch_stability_config
from app.midi import _preprocess_bass_for_fallback_transcription
from app.midi import _stabilize_octaves_sequence
from app.midi import _smooth_midi_track_viterbi
from app.midi import transcribe_bass_stem_to_midi_detailed
from app.midi import transcribe_bass_stem_to_midi


def test_transcribe_bass_stem_returns_midi_bytes(tmp_path: Path):
    bass_stem = tmp_path / "bass.wav"
    bass_stem.write_bytes(b"fake-audio")

    midi_bytes = transcribe_bass_stem_to_midi(
        bass_stem,
        transcribe_fn=lambda _in_path, _out_path: _out_path.write_bytes(b"MThd\x00\x00\x00\x06"),
    )

    assert midi_bytes.startswith(b"MThd")


def test_transcribe_bass_stem_detailed_reports_primary_engine(tmp_path: Path) -> None:
    bass_stem = tmp_path / "bass.wav"
    bass_stem.write_bytes(b"fake-audio")

    result = transcribe_bass_stem_to_midi_detailed(
        bass_stem,
        transcribe_fn=lambda _in_path, out_path: out_path.write_bytes(b"MThd\x00\x00\x00\x06"),
    )

    assert result.engine_used == "basic_pitch"
    assert result.midi_bytes.startswith(b"MThd")
    assert result.diagnostics["transcription_engine_used"] == "basic_pitch"


def test_transcribe_bass_stem_raises_when_input_missing(tmp_path: Path):
    missing = tmp_path / "missing.wav"

    with pytest.raises(RuntimeError, match="Bass stem file missing"):
        transcribe_bass_stem_to_midi(missing)


def test_transcribe_bass_stem_wraps_engine_failure(tmp_path: Path):
    bass_stem = tmp_path / "bass.wav"
    bass_stem.write_bytes(b"fake-audio")

    def broken(_input_path: Path, _output_path: Path) -> None:
        raise RuntimeError("engine crashed")

    with pytest.raises(RuntimeError, match="Bass MIDI transcription failed: engine crashed"):
        transcribe_bass_stem_to_midi(bass_stem, transcribe_fn=broken)


def test_transcribe_bass_stem_uses_fallback_when_primary_dependency_missing(tmp_path: Path):
    bass_stem = tmp_path / "bass.wav"
    bass_stem.write_bytes(b"fake-audio")

    def missing(_input_path: Path, _output_path: Path) -> None:
        raise ModuleNotFoundError("No module named 'basic_pitch'")

    def fallback(_input_path: Path, output_path: Path) -> None:
        output_path.write_bytes(b"MThd\x00\x00\x00\x06")

    midi_bytes = transcribe_bass_stem_to_midi(
        bass_stem,
        transcribe_fn=missing,
        fallback_fn=fallback,
    )
    assert midi_bytes.startswith(b"MThd")


def test_transcribe_bass_stem_detailed_reports_fallback_engine(tmp_path: Path) -> None:
    bass_stem = tmp_path / "bass.wav"
    bass_stem.write_bytes(b"fake-audio")

    def missing(_input_path: Path, _output_path: Path) -> None:
        raise RuntimeError("Stem runtime dependency missing: No module named 'basic_pitch'")

    def fallback(_input_path: Path, output_path: Path) -> dict[str, object]:
        output_path.write_bytes(b"MThd\x00\x00\x00\x06")
        return {"fallback_octave_corrections_applied": 7}

    result = transcribe_bass_stem_to_midi_detailed(
        bass_stem,
        transcribe_fn=missing,
        fallback_fn=fallback,
    )
    assert result.engine_used == "fallback_frequency"
    assert result.midi_bytes.startswith(b"MThd")
    assert result.diagnostics["fallback_octave_corrections_applied"] == 7


def test_smooth_midi_track_viterbi_penalizes_isolated_octave_jump() -> None:
    midi_track = np.array([40.0, 40.2, 52.1, 40.1, 39.9], dtype=float)
    voiced_prob = np.array([0.95, 0.95, 0.95, 0.95, 0.95], dtype=float)

    smoothed = _smooth_midi_track_viterbi(midi_track, voiced_prob)

    assert smoothed[2] in (40, 41)


def test_apply_spectral_octave_verification_shifts_when_half_has_more_energy() -> None:
    midi_track = np.array([52, 52, 52], dtype=int)
    freqs = np.array([80.0, 160.0], dtype=float)
    spectrogram = np.array(
        [
            [10.0, 12.0, 11.0],
            [3.0, 2.0, 2.5],
        ],
        dtype=float,
    )

    corrected, correction_count = _apply_spectral_octave_verification(
        midi_track,
        freqs,
        spectrogram,
    )

    assert correction_count == 3
    assert corrected.tolist() == [40, 40, 40]


def test_stabilize_octaves_sequence_corrects_local_outlier() -> None:
    events = [
        (0.0, 0.4, 40, 0.8),
        (0.5, 0.8, 52, 0.8),
        (0.9, 1.2, 41, 0.8),
    ]

    corrected, correction_count = _stabilize_octaves_sequence(events, window_sec=1.5)

    assert correction_count == 1
    assert corrected[1][2] == 40


def test_legacy_monophonic_estimator_detects_simple_bass_tone() -> None:
    sr = 22050
    t = np.linspace(0.0, 0.8, int(sr * 0.8), endpoint=False)
    audio = 0.2 * np.sin(2.0 * np.pi * 55.0 * t)

    events = _estimate_monophonic_notes_legacy_from_audio(audio.astype(np.float32), sr=sr)

    assert len(events) >= 1
    assert 28 <= events[0][2] <= 76


def test_estimate_monophonic_notes_short_clip_uses_legacy_backstop(tmp_path: Path) -> None:
    sr = 22050
    t = np.linspace(0.0, 0.7, int(sr * 0.7), endpoint=False)
    audio = (0.25 * np.sin(2.0 * np.pi * 55.0 * t) * 32767.0).astype(np.int16)
    wav_path = tmp_path / "short.wav"
    with wave.open(str(wav_path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sr)
        wav_file.writeframes(audio.tobytes())

    events, diagnostics = _estimate_monophonic_notes_from_wav(wav_path)

    assert events
    assert diagnostics["fallback_legacy_backstop_used"] in (0, 1)


def test_estimate_monophonic_notes_from_wav_uses_pitch_stabilizer(tmp_path: Path, monkeypatch) -> None:
    sr = 22050
    duration_sec = 4.0
    t = np.linspace(0.0, duration_sec, int(sr * duration_sec), endpoint=False)
    audio = (0.22 * np.sin(2.0 * np.pi * 55.0 * t) * 32767.0).astype(np.int16)
    wav_path = tmp_path / "long.wav"
    with wave.open(str(wav_path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sr)
        wav_file.writeframes(audio.tobytes())

    called: dict[str, object] = {}

    def fake_stabilizer(**kwargs):
        called["frame_count"] = len(kwargs["frame_midi"])
        called["config"] = kwargs["config"]
        return (
            np.full(len(kwargs["frame_midi"]), 40, dtype=int),
            [(0.0, duration_sec, 40, 0.92)],
            {
                "stabilizer_enabled": True,
                "octave_corrections_applied": 2,
                "harmonic_rechecks_applied": 1,
                "suppressed_short_transitions": 3,
                "merged_gap_regions": 1,
            },
        )

    monkeypatch.setattr(midi_mod, "stabilize_bass_pitch_track", fake_stabilizer)

    events, diagnostics = _estimate_monophonic_notes_from_wav(wav_path)

    assert events == [(0.0, duration_sec, 40, 0.92)]
    assert called["frame_count"]
    assert diagnostics["fallback_pitch_stability_enabled"] == 1
    assert diagnostics["fallback_pitch_short_transition_suppressions"] == 3
    assert diagnostics["fallback_pitch_gap_merges"] == 1


def test_preprocess_bass_for_fallback_transcription_uses_bass_focused_filters(
    tmp_path: Path,
    monkeypatch,
) -> None:
    source_path = tmp_path / "bass.wav"
    source_path.write_bytes(b"fake-audio")
    output_path = tmp_path / "bass_mono.wav"
    called: dict[str, object] = {}

    def fake_run(cmd, capture_output, text):
        called["cmd"] = cmd
        output_path.write_bytes(b"RIFF")

        class Result:
            returncode = 0
            stderr = ""

        return Result()

    monkeypatch.setattr(midi_mod.subprocess, "run", fake_run)

    _preprocess_bass_for_fallback_transcription(source_path, output_path)

    ffmpeg_cmd = " ".join(called["cmd"])
    assert "highpass=f=35" in ffmpeg_cmd
    assert "lowpass=f=300" in ffmpeg_cmd
    assert "-ac 1" in ffmpeg_cmd
    assert "-ar 22050" in ffmpeg_cmd


def test_pitch_stability_config_parses_raw_recall_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DECHORD_RAW_NOTE_RECALL_ENABLE", "1")
    monkeypatch.setenv("DECHORD_RAW_NOTE_MIN_CONFIDENCE", "0.15")
    monkeypatch.setenv("DECHORD_RAW_NOTE_MIN_DURATION_MS", "35")
    monkeypatch.setenv("DECHORD_RAW_NOTE_ALLOW_WEAK_BASS_CANDIDATES", "1")
    monkeypatch.setenv("DECHORD_RAW_NOTE_SPARSE_REGION_BOOST_ENABLE", "1")
    monkeypatch.setenv("DECHORD_DENSE_CANDIDATE_SPARSE_REGION_THRESHOLD_MS", "180")
    monkeypatch.setenv("DECHORD_DENSE_CANDIDATE_SUPPORT_RELAXATION", "0.2")

    config = _get_pitch_stability_config()

    assert config.raw_note_recall_enable is True
    assert config.raw_note_min_confidence == pytest.approx(0.15)
    assert config.raw_note_min_duration_ms == 35
    assert config.raw_note_allow_weak_bass_candidates is True
    assert config.raw_note_sparse_region_boost_enable is True
    assert config.dense_candidate_sparse_region_threshold_ms == 180
    assert config.dense_candidate_support_relaxation == pytest.approx(0.2)


def test_pitch_stability_config_falls_back_for_invalid_raw_recall_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DECHORD_RAW_NOTE_RECALL_ENABLE", "maybe")
    monkeypatch.setenv("DECHORD_RAW_NOTE_MIN_CONFIDENCE", "-1")
    monkeypatch.setenv("DECHORD_RAW_NOTE_MIN_DURATION_MS", "0")
    monkeypatch.setenv("DECHORD_RAW_NOTE_ALLOW_WEAK_BASS_CANDIDATES", "maybe")
    monkeypatch.setenv("DECHORD_RAW_NOTE_SPARSE_REGION_BOOST_ENABLE", "wat")
    monkeypatch.setenv("DECHORD_DENSE_CANDIDATE_SPARSE_REGION_THRESHOLD_MS", "-10")
    monkeypatch.setenv("DECHORD_DENSE_CANDIDATE_SUPPORT_RELAXATION", "7.5")

    config = _get_pitch_stability_config()

    assert config.raw_note_recall_enable is False
    assert 0.0 <= config.raw_note_min_confidence <= 1.0
    assert config.raw_note_min_duration_ms > 0
    assert config.raw_note_allow_weak_bass_candidates is False
    assert config.raw_note_sparse_region_boost_enable is False
    assert config.dense_candidate_sparse_region_threshold_ms > 0
    assert 0.0 <= config.dense_candidate_support_relaxation <= 1.0
