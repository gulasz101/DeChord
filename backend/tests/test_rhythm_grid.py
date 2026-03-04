from __future__ import annotations

import pytest

from app.services.rhythm_grid import Bar, BarGrid, validate_increasing_timestamps


def test_validate_increasing_timestamps_accepts_increasing_values() -> None:
    validate_increasing_timestamps([0.1, 0.2, 0.4, 1.0], label="beats")


def test_validate_increasing_timestamps_rejects_non_increasing_values() -> None:
    with pytest.raises(ValueError, match="beats must be strictly increasing"):
        validate_increasing_timestamps([0.1, 0.2, 0.2], label="beats")


def test_bar_grid_container_holds_bar_sequence() -> None:
    bars = [
        Bar(index=0, start_sec=0.0, end_sec=2.0, beats_sec=[0.0, 0.5, 1.0, 1.5]),
        Bar(index=1, start_sec=2.0, end_sec=4.0, beats_sec=[2.0, 2.5, 3.0, 3.5]),
    ]
    grid = BarGrid(bars=bars)

    assert len(grid.bars) == 2
    assert grid.bars[0].index == 0
    assert grid.bars[1].start_sec == 2.0
