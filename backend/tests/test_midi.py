import math
import struct
import tempfile
import wave
from pathlib import Path

import pytest

from app.midi import _estimate_monophonic_notes_from_wav, transcribe_bass_stem_to_midi


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


# --- Librosa-based transcription tests ---


def _make_sine_wav(path: Path, freq: float, duration: float = 1.0, sr: int = 22050) -> None:
    """Write a mono 16-bit WAV file containing a pure sine tone."""
    n_samples = int(sr * duration)
    samples = [int(32767 * 0.5 * math.sin(2 * math.pi * freq * t / sr)) for t in range(n_samples)]
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sr)
        wav.writeframes(struct.pack(f"{len(samples)}h", *samples))


def test_librosa_transcription_detects_single_note():
    """The improved transcriber should detect a sustained A2 (110 Hz, MIDI 45)."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        path = Path(f.name)
    try:
        _make_sine_wav(path, freq=110.0, duration=1.0)
        events = _estimate_monophonic_notes_from_wav(path)
        assert len(events) >= 1
        # At least one event should be close to MIDI 45 (A2 = 110 Hz)
        assert any(abs(e[2] - 45) <= 1 for e in events), (
            f"Expected MIDI ~45, got: {[e[2] for e in events]}"
        )
    finally:
        path.unlink(missing_ok=True)


def test_librosa_transcription_detects_two_notes():
    """The transcriber should detect two different pitches played sequentially."""
    sr = 22050
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        path = Path(f.name)
    try:
        # Build a WAV with A2 (110 Hz) for 0.8s, 150ms silence, then E3 (164.8 Hz) for 0.8s.
        # Using well-separated pitches and longer durations for reliable pyin detection.
        freq_a = 110.0   # A2 = MIDI 45
        freq_b = 164.81  # E3 = MIDI 52
        n_note = int(sr * 0.8)
        n_gap = int(sr * 0.15)  # 150ms silence gap
        samples: list[int] = []
        for t in range(n_note):
            samples.append(int(32767 * 0.5 * math.sin(2 * math.pi * freq_a * t / sr)))
        samples.extend([0] * n_gap)
        for t in range(n_note):
            samples.append(int(32767 * 0.5 * math.sin(2 * math.pi * freq_b * t / sr)))

        with wave.open(str(path), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sr)
            wav.writeframes(struct.pack(f"{len(samples)}h", *samples))

        events = _estimate_monophonic_notes_from_wav(path)
        midi_notes = [e[2] for e in events]
        # Should detect at least two distinct note events
        assert len(events) >= 2, f"Expected >=2 events, got {len(events)}: {events}"
        # The two detected notes should be different from each other
        unique_notes = set(midi_notes)
        assert len(unique_notes) >= 2, (
            f"Expected at least 2 distinct pitches, got: {midi_notes}"
        )
    finally:
        path.unlink(missing_ok=True)


def test_librosa_transcription_returns_empty_for_silence():
    """Silence should produce no note events."""
    sr = 22050
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        path = Path(f.name)
    try:
        n_samples = int(sr * 1.0)
        samples = [0] * n_samples
        with wave.open(str(path), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sr)
            wav.writeframes(struct.pack(f"{n_samples}h", *samples))

        events = _estimate_monophonic_notes_from_wav(path)
        assert events == []
    finally:
        path.unlink(missing_ok=True)


def test_librosa_transcription_clamps_to_bass_range():
    """Notes outside bass range should be clamped to MIDI 28-67."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        path = Path(f.name)
    try:
        # Very low frequency at ~41 Hz — near bass range boundary
        _make_sine_wav(path, freq=41.0, duration=1.0)
        events = _estimate_monophonic_notes_from_wav(path)
        for _start, _end, midi_note in events:
            assert 28 <= midi_note <= 67, f"MIDI {midi_note} out of bass range"
    finally:
        path.unlink(missing_ok=True)
