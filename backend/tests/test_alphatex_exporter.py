from __future__ import annotations

from app.services.alphatex_exporter import build_sync_points, export_alphatex
from app.services.fingering import FingeredNote
from app.services.rhythm_grid import Bar


def _bars() -> list[Bar]:
    bars: list[Bar] = []
    for idx in range(16):
        start = float(idx * 2)
        bars.append(
            Bar(index=idx, start_sec=start, end_sec=start + 2.0, beats_sec=[start, start + 0.5, start + 1.0, start + 1.5])
        )
    return bars


def test_build_sync_points_emits_first_every_8_and_last() -> None:
    points = build_sync_points(_bars(), sync_every_bars=8)

    assert [p.bar_index for p in points] == [0, 8, 15]
    assert points[0].millisecond_offset == 0
    assert points[1].millisecond_offset == 16000


def test_export_alphatex_contains_tempo_tuning_and_sync_lines() -> None:
    notes = [
        FingeredNote(
            bar_index=0,
            beat_position=0.0,
            duration_beats=1.0,
            pitch_midi=40,
            start_sec=0.0,
            end_sec=0.5,
            string=4,
            fret=0,
        )
    ]

    alphatex, points = export_alphatex(notes, _bars(), tempo_used=120, time_signature=(4, 4), sync_every_bars=8)

    assert "\\tempo 120" in alphatex
    assert "\\tuning E1 A1 D2 G2" in alphatex
    assert "\\sync(0 0 0 0)" in alphatex
    assert "\\sync(8 0 16000 0)" in alphatex
    assert "\\sync(15 0 30000 0)" in alphatex
    assert points[-1].bar_index == 15


def test_dotted_quarter_note_exported() -> None:
    note = FingeredNote(
        bar_index=0, beat_position=0.0, duration_beats=1.5,
        pitch_midi=33, start_sec=0.0, end_sec=0.0, string=3, fret=0,
    )
    bars = [Bar(index=0, start_sec=0.0, end_sec=2.0, beats_sec=[0.0, 0.5, 1.0, 1.5])]
    alphatex, _ = export_alphatex([note], bars, tempo_used=120)
    assert "4d" in alphatex


def test_dotted_eighth_note_exported() -> None:
    note = FingeredNote(
        bar_index=0, beat_position=0.0, duration_beats=0.75,
        pitch_midi=33, start_sec=0.0, end_sec=0.0, string=3, fret=0,
    )
    bars = [Bar(index=0, start_sec=0.0, end_sec=2.0, beats_sec=[0.0, 0.5, 1.0, 1.5])]
    alphatex, _ = export_alphatex([note], bars, tempo_used=120)
    assert "8d" in alphatex


def test_rest_fills_gap_between_notes() -> None:
    notes = [
        FingeredNote(bar_index=0, beat_position=0.0, duration_beats=1.0,
                     pitch_midi=33, start_sec=0.0, end_sec=0.0, string=3, fret=0),
        FingeredNote(bar_index=0, beat_position=3.0, duration_beats=1.0,
                     pitch_midi=33, start_sec=1.5, end_sec=0.0, string=3, fret=0),
    ]
    bars = [Bar(index=0, start_sec=0.0, end_sec=2.0, beats_sec=[0.0, 0.5, 1.0, 1.5])]
    alphatex, _ = export_alphatex(notes, bars, tempo_used=120)
    # Should have a rest between the two notes (beats 1-3 = 2 beats = half rest)
    assert "r." in alphatex
