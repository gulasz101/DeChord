from __future__ import annotations

from app.services.fingering import FingeredNote
from app.services.gp5_reference import ReferenceNote
from app.services.tab_report import generate_comparison_report


def _ref(bar: int, beat: float, dur: float, pitch: int, string: int, fret: int) -> ReferenceNote:
    return ReferenceNote(bar_index=bar, beat_position=beat, duration_beats=dur, pitch_midi=pitch, string=string, fret=fret)


def _gen(bar: int, beat: float, dur: float, pitch: int, string: int, fret: int) -> FingeredNote:
    return FingeredNote(bar_index=bar, beat_position=beat, duration_beats=dur, pitch_midi=pitch, start_sec=0.0, end_sec=0.0, string=string, fret=fret)


def test_report_contains_summary_and_per_bar_table() -> None:
    ref = [_ref(0, 0.0, 0.25, 33, 3, 0), _ref(0, 0.25, 0.25, 40, 2, 2)]
    gen = [_gen(0, 0.0, 0.25, 33, 3, 0)]
    report = generate_comparison_report(ref, gen, song_name="Test Song")
    assert "# Test Song" in report
    assert "F1" in report
    assert "| 0 |" in report


def test_report_marks_missing_notes() -> None:
    ref = [_ref(0, 0.0, 0.25, 33, 3, 0)]
    gen = []
    report = generate_comparison_report(ref, gen, song_name="Test")
    assert "MISS" in report or "0.00" in report
