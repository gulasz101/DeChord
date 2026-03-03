from pathlib import Path

import pytest

from app.midi import transcribe_bass_stem_to_midi


def test_transcribe_bass_stem_returns_midi_bytes(tmp_path: Path):
    bass_stem = tmp_path / "bass.wav"
    bass_stem.write_bytes(b"fake-audio")

    midi_bytes = transcribe_bass_stem_to_midi(
        bass_stem,
        transcribe_fn=lambda _in_path, _out_path: _out_path.write_bytes(b"MThd\x00\x00\x00\x06"),
    )

    assert midi_bytes.startswith(b"MThd")


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
