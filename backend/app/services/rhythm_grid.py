from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Bar:
    index: int
    start_sec: float
    end_sec: float
    beats_sec: list[float]


@dataclass(frozen=True)
class BarGrid:
    bars: list[Bar]


def validate_increasing_timestamps(timestamps: list[float], *, label: str) -> None:
    for idx in range(1, len(timestamps)):
        if timestamps[idx] <= timestamps[idx - 1]:
            raise ValueError(f"{label} must be strictly increasing")
