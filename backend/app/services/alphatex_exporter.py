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
    if duration_beats >= 4.0:
        return "1"
    if duration_beats >= 2.0:
        return "2"
    if duration_beats >= 1.0:
        return "4"
    if duration_beats >= 0.5:
        return "8"
    return "16"


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
    for bar in bars:
        bar_notes = sorted(by_bar.get(bar.index, []), key=lambda note: note.start_sec)
        if not bar_notes:
            measure_lines.append("r.1")
            continue

        tokens: list[str] = []
        for note in bar_notes:
            duration = _duration_to_token(note.duration_beats)
            tokens.append(f"{note.fret}.{note.string}.{duration}")
        measure_lines.append(" ".join(tokens))

    body = " | ".join(measure_lines)
    lines.append(body)
    return "\n".join(lines), sync_points
