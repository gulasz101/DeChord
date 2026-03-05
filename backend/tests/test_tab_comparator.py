from __future__ import annotations

from app.services.fingering import FingeredNote
from app.services.gp5_reference import ReferenceNote
from app.services.tab_comparator import ComparisonResult, compare_tabs


def _ref(bar: int, beat: float, dur: float, pitch: int, string: int, fret: int) -> ReferenceNote:
    return ReferenceNote(bar_index=bar, beat_position=beat, duration_beats=dur, pitch_midi=pitch, string=string, fret=fret)


def _gen(bar: int, beat: float, dur: float, pitch: int, string: int, fret: int) -> FingeredNote:
    return FingeredNote(bar_index=bar, beat_position=beat, duration_beats=dur, pitch_midi=pitch, start_sec=0.0, end_sec=0.0, string=string, fret=fret)


def test_perfect_match_returns_100_percent() -> None:
    ref = [_ref(0, 0.0, 0.25, 33, 3, 0), _ref(0, 0.25, 0.25, 40, 2, 2)]
    gen = [_gen(0, 0.0, 0.25, 33, 3, 0), _gen(0, 0.25, 0.25, 40, 2, 2)]
    result = compare_tabs(ref, gen)
    assert result.pitch_accuracy == 1.0
    assert result.note_density_correlation >= 0.99
    assert result.f1_score == 1.0
    assert result.fingering_accuracy == 1.0


def test_missing_notes_lowers_recall() -> None:
    ref = [_ref(0, 0.0, 0.25, 33, 3, 0), _ref(0, 0.25, 0.25, 40, 2, 2)]
    gen = [_gen(0, 0.0, 0.25, 33, 3, 0)]
    result = compare_tabs(ref, gen)
    assert result.f1_score < 1.0
    assert result.recall < 1.0
    assert result.precision == 1.0


def test_extra_notes_lowers_precision() -> None:
    ref = [_ref(0, 0.0, 0.25, 33, 3, 0)]
    gen = [_gen(0, 0.0, 0.25, 33, 3, 0), _gen(0, 0.25, 0.25, 40, 2, 2)]
    result = compare_tabs(ref, gen)
    assert result.precision < 1.0
    assert result.recall == 1.0


def test_wrong_pitch_lowers_pitch_accuracy() -> None:
    ref = [_ref(0, 0.0, 0.25, 33, 3, 0)]
    gen = [_gen(0, 0.0, 0.25, 35, 3, 2)]
    result = compare_tabs(ref, gen)
    assert result.pitch_accuracy == 0.0


def test_empty_inputs() -> None:
    result = compare_tabs([], [])
    assert result.f1_score == 0.0
    assert result.precision == 0.0
    assert result.recall == 0.0


def test_per_bar_breakdown() -> None:
    ref = [_ref(0, 0.0, 0.25, 33, 3, 0), _ref(1, 0.0, 0.25, 40, 2, 2)]
    gen = [_gen(0, 0.0, 0.25, 33, 3, 0)]
    result = compare_tabs(ref, gen)
    assert 0 in result.per_bar
    assert 1 in result.per_bar
    assert result.per_bar[0].f1_score == 1.0
    assert result.per_bar[1].f1_score == 0.0
