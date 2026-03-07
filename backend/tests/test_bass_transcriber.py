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


def test_basic_pitch_transcriber_suppresses_short_false_intrusion_when_pitch_stability_enabled(
    monkeypatch,
) -> None:
    monkeypatch.setenv("DECHORD_PITCH_STABILITY_ENABLE", "1")
    monkeypatch.setenv("DECHORD_PITCH_MIN_NOTE_DURATION_MS", "80")
    monkeypatch.setenv("DECHORD_PITCH_MERGE_GAP_MS", "60")

    raw_notes = [
        RawNoteEvent(pitch_midi=40, start_sec=0.0, end_sec=0.24, confidence=0.9),
        RawNoteEvent(pitch_midi=47, start_sec=0.24, end_sec=0.28, confidence=0.8),
        RawNoteEvent(pitch_midi=40, start_sec=0.28, end_sec=0.52, confidence=0.92),
    ]
    transcriber = BasicPitchTranscriber(
        midi_transcribe_fn=lambda _path: b"MThd\x00\x00\x00\x06",
        parse_notes_fn=lambda _midi: raw_notes,
    )

    result = transcriber.transcribe(Path("bass.wav"))

    assert result.raw_notes == [
        RawNoteEvent(pitch_midi=40, start_sec=0.0, end_sec=0.52, confidence=0.92)
    ]
    assert result.debug_info["basicpitch_short_intrusions_suppressed"] == 1


def test_basic_pitch_transcriber_keeps_short_intrusion_when_pitch_stability_disabled(
    monkeypatch,
) -> None:
    monkeypatch.setenv("DECHORD_PITCH_STABILITY_ENABLE", "0")

    raw_notes = [
        RawNoteEvent(pitch_midi=40, start_sec=0.0, end_sec=0.24, confidence=0.9),
        RawNoteEvent(pitch_midi=47, start_sec=0.24, end_sec=0.28, confidence=0.8),
        RawNoteEvent(pitch_midi=40, start_sec=0.28, end_sec=0.52, confidence=0.92),
    ]
    transcriber = BasicPitchTranscriber(
        midi_transcribe_fn=lambda _path: b"MThd\x00\x00\x00\x06",
        parse_notes_fn=lambda _midi: raw_notes,
    )

    result = transcriber.transcribe(Path("bass.wav"))

    assert result.raw_notes == raw_notes
    assert result.debug_info["basicpitch_short_intrusions_suppressed"] == 0
