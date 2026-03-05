from __future__ import annotations

from pathlib import Path

import pytest

from app.services.rhythm_grid import (
    Bar,
    BarGrid,
    compute_derived_bpm,
    extract_beats_and_downbeats,
    reconcile_tempo,
    validate_increasing_timestamps,
)


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


def test_extract_beats_and_downbeats_prefers_madmom_when_available() -> None:
    def fake_madmom(_path: Path) -> tuple[list[float], list[float]]:
        return [0.0, 0.5, 1.0, 1.5], [0.0, 1.0]

    beats, downbeats, source = extract_beats_and_downbeats(
        Path("drums.wav"),
        madmom_fn=fake_madmom,
        librosa_fn=None,
    )

    assert source == "madmom"
    assert beats == [0.0, 0.5, 1.0, 1.5]
    assert downbeats == [0.0, 1.0]


def test_extract_beats_and_downbeats_falls_back_to_librosa() -> None:
    def fake_madmom(_path: Path) -> tuple[list[float], list[float]]:
        raise RuntimeError("madmom unavailable")

    def fake_librosa(_path: Path) -> list[float]:
        return [0.0, 0.5, 1.0, 1.5, 2.0]

    beats, downbeats, source = extract_beats_and_downbeats(
        Path("drums.wav"),
        madmom_fn=fake_madmom,
        librosa_fn=fake_librosa,
        time_signature_numerator=4,
    )

    assert source == "librosa"
    assert beats == [0.0, 0.5, 1.0, 1.5, 2.0]
    assert downbeats == [0.0, 2.0]


def test_compute_derived_bpm_uses_median_beat_period() -> None:
    bpm = compute_derived_bpm([0.0, 0.5, 1.0, 1.5])
    assert bpm == pytest.approx(120.0)


def test_reconcile_tempo_corrects_half_time_ambiguity() -> None:
    tempo = reconcile_tempo(derived_bpm=70.0, bpm_hint=140.0)
    assert tempo == pytest.approx(140.0)


def test_reconcile_tempo_keeps_derived_without_hint() -> None:
    tempo = reconcile_tempo(derived_bpm=102.0, bpm_hint=None)
    assert tempo == pytest.approx(102.0)
