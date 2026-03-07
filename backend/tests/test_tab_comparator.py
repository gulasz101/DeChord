from __future__ import annotations

import pytest

from app.services.tab_comparator import ReferenceNote, compare_tabs


def test_compare_tabs_reports_onset_metrics_for_ms_and_grid_tolerances() -> None:
    reference = [
        ReferenceNote(bar_index=0, beat_position=0.0, duration_beats=0.5, pitch_midi=40, string=4, fret=12),
        ReferenceNote(bar_index=0, beat_position=1.0, duration_beats=0.5, pitch_midi=42, string=4, fret=14),
    ]
    generated = [
        ReferenceNote(bar_index=0, beat_position=0.03, duration_beats=0.5, pitch_midi=40, string=4, fret=12),
        ReferenceNote(bar_index=0, beat_position=1.2, duration_beats=0.5, pitch_midi=42, string=4, fret=14),
    ]

    comparison = compare_tabs(
        reference,
        generated,
        beat_tolerance=0.125,
        bpm=120.0,
        subdivision=16,
        onset_tolerance_ms=30.0,
    )

    assert comparison.onset_precision_ms == pytest.approx(0.5)
    assert comparison.onset_recall_ms == pytest.approx(0.5)
    assert comparison.onset_f1_ms == pytest.approx(0.5)

    # grid tolerance is 1/subdivision-per-beat => 0.25 beat at 16th-note grid
    assert comparison.onset_precision_grid == pytest.approx(1.0)
    assert comparison.onset_recall_grid == pytest.approx(1.0)
    assert comparison.onset_f1_grid == pytest.approx(1.0)


def test_compare_tabs_reports_octave_confusion_breakdown() -> None:
    reference = [
        ReferenceNote(bar_index=0, beat_position=0.0, duration_beats=0.5, pitch_midi=40, string=4, fret=12),
        ReferenceNote(bar_index=0, beat_position=1.0, duration_beats=0.5, pitch_midi=43, string=3, fret=10),
        ReferenceNote(bar_index=0, beat_position=2.0, duration_beats=0.5, pitch_midi=45, string=2, fret=7),
        ReferenceNote(bar_index=0, beat_position=3.0, duration_beats=0.5, pitch_midi=47, string=1, fret=4),
    ]
    generated = [
        ReferenceNote(bar_index=0, beat_position=0.0, duration_beats=0.5, pitch_midi=40, string=4, fret=12),  # exact
        ReferenceNote(bar_index=0, beat_position=1.0, duration_beats=0.5, pitch_midi=55, string=2, fret=17),  # +12
        ReferenceNote(bar_index=0, beat_position=2.0, duration_beats=0.5, pitch_midi=33, string=4, fret=5),   # -12
        ReferenceNote(bar_index=0, beat_position=3.0, duration_beats=0.5, pitch_midi=49, string=1, fret=6),   # other
    ]

    comparison = compare_tabs(reference, generated, beat_tolerance=0.01, bpm=120.0, subdivision=16)

    assert comparison.total_matched == 4
    assert comparison.octave_confusion["exact"] == 1
    assert comparison.octave_confusion["octave_plus_12"] == 1
    assert comparison.octave_confusion["octave_minus_12"] == 1
    assert comparison.octave_confusion["other"] == 1
