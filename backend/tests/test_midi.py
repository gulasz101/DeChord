from pathlib import Path

import numpy as np
import pytest

from app.midi import _apply_spectral_octave_verification
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
