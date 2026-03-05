from __future__ import annotations

from app.services.bass_transcriber import RawNoteEvent
from app.services.onset_recovery import recover_missing_onsets, recovery_params_for_bpm


def test_recovery_params_for_bpm_are_tempo_adaptive() -> None:
    slow = recovery_params_for_bpm(90.0)
    fast = recovery_params_for_bpm(180.0)

    assert slow["min_split_duration"] >= fast["min_split_duration"]
    assert slow["onset_tolerance"] >= fast["onset_tolerance"]


def test_recover_missing_onsets_splits_notes_and_reports_split_starts() -> None:
    notes = [
        RawNoteEvent(pitch_midi=40, start_sec=0.0, end_sec=1.0, confidence=0.9),
    ]

    recovered, split_starts, split_count = recover_missing_onsets(
        notes,
        [0.42],
        min_split_duration=0.08,
        onset_tolerance=0.05,
    )

    assert split_count == 1
    assert len(recovered) == 2
    assert recovered[0].start_sec == 0.0
    assert recovered[0].end_sec == 0.42
    assert recovered[1].start_sec == 0.42
    assert recovered[1].end_sec == 1.0
    assert round(recovered[1].start_sec, 6) in split_starts
