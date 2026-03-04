from __future__ import annotations

from app.services.fingering import optimize_fingering
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
