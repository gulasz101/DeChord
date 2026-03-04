from __future__ import annotations

import pytest

from app.services.fingering import (
    _candidates_for_pitch,
    assert_candidate_sanity,
    candidate_sanity_probe,
    optimize_fingering,
    optimize_fingering_with_debug,
)
from app.services.quantization import QuantizedNote


def test_optimize_fingering_respects_string_and_fret_constraints() -> None:
    notes = [
        QuantizedNote(bar_index=0, beat_position=0.0, duration_beats=1.0, pitch_midi=40, start_sec=0.0, end_sec=0.5),
        QuantizedNote(bar_index=0, beat_position=1.0, duration_beats=1.0, pitch_midi=45, start_sec=0.5, end_sec=1.0),
        QuantizedNote(bar_index=0, beat_position=2.0, duration_beats=1.0, pitch_midi=50, start_sec=1.0, end_sec=1.5),
    ]

    fingering = optimize_fingering(notes, max_fret=24)

    assert len(fingering) == 3
    assert all(1 <= n.string <= 4 for n in fingering)
    assert all(0 <= n.fret <= 24 for n in fingering)


def test_optimize_fingering_reduces_extreme_fret_jumps() -> None:
    notes = [
        QuantizedNote(bar_index=0, beat_position=0.0, duration_beats=1.0, pitch_midi=40, start_sec=0.0, end_sec=0.5),
        QuantizedNote(bar_index=0, beat_position=1.0, duration_beats=1.0, pitch_midi=52, start_sec=0.5, end_sec=1.0),
        QuantizedNote(bar_index=0, beat_position=2.0, duration_beats=1.0, pitch_midi=53, start_sec=1.0, end_sec=1.5),
        QuantizedNote(bar_index=0, beat_position=3.0, duration_beats=1.0, pitch_midi=54, start_sec=1.5, end_sec=2.0),
    ]

    fingering = optimize_fingering(notes, max_fret=24)

    jumps = [abs(fingering[idx].fret - fingering[idx - 1].fret) for idx in range(1, len(fingering))]
    assert max(jumps) <= 5


def test_candidates_for_pitch_regression_cases_use_standard_bass_octaves() -> None:
    assert _candidates_for_pitch(34, max_fret=24) == [(3, 1), (4, 6)]
    assert _candidates_for_pitch(33, max_fret=24) == [(3, 0), (4, 5)]
    assert (4, 12) in _candidates_for_pitch(40, max_fret=24)
    assert _candidates_for_pitch(62, max_fret=24) == [(1, 19), (2, 24)]
    assert _candidates_for_pitch(20, max_fret=24) == []


def test_optimize_fingering_drops_only_unplayable_notes() -> None:
    notes = [
        QuantizedNote(bar_index=0, beat_position=0.0, duration_beats=1.0, pitch_midi=40, start_sec=0.0, end_sec=0.5),
        QuantizedNote(bar_index=0, beat_position=1.0, duration_beats=1.0, pitch_midi=20, start_sec=0.5, end_sec=1.0),
        QuantizedNote(bar_index=0, beat_position=2.0, duration_beats=1.0, pitch_midi=45, start_sec=1.0, end_sec=1.5),
    ]

    fingering = optimize_fingering(notes, max_fret=24)

    assert [note.pitch_midi for note in fingering] == [40, 45]


def test_optimize_fingering_with_debug_reports_drop_reasons_and_tuning() -> None:
    notes = [
        QuantizedNote(bar_index=0, beat_position=0.0, duration_beats=1.0, pitch_midi=40, start_sec=0.0, end_sec=0.5),
        QuantizedNote(bar_index=0, beat_position=1.0, duration_beats=1.0, pitch_midi=20, start_sec=0.5, end_sec=1.0),
        QuantizedNote(bar_index=0, beat_position=2.0, duration_beats=1.0, pitch_midi=45, start_sec=1.0, end_sec=1.5),
    ]

    fingering, debug = optimize_fingering_with_debug(notes, max_fret=24)

    assert [note.pitch_midi for note in fingering] == [40, 45]
    assert debug["dropped_reasons"] == {"no_fingering_candidate": 1}
    assert debug["octave_salvaged_notes"] == 0
    assert debug["max_fret"] == 24
    assert debug["tuning_midi"] == {4: 28, 3: 33, 2: 38, 1: 43}


def test_candidate_sanity_probe_reports_canonical_pitch_candidates() -> None:
    probe = candidate_sanity_probe(max_fret=24)

    assert probe["all_ok"] is True
    assert probe["candidate_map"][34] == [(3, 1), (4, 6)]
    assert probe["failures"] == {}


def test_assert_candidate_sanity_raises_for_missing_candidates() -> None:
    with pytest.raises(RuntimeError, match="Candidate sanity probe failed"):
        assert_candidate_sanity(max_fret=0)
