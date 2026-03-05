from __future__ import annotations

from scripts.eval_no_madmom import (
    build_bars,
    extend_bars_to_cover_duration,
    events_to_raw_notes,
)


def test_events_to_raw_notes_converts_transcription_tuples() -> None:
    events = [(0.0, 0.2, 33), (0.2, 0.4, 35)]

    raw_notes = events_to_raw_notes(events)

    assert len(raw_notes) == 2
    assert raw_notes[0].pitch_midi == 33
    assert raw_notes[0].start_sec == 0.0
    assert raw_notes[0].end_sec == 0.2
    assert raw_notes[0].confidence == 1.0


def test_build_bars_groups_beats_by_time_signature() -> None:
    beats = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5]

    bars = build_bars(beats, numerator=4)

    assert len(bars) == 2
    assert bars[0].index == 0
    assert bars[0].start_sec == 0.0
    assert bars[0].end_sec == 2.0
    assert bars[1].index == 1
    assert bars[1].start_sec == 2.0
    assert bars[1].end_sec > bars[1].start_sec


def test_extend_bars_to_cover_duration_adds_tail_bar() -> None:
    beats = [0.0, 0.5, 1.0, 1.5]
    bars = build_bars(beats, numerator=4)

    extended = extend_bars_to_cover_duration(bars, target_end_sec=3.6, beats_per_bar=4)

    assert len(extended) > len(bars)
    assert extended[-1].end_sec >= 3.6
