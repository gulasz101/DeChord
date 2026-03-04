from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from statistics import median
from typing import Callable

BeatExtractor = Callable[[Path], list[float]]
DownbeatExtractor = Callable[[Path], tuple[list[float], list[float]]]


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


def _infer_downbeats_from_beats(beats: list[float], *, numerator: int) -> list[float]:
    if numerator <= 0:
        numerator = 4
    return [beat for idx, beat in enumerate(beats) if idx % numerator == 0]


def build_bars_from_beats_downbeats(
    beats: list[float],
    downbeats: list[float],
    *,
    time_signature_numerator: int = 4,
) -> list[Bar]:
    validate_increasing_timestamps(beats, label="beats")
    if downbeats:
        validate_increasing_timestamps(downbeats, label="downbeats")

    bars: list[Bar] = []
    if len(downbeats) >= 2:
        for idx, start in enumerate(downbeats[:-1]):
            end = downbeats[idx + 1]
            beats_in_bar = [beat for beat in beats if start <= beat < end]
            if not beats_in_bar:
                beats_in_bar = [start]
            bars.append(Bar(index=idx, start_sec=start, end_sec=end, beats_sec=beats_in_bar))
        return bars

    numerator = max(time_signature_numerator, 1)
    if not beats:
        return []

    default_interval = median([beats[i] - beats[i - 1] for i in range(1, len(beats))]) if len(beats) > 1 else 0.5
    bar_index = 0
    for idx in range(0, len(beats), numerator):
        group = beats[idx : idx + numerator]
        if not group:
            continue
        start = group[0]
        if idx + numerator < len(beats):
            end = beats[idx + numerator]
        else:
            end = group[-1] + (default_interval or 0.5)
        bars.append(Bar(index=bar_index, start_sec=start, end_sec=end, beats_sec=group))
        bar_index += 1

    return bars


def compute_derived_bpm(beats: list[float]) -> float | None:
    if len(beats) < 2:
        return None

    diffs = [beats[idx] - beats[idx - 1] for idx in range(1, len(beats))]
    diffs = [d for d in diffs if d > 0]
    if not diffs:
        return None

    return 60.0 / median(diffs)


def reconcile_tempo(derived_bpm: float | None, bpm_hint: float | None) -> float:
    if derived_bpm is None and bpm_hint is None:
        return 120.0
    if derived_bpm is None:
        return float(bpm_hint or 120.0)
    if bpm_hint is None:
        return float(derived_bpm)

    candidates = [derived_bpm * 0.5, derived_bpm, derived_bpm * 2.0]
    best = min(candidates, key=lambda tempo: abs(tempo - bpm_hint))
    return float(best)


def _extract_with_madmom(drums_wav: Path) -> tuple[list[float], list[float]]:
    try:
        from madmom.features.downbeats import DBNDownBeatTrackingProcessor, RNNDownBeatProcessor  # type: ignore
    except ModuleNotFoundError as exc:  # pragma: no cover - optional runtime
        raise RuntimeError("madmom is not available") from exc

    activations = RNNDownBeatProcessor()(str(drums_wav))
    tracking = DBNDownBeatTrackingProcessor(beats_per_bar=[4], fps=100)
    result = tracking(activations)

    beats = [float(item[0]) for item in result]
    downbeats = [float(item[0]) for item in result if int(item[1]) == 1]
    return beats, downbeats


def _extract_with_librosa(drums_wav: Path) -> list[float]:
    try:
        import librosa
    except ModuleNotFoundError as exc:  # pragma: no cover - optional runtime
        raise RuntimeError("librosa is not available") from exc

    y, sr = librosa.load(str(drums_wav), sr=None, mono=True)
    _tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)
    return [float(t) for t in beat_times]


def extract_beats_and_downbeats(
    drums_wav: Path,
    *,
    madmom_fn: DownbeatExtractor | None = None,
    librosa_fn: BeatExtractor | None = None,
    time_signature_numerator: int = 4,
) -> tuple[list[float], list[float], str]:
    madmom_runner = madmom_fn or _extract_with_madmom
    librosa_runner = librosa_fn or _extract_with_librosa

    try:
        beats, downbeats = madmom_runner(drums_wav)
        validate_increasing_timestamps(beats, label="beats")
        validate_increasing_timestamps(downbeats, label="downbeats")
        return beats, downbeats, "madmom"
    except Exception:
        beats = librosa_runner(drums_wav)
        validate_increasing_timestamps(beats, label="beats")
        downbeats = _infer_downbeats_from_beats(beats, numerator=time_signature_numerator)
        validate_increasing_timestamps(downbeats, label="downbeats")
        return beats, downbeats, "librosa"
