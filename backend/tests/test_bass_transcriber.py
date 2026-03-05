from __future__ import annotations

from pathlib import Path

import pytest

from app.services.bass_transcriber import BasicPitchTranscriber, RawNoteEvent


def test_basic_pitch_transcriber_returns_midi_and_note_events() -> None:
    expected_midi = b"MThd\x00\x00\x00\x06"
    expected_notes = [
        RawNoteEvent(pitch_midi=40, start_sec=0.0, end_sec=0.5, confidence=1.0),
        RawNoteEvent(pitch_midi=43, start_sec=0.5, end_sec=1.0, confidence=1.0),
    ]

    transcriber = BasicPitchTranscriber(
        midi_transcribe_fn=lambda _path: expected_midi,
        parse_notes_fn=lambda _midi: expected_notes,
    )

    result = transcriber.transcribe(Path("bass.wav"))

    assert result.engine == "basic_pitch"
    assert result.midi_bytes == expected_midi
    assert result.raw_notes == expected_notes


def test_basic_pitch_transcriber_raises_when_midi_is_empty() -> None:
    transcriber = BasicPitchTranscriber(
        midi_transcribe_fn=lambda _path: b"",
        parse_notes_fn=lambda _midi: [],
    )

    with pytest.raises(RuntimeError, match="generated MIDI is empty"):
        transcriber.transcribe(Path("bass.wav"))
