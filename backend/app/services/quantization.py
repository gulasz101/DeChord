from __future__ import annotations

from dataclasses import dataclass
from math import ceil

from app.services.bass_transcriber import RawNoteEvent
from app.services.rhythm_grid import BarGrid


@dataclass(frozen=True)
class QuantizedNote:
    bar_index: int
    beat_position: float
    duration_beats: float
    pitch_midi: int
    start_sec: float
    end_sec: float


def _find_bar_index(time_sec: float, grid: BarGrid) -> int | None:
    for idx, bar in enumerate(grid.bars):
        if bar.start_sec <= time_sec < bar.end_sec:
            return idx
    if grid.bars and time_sec == grid.bars[-1].end_sec:
        return len(grid.bars) - 1
    return None


def _snap_time_to_bar_grid(
    time_sec: float, *, bar_start: float, bar_end: float, subdivisions_per_bar: int
) -> float:
    duration = max(bar_end - bar_start, 1e-6)
    relative = max(0.0, min((time_sec - bar_start) / duration, 1.0))
    snapped_step = round(relative * subdivisions_per_bar)
    snapped_rel = snapped_step / subdivisions_per_bar
    return bar_start + (snapped_rel * duration)


def quantize_note_events(
    events: list[RawNoteEvent],
    grid: BarGrid,
    *,
    subdivision: int = 16,
) -> list[QuantizedNote]:
    if not events or not grid.bars:
        return []

    numerator = max(len(grid.bars[0].beats_sec), 1)
    steps_per_beat = max(int(ceil(subdivision / 4)), 1)
    subdivisions_per_bar = max(numerator * steps_per_beat, 1)
    quantized: list[QuantizedNote] = []

    for event in sorted(events, key=lambda e: (e.start_sec, e.end_sec, e.pitch_midi)):
        cursor = event.start_sec
        event_end = event.end_sec

        while cursor < event_end:
            bar_idx = _find_bar_index(cursor, grid)
            if bar_idx is None:
                break

            bar = grid.bars[bar_idx]
            segment_end = min(event_end, bar.end_sec)
            if segment_end <= cursor:
                break

            snapped_start = _snap_time_to_bar_grid(
                cursor,
                bar_start=bar.start_sec,
                bar_end=bar.end_sec,
                subdivisions_per_bar=subdivisions_per_bar,
            )
            snapped_end = _snap_time_to_bar_grid(
                segment_end,
                bar_start=bar.start_sec,
                bar_end=bar.end_sec,
                subdivisions_per_bar=subdivisions_per_bar,
            )

            if snapped_end <= snapped_start:
                snapped_end = min(
                    bar.end_sec,
                    snapped_start
                    + ((bar.end_sec - bar.start_sec) / subdivisions_per_bar),
                )

            beat_position = (
                (snapped_start - bar.start_sec) / (bar.end_sec - bar.start_sec)
            ) * numerator
            duration_beats = (
                (snapped_end - snapped_start) / (bar.end_sec - bar.start_sec)
            ) * numerator

            quantized.append(
                QuantizedNote(
                    bar_index=bar.index,
                    beat_position=max(0.0, beat_position),
                    duration_beats=max(duration_beats, 1.0 / steps_per_beat),
                    pitch_midi=event.pitch_midi,
                    start_sec=snapped_start,
                    end_sec=snapped_end,
                )
            )

            if segment_end >= bar.end_sec:
                cursor = bar.end_sec
            else:
                break

    return quantized
