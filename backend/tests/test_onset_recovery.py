from __future__ import annotations

from app.services.bass_transcriber import RawNoteEvent
from app.services.onset_recovery import recover_missing_onsets


def test_splits_long_note_at_detected_onset() -> None:
    notes = [RawNoteEvent(pitch_midi=33, start_sec=0.0, end_sec=2.0, confidence=0.9)]
    onset_times = [0.0, 0.5, 1.0, 1.5]
    result = recover_missing_onsets(notes, onset_times)
    assert len(result) == 4


def test_no_split_when_note_is_short() -> None:
    notes = [RawNoteEvent(pitch_midi=33, start_sec=0.0, end_sec=0.3, confidence=0.9)]
    onset_times = [0.0, 0.15]
    result = recover_missing_onsets(notes, onset_times, min_split_duration=0.25)
    assert len(result) == 1


def test_preserves_notes_without_extra_onsets() -> None:
    notes = [RawNoteEvent(pitch_midi=33, start_sec=0.0, end_sec=0.5, confidence=0.9)]
    onset_times = [0.0]
    result = recover_missing_onsets(notes, onset_times)
    assert len(result) == 1


def test_empty_inputs() -> None:
    assert recover_missing_onsets([], []) == []
    notes = [RawNoteEvent(pitch_midi=33, start_sec=0.0, end_sec=0.5, confidence=0.9)]
    assert len(recover_missing_onsets(notes, [])) == 1
    assert len(recover_missing_onsets([], [0.0, 0.5])) == 0


def test_multiple_notes_with_onsets() -> None:
    notes = [
        RawNoteEvent(pitch_midi=33, start_sec=0.0, end_sec=1.0, confidence=0.9),
        RawNoteEvent(pitch_midi=40, start_sec=1.0, end_sec=2.0, confidence=0.9),
    ]
    onset_times = [0.0, 0.5, 1.0, 1.5]
    result = recover_missing_onsets(notes, onset_times)
    assert len(result) == 4
    assert result[0].pitch_midi == 33
    assert result[1].pitch_midi == 33
    assert result[2].pitch_midi == 40
    assert result[3].pitch_midi == 40
