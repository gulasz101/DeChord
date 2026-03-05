from __future__ import annotations

from app.services.bass_transcriber import RawNoteEvent
from app.services.note_cleanup import cleanup_note_events


def test_cleanup_enforces_monophony_by_confidence() -> None:
    events = [
        RawNoteEvent(pitch_midi=40, start_sec=0.0, end_sec=0.5, confidence=0.6),
        RawNoteEvent(pitch_midi=43, start_sec=0.25, end_sec=0.7, confidence=0.9),
    ]

    cleaned = cleanup_note_events(events)

    assert len(cleaned) == 2
    assert cleaned[0].end_sec == 0.25
    assert cleaned[1].pitch_midi == 43


def test_cleanup_drops_short_and_low_confidence_notes() -> None:
    events = [
        RawNoteEvent(pitch_midi=40, start_sec=0.0, end_sec=0.03, confidence=0.9),
        RawNoteEvent(pitch_midi=43, start_sec=0.1, end_sec=0.4, confidence=0.1),
        RawNoteEvent(pitch_midi=45, start_sec=0.5, end_sec=0.9, confidence=0.8),
    ]

    cleaned = cleanup_note_events(events, min_duration_sec=0.06, min_confidence=0.2)

    assert len(cleaned) == 1
    assert cleaned[0].pitch_midi == 45


def test_cleanup_merges_repeated_notes_with_small_gap() -> None:
    events = [
        RawNoteEvent(pitch_midi=40, start_sec=0.0, end_sec=0.5, confidence=0.7),
        RawNoteEvent(pitch_midi=40, start_sec=0.53, end_sec=0.9, confidence=0.9),
    ]

    cleaned = cleanup_note_events(events, merge_gap_sec=0.04)

    assert len(cleaned) == 1
    assert cleaned[0].start_sec == 0.0
    assert cleaned[0].end_sec == 0.9
    assert cleaned[0].confidence == 0.9


def test_cleanup_corrects_single_octave_jump_when_neighbors_support_it() -> None:
    events = [
        RawNoteEvent(pitch_midi=40, start_sec=0.0, end_sec=0.4, confidence=0.8),
        RawNoteEvent(pitch_midi=52, start_sec=0.5, end_sec=0.9, confidence=0.8),
        RawNoteEvent(pitch_midi=41, start_sec=1.0, end_sec=1.4, confidence=0.8),
    ]

    cleaned = cleanup_note_events(events, apply_octave_correction=True)

    assert len(cleaned) == 3
    assert cleaned[1].pitch_midi == 40
