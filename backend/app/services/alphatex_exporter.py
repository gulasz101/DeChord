from __future__ import annotations

from dataclasses import dataclass

from app.services.fingering import FingeredNote
from app.services.rhythm_grid import Bar


@dataclass(frozen=True)
class SyncPoint:
    bar_index: int
    millisecond_offset: int


def build_sync_points(bars: list[Bar], *, sync_every_bars: int = 8) -> list[SyncPoint]:
    if not bars:
        return []

    selected_indexes = {0, len(bars) - 1}
    if sync_every_bars > 0:
        for idx in range(0, len(bars), sync_every_bars):
            selected_indexes.add(idx)

    points: list[SyncPoint] = []
    for idx in sorted(selected_indexes):
        bar = bars[idx]
        points.append(SyncPoint(bar_index=bar.index, millisecond_offset=round(bar.start_sec * 1000)))
    return points


def _duration_to_token(duration_beats: float) -> str:
    """Convert beat duration to AlphaTeX duration token.

    Supports dotted notes (suffix 'd') for 1.5x standard durations.
    """
    # Check dotted durations first (within tolerance)
    if abs(duration_beats - 6.0) < 0.2:
        return "1d"  # dotted whole
    if abs(duration_beats - 3.0) < 0.1:
        return "2d"  # dotted half
    if abs(duration_beats - 1.5) < 0.05:
        return "4d"  # dotted quarter
    if abs(duration_beats - 0.75) < 0.03:
        return "8d"  # dotted eighth
    if abs(duration_beats - 0.375) < 0.02:
        return "16d"  # dotted sixteenth
    # Standard durations
    if duration_beats >= 3.5:
        return "1"
    if duration_beats >= 1.75:
        return "2"
    if duration_beats >= 0.875:
        return "4"
    if duration_beats >= 0.4375:
        return "8"
    return "16"


def _fill_rests(gap_beats: float) -> list[str]:
    """Break a gap (in beats) into rest tokens, largest first."""
    # Ordered from largest to smallest, including dotted values
    rest_values = [
        (4.0, "1"), (3.0, "2d"), (2.0, "2"), (1.5, "4d"),
        (1.0, "4"), (0.75, "8d"), (0.5, "8"), (0.375, "16d"), (0.25, "16"),
    ]
    tokens: list[str] = []
    remaining = gap_beats
    for beats, token in rest_values:
        while remaining >= beats - 0.01:
            tokens.append(f"r.{token}")
            remaining -= beats
    return tokens


def export_alphatex(
    notes: list[FingeredNote],
    bars: list[Bar],
    *,
    tempo_used: float,
    time_signature: tuple[int, int] = (4, 4),
    sync_every_bars: int = 8,
) -> tuple[str, list[SyncPoint]]:
    numerator, denominator = time_signature
    sync_points = build_sync_points(bars, sync_every_bars=sync_every_bars)

    by_bar: dict[int, list[FingeredNote]] = {}
    for note in notes:
        by_bar.setdefault(note.bar_index, []).append(note)

    lines: list[str] = [
        f"\\tempo {round(tempo_used)}",
        f"\\ts {numerator} {denominator}",
        "\\tuning E1 A1 D2 G2",
    ]

    for point in sync_points:
        lines.append(f"\\sync({point.bar_index} 0 {point.millisecond_offset} 0)")

    measure_lines: list[str] = []
    beats_per_bar = float(numerator)
    for bar in bars:
        bar_notes = sorted(by_bar.get(bar.index, []), key=lambda note: note.beat_position)
        if not bar_notes:
            measure_lines.append("r.1")
            continue

        tokens: list[str] = []
        cursor = 0.0  # current beat position within the bar
        for note in bar_notes:
            gap = note.beat_position - cursor
            if gap > 0.01:
                tokens.extend(_fill_rests(gap))
            duration = _duration_to_token(note.duration_beats)
            tokens.append(f"{note.fret}.{note.string}.{duration}")
            cursor = note.beat_position + note.duration_beats
        # Fill trailing rest if notes don't reach end of bar
        trailing = beats_per_bar - cursor
        if trailing > 0.01:
            tokens.extend(_fill_rests(trailing))
        measure_lines.append(" ".join(tokens))

    body = " | ".join(measure_lines)
    lines.append(body)
    return "\n".join(lines), sync_points
