from __future__ import annotations

from pathlib import Path

import pytest

from app.midi import MidiTranscriptionResult
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


def test_basic_pitch_transcriber_uses_engine_from_detailed_midi_result() -> None:
    expected_notes = [RawNoteEvent(pitch_midi=40, start_sec=0.0, end_sec=0.5, confidence=0.8)]
    transcriber = BasicPitchTranscriber(
        midi_transcribe_fn=lambda _path: MidiTranscriptionResult(
            midi_bytes=b"MThd\x00\x00\x00\x06",
            engine_used="fallback_frequency",
            diagnostics={"fallback_octave_corrections_applied": 2},
        ),
        parse_notes_fn=lambda _midi: expected_notes,
    )

    result = transcriber.transcribe(Path("bass.wav"))

    assert result.engine == "fallback_frequency"
    assert result.debug_info["fallback_octave_corrections_applied"] == 2


def test_basic_pitch_transcriber_applies_conservative_octave_stabilization() -> None:
    raw_notes = [
        RawNoteEvent(pitch_midi=40, start_sec=0.0, end_sec=0.4, confidence=0.9),
        RawNoteEvent(pitch_midi=52, start_sec=0.5, end_sec=0.9, confidence=0.9),
        RawNoteEvent(pitch_midi=41, start_sec=1.0, end_sec=1.4, confidence=0.9),
    ]
    transcriber = BasicPitchTranscriber(
        midi_transcribe_fn=lambda _path: b"MThd\x00\x00\x00\x06",
        parse_notes_fn=lambda _midi: raw_notes,
    )

    result = transcriber.transcribe(Path("bass.wav"))

    assert [note.pitch_midi for note in result.raw_notes] == [40, 40, 41]
    assert result.debug_info["basicpitch_octave_corrections_applied"] == 1


def test_basic_pitch_transcriber_does_not_overcorrect_when_context_is_weak() -> None:
    raw_notes = [
        RawNoteEvent(pitch_midi=40, start_sec=0.0, end_sec=0.4, confidence=0.9),
        RawNoteEvent(pitch_midi=52, start_sec=0.5, end_sec=0.9, confidence=0.2),
        RawNoteEvent(pitch_midi=58, start_sec=1.0, end_sec=1.4, confidence=0.9),
    ]
    transcriber = BasicPitchTranscriber(
        midi_transcribe_fn=lambda _path: b"MThd\x00\x00\x00\x06",
        parse_notes_fn=lambda _midi: raw_notes,
    )

    result = transcriber.transcribe(Path("bass.wav"))

    assert [note.pitch_midi for note in result.raw_notes] == [40, 52, 58]
    assert result.debug_info["basicpitch_octave_corrections_applied"] == 0
