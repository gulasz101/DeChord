from __future__ import annotations

import signal

import pytest

from app.services.bass_transcriber import RawNoteEvent
from app.services.quantization import quantize_note_events
from app.services.rhythm_grid import Bar, BarGrid


def _grid() -> BarGrid:
    return BarGrid(
        bars=[
            Bar(index=0, start_sec=0.0, end_sec=2.0, beats_sec=[0.0, 0.5, 1.0, 1.5]),
            Bar(index=1, start_sec=2.0, end_sec=4.0, beats_sec=[2.0, 2.5, 3.0, 3.5]),
        ]
    )


def test_quantize_snaps_start_to_nearest_sixteenth() -> None:
    events = [RawNoteEvent(pitch_midi=40, start_sec=0.37, end_sec=0.86, confidence=0.8)]

    quantized = quantize_note_events(events, _grid(), subdivision=16)

    assert len(quantized) == 1
    # nearest sixteenth in 2s bar => 0.125s grid, 0.37 -> 0.375
    assert quantized[0].start_sec == pytest.approx(0.375)
    assert abs(quantized[0].start_sec - 0.37) <= 0.07


def test_quantize_splits_notes_crossing_bar_boundaries() -> None:
    events = [RawNoteEvent(pitch_midi=43, start_sec=1.8, end_sec=2.2, confidence=0.9)]

    quantized = quantize_note_events(events, _grid(), subdivision=16)

    assert len(quantized) == 2
    assert quantized[0].bar_index == 0
    assert quantized[1].bar_index == 1
    assert quantized[0].end_sec <= 2.0
    assert quantized[1].start_sec >= 2.0


def test_quantize_terminates_when_note_extends_past_final_bar() -> None:
    events = [RawNoteEvent(pitch_midi=43, start_sec=3.8, end_sec=4.4, confidence=0.9)]

    def _timeout_handler(_signum: int, _frame: object | None) -> None:
        raise TimeoutError("quantize_note_events did not terminate")

    previous_handler = signal.signal(signal.SIGALRM, _timeout_handler)
    signal.setitimer(signal.ITIMER_REAL, 0.1)
    try:
        quantized = quantize_note_events(events, _grid(), subdivision=16)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous_handler)

    assert len(quantized) == 1
    assert quantized[0].bar_index == 1
    assert quantized[0].start_sec == pytest.approx(3.75)
    assert quantized[0].end_sec == pytest.approx(4.0)
