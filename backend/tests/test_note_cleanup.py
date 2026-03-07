from __future__ import annotations

from app.services.bass_transcriber import RawNoteEvent
from app.services.note_cleanup import cleanup_note_events, cleanup_params_for_bpm


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


def test_cleanup_params_for_bpm_are_tempo_adaptive() -> None:
    slow = cleanup_params_for_bpm(90.0)
    fast = cleanup_params_for_bpm(180.0)

    assert slow["min_duration_sec"] >= fast["min_duration_sec"]
    assert slow["merge_gap_sec"] >= fast["merge_gap_sec"]
    assert slow["apply_octave_correction"] is True


def test_cleanup_collects_rule_counters() -> None:
    events = [
        RawNoteEvent(pitch_midi=40, start_sec=0.0, end_sec=0.03, confidence=0.9),  # short
        RawNoteEvent(pitch_midi=42, start_sec=0.10, end_sec=0.30, confidence=0.1),  # low conf
        RawNoteEvent(pitch_midi=40, start_sec=0.30, end_sec=0.55, confidence=0.7),
        RawNoteEvent(pitch_midi=40, start_sec=0.57, end_sec=0.80, confidence=0.8),  # merged
    ]
    stats: dict[str, int] = {}

    cleaned = cleanup_note_events(events, stats=stats)

    assert len(cleaned) == 1
    assert stats["removed_short"] == 1
    assert stats["removed_low_conf"] == 1
    assert stats["merged_same_pitch"] == 1


def test_cleanup_does_not_merge_same_pitch_when_onset_between_notes() -> None:
    events = [
        RawNoteEvent(pitch_midi=40, start_sec=0.0, end_sec=0.5, confidence=0.7),
        RawNoteEvent(pitch_midi=40, start_sec=0.52, end_sec=0.9, confidence=0.9),
    ]
    stats: dict[str, int] = {}

    cleaned = cleanup_note_events(
        events,
        merge_gap_sec=0.04,
        onset_times=[0.51],
        stats=stats,
    )

    assert len(cleaned) == 2
    assert stats["merges_blocked_by_onset"] == 1
