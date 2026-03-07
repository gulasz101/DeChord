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


def test_basic_pitch_transcriber_rejects_isolated_short_low_confidence_note(
    monkeypatch,
) -> None:
    monkeypatch.setenv("DECHORD_PITCH_STABILITY_ENABLE", "1")
    monkeypatch.setenv("DECHORD_NOTE_ADMISSION_ENABLE", "1")
    monkeypatch.setenv("DECHORD_NOTE_MIN_DURATION_MS", "60")
    monkeypatch.setenv("DECHORD_NOTE_LOW_CONFIDENCE_THRESHOLD", "0.45")

    transcriber = BasicPitchTranscriber(
        midi_transcribe_fn=lambda _path: b"MThd\x00\x00\x00\x06",
        parse_notes_fn=lambda _midi: [
            RawNoteEvent(pitch_midi=40, start_sec=0.0, end_sec=0.04, confidence=0.24),
        ],
    )

    result = transcriber.transcribe(Path("bass.wav"))

    assert result.raw_notes == []
    assert result.debug_info["basicpitch_rejected_notes"] == 1


def test_basic_pitch_transcriber_merges_same_pitch_fragments_across_short_octave_intrusion(
    monkeypatch,
) -> None:
    monkeypatch.setenv("DECHORD_PITCH_STABILITY_ENABLE", "1")
    monkeypatch.setenv("DECHORD_NOTE_ADMISSION_ENABLE", "1")
    monkeypatch.setenv("DECHORD_NOTE_MIN_DURATION_MS", "60")
    monkeypatch.setenv("DECHORD_NOTE_OCTAVE_INTRUSION_MAX_DURATION_MS", "90")
    monkeypatch.setenv("DECHORD_NOTE_MERGE_GAP_MS", "50")

    raw_notes = [
        RawNoteEvent(pitch_midi=40, start_sec=0.00, end_sec=0.18, confidence=0.93),
        RawNoteEvent(pitch_midi=52, start_sec=0.18, end_sec=0.22, confidence=0.41),
        RawNoteEvent(pitch_midi=40, start_sec=0.22, end_sec=0.42, confidence=0.91),
    ]
    transcriber = BasicPitchTranscriber(
        midi_transcribe_fn=lambda _path: b"MThd\x00\x00\x00\x06",
        parse_notes_fn=lambda _midi: raw_notes,
    )

    result = transcriber.transcribe(Path("bass.wav"))

    assert result.raw_notes == [
        RawNoteEvent(pitch_midi=40, start_sec=0.0, end_sec=0.42, confidence=0.93),
    ]
    assert result.debug_info["basicpitch_short_intrusions_suppressed"] == 1


def test_basic_pitch_transcriber_keeps_real_repeated_same_pitch_notes_distinct(
    monkeypatch,
) -> None:
    monkeypatch.setenv("DECHORD_PITCH_STABILITY_ENABLE", "1")
    monkeypatch.setenv("DECHORD_NOTE_ADMISSION_ENABLE", "1")
    monkeypatch.setenv("DECHORD_NOTE_MERGE_GAP_MS", "60")

    raw_notes = [
        RawNoteEvent(pitch_midi=40, start_sec=0.00, end_sec=0.12, confidence=0.96),
        RawNoteEvent(pitch_midi=40, start_sec=0.16, end_sec=0.28, confidence=0.97),
    ]
    transcriber = BasicPitchTranscriber(
        midi_transcribe_fn=lambda _path: b"MThd\x00\x00\x00\x06",
        parse_notes_fn=lambda _midi: raw_notes,
    )

    result = transcriber.transcribe(Path("bass.wav"))

    assert result.raw_notes == raw_notes


def test_basic_pitch_transcriber_uses_model_note_events_to_improve_raw_recall(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DECHORD_RAW_NOTE_RECALL_ENABLE", "1")
    monkeypatch.setenv("DECHORD_RAW_NOTE_MIN_CONFIDENCE", "0.15")
    monkeypatch.setenv("DECHORD_RAW_NOTE_MIN_DURATION_MS", "35")
    monkeypatch.setenv("DECHORD_RAW_NOTE_ALLOW_WEAK_BASS_CANDIDATES", "1")
    monkeypatch.setenv("DECHORD_PITCH_STABILITY_ENABLE", "0")

    transcriber = BasicPitchTranscriber(
        midi_transcribe_fn=lambda _path: MidiTranscriptionResult(
            midi_bytes=b"MThd\x00\x00\x00\x06",
            engine_used="basic_pitch",
            diagnostics={
                "basic_pitch_note_events": [
                    (0.00, 0.06, 40, 0.92),
                    (0.12, 0.18, 40, 0.18),
                    (0.24, 0.30, 43, 0.19),
                ]
            },
        ),
        parse_notes_fn=lambda _midi: [
            RawNoteEvent(pitch_midi=40, start_sec=0.00, end_sec=0.06, confidence=1.0),
        ],
    )

    result = transcriber.transcribe(Path("bass.wav"))

    assert [(round(note.start_sec, 2), note.pitch_midi) for note in result.raw_notes] == [
        (0.0, 40),
        (0.12, 40),
        (0.24, 43),
    ]
    assert result.debug_info["basicpitch_raw_notes_before_local_filter"] == 3
    assert result.debug_info["basicpitch_raw_notes_after_local_filter"] == 3
    assert result.debug_info["pipeline_trace"]["pipeline_stats"]["basic_pitch_raw"]["note_count"] == 3


def test_basic_pitch_transcriber_bounds_spurious_model_note_events_during_raw_recall(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DECHORD_RAW_NOTE_RECALL_ENABLE", "1")
    monkeypatch.setenv("DECHORD_RAW_NOTE_MIN_CONFIDENCE", "0.15")
    monkeypatch.setenv("DECHORD_RAW_NOTE_MIN_DURATION_MS", "35")
    monkeypatch.setenv("DECHORD_RAW_NOTE_ALLOW_WEAK_BASS_CANDIDATES", "1")
    monkeypatch.setenv("DECHORD_PITCH_STABILITY_ENABLE", "0")

    transcriber = BasicPitchTranscriber(
        midi_transcribe_fn=lambda _path: MidiTranscriptionResult(
            midi_bytes=b"MThd\x00\x00\x00\x06",
            engine_used="basic_pitch",
            diagnostics={
                "basic_pitch_note_events": [
                    (0.00, 0.06, 40, 0.18),
                    (0.12, 0.15, 43, 0.95),
                    (0.20, 0.28, 76, 0.90),
                    (0.32, 0.40, 31, 0.04),
                ]
            },
        ),
        parse_notes_fn=lambda _midi: [],
    )

    result = transcriber.transcribe(Path("bass.wav"))

    assert result.raw_notes == [
        RawNoteEvent(pitch_midi=40, start_sec=0.0, end_sec=0.06, confidence=0.18),
    ]
    assert result.debug_info["basicpitch_raw_notes_before_local_filter"] == 4
    assert result.debug_info["basicpitch_raw_notes_after_local_filter"] == 1
    assert result.debug_info["basicpitch_raw_notes_removed_by_local_filter"] == 3
