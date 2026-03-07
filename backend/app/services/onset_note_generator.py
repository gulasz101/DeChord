from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import numpy as np

from app.services.bass_transcriber import RawNoteEvent

AudioLoadFn = Callable[[Path | str], tuple[list[float], int]]


@dataclass(frozen=True)
class OnsetNoteGeneratorConfig:
    onset_min_spacing_ms: int = 70
    onset_strength_threshold: float = 0.35
    onset_region_max_duration_ms: int = 220
    onset_region_min_duration_ms: int = 40
    minimum_pitch_confidence: float = 0.25


@dataclass(frozen=True)
class OnsetNoteCandidate:
    pitch_midi: int
    start_sec: float
    end_sec: float
    confidence: float
    source_tag: str = "onset_note_generator"
    support: dict[str, object] = field(default_factory=dict)

    def to_raw_note(self) -> RawNoteEvent:
        return RawNoteEvent(
            pitch_midi=self.pitch_midi,
            start_sec=self.start_sec,
            end_sec=self.end_sec,
            confidence=self.confidence,
        )


def detect_bass_onsets(
    audio: list[float],
    sr: int,
    *,
    config: OnsetNoteGeneratorConfig,
) -> list[float]:
    if not audio or sr <= 0:
        return []

    signal = np.asarray(audio, dtype=np.float32)
    if signal.size < 32:
        return []

    frame_size = max(128, int(sr * 0.032))
    hop_size = max(32, int(sr * 0.008))
    if signal.size < frame_size:
        frame_size = signal.size
        hop_size = max(1, frame_size // 4)

    envelope = []
    for start in range(0, max(1, signal.size - frame_size + 1), hop_size):
        frame = signal[start : start + frame_size]
        envelope.append(float(np.sqrt(np.mean(np.square(frame), dtype=np.float64))))
    if not envelope:
        return []

    env = np.asarray(envelope, dtype=np.float32)
    smoothed = _moving_average(env, window=max(3, int(0.020 * sr / hop_size)))
    onset_strength = np.maximum(0.0, smoothed - np.concatenate(([smoothed[0]], smoothed[:-1])))
    max_strength = float(np.max(onset_strength)) if onset_strength.size else 0.0
    if max_strength <= 1e-6:
        return []

    normalized = onset_strength / max_strength
    threshold = max(float(config.onset_strength_threshold), float(np.median(normalized) + 0.05))
    min_spacing_sec = max(float(config.onset_min_spacing_ms) / 1000.0, 0.0)
    onset_times: list[float] = []
    last_onset_sec = -float("inf")

    for idx in range(1, len(normalized) - 1):
        strength = float(normalized[idx])
        if strength < threshold:
            continue
        if strength < float(normalized[idx - 1]) or strength < float(normalized[idx + 1]):
            continue
        timestamp = float(((idx * hop_size) + (frame_size / 2.0)) / sr)
        if (timestamp - last_onset_sec) < min_spacing_sec:
            continue
        onset_times.append(timestamp)
        last_onset_sec = timestamp

    return onset_times


def build_onset_regions(
    onset_times: list[float],
    *,
    audio_duration_sec: float,
    config: OnsetNoteGeneratorConfig,
) -> list[tuple[float, float]]:
    if not onset_times:
        return []

    ordered = sorted(max(0.0, float(onset)) for onset in onset_times)
    min_duration_sec = max(float(config.onset_region_min_duration_ms) / 1000.0, 0.01)
    max_duration_sec = max(min_duration_sec, float(config.onset_region_max_duration_ms) / 1000.0)

    regions: list[tuple[float, float]] = []
    for idx, onset_sec in enumerate(ordered):
        next_onset = ordered[idx + 1] if idx + 1 < len(ordered) else float(audio_duration_sec)
        if next_onset <= onset_sec:
            continue
        region_end = min(next_onset, onset_sec + max_duration_sec)
        if (region_end - onset_sec) < min_duration_sec:
            region_end = min(
                float(audio_duration_sec) if audio_duration_sec > 0 else onset_sec + min_duration_sec,
                onset_sec + min_duration_sec,
            )
        if region_end <= onset_sec:
            continue
        regions.append((onset_sec, region_end))
    return regions


def estimate_pitch_for_region(
    audio: list[float],
    sr: int,
    *,
    region: tuple[float, float],
    config: OnsetNoteGeneratorConfig,
) -> tuple[int, float] | None:
    if not audio or sr <= 0:
        return None

    start_sec, end_sec = region
    if end_sec <= start_sec:
        return None

    signal = np.asarray(audio, dtype=np.float32)
    start_idx = max(0, int(start_sec * sr))
    end_idx = min(signal.size, int(end_sec * sr))
    segment = signal[start_idx:end_idx]
    if segment.size < max(128, int(sr * 0.04)):
        return None

    rms = float(np.sqrt(np.mean(np.square(segment), dtype=np.float64)))
    if rms <= 1e-3:
        return None

    segment = segment - float(np.mean(segment))
    segment = segment * np.hanning(segment.size)
    autocorr = np.correlate(segment, segment, mode="full")[segment.size - 1 :]
    if autocorr.size < 4 or autocorr[0] <= 0.0:
        return None
    autocorr = autocorr / float(autocorr[0])

    min_midi = 28
    max_midi = 64
    max_freq_hz = 440.0 * (2.0 ** ((max_midi - 69) / 12.0))
    min_freq_hz = 440.0 * (2.0 ** ((min_midi - 69) / 12.0))
    min_lag = max(1, int(sr / max_freq_hz))
    max_lag = min(autocorr.size - 1, int(sr / min_freq_hz))
    if max_lag <= min_lag:
        return None

    best_lag: int | None = None
    best_score = -1.0
    lag_range = max_lag - min_lag + 1
    for lag in range(min_lag, max_lag + 1):
        score = float(autocorr[lag])
        if (lag * 2) <= max_lag:
            score += 0.35 * float(autocorr[lag * 2])
        if (lag * 3) <= max_lag:
            score += 0.15 * float(autocorr[lag * 3])
        score += 0.03 * (lag - min_lag) / max(1, lag_range)
        if score > best_score:
            best_score = score
            best_lag = lag

    if best_lag is None or best_score <= 0.0:
        return None

    lower_octave_lag = best_lag * 2
    if lower_octave_lag <= max_lag:
        lower_octave_score = float(autocorr[lower_octave_lag]) + (0.45 * float(autocorr[best_lag]))
        if lower_octave_score >= (best_score * 0.92):
            best_lag = lower_octave_lag
            best_score = lower_octave_score

    frequency_hz = sr / float(best_lag)
    midi_pitch = int(round(69 + (12.0 * np.log2(frequency_hz / 440.0))))
    if not (min_midi <= midi_pitch <= max_midi):
        return None

    confidence = max(0.0, min(1.0, (best_score - 0.15) / 0.95))
    if confidence < config.minimum_pitch_confidence:
        return None
    return midi_pitch, confidence


class OnsetNoteGenerator:
    def __init__(
        self,
        *,
        audio_loader: AudioLoadFn | None = None,
        config: OnsetNoteGeneratorConfig | None = None,
    ) -> None:
        self._audio_loader = audio_loader or _load_audio_mono
        self._config = config or OnsetNoteGeneratorConfig()

    def generate(
        self,
        bass_wav: Path | str,
        *,
        onset_times: list[float] | None = None,
    ) -> list[OnsetNoteCandidate]:
        audio, sr = self._audio_loader(bass_wav)
        if not audio or sr <= 0:
            return []

        duration_sec = float(len(audio)) / float(sr)
        detected_onsets = list(onset_times) if onset_times is not None else detect_bass_onsets(audio, sr, config=self._config)
        regions = build_onset_regions(detected_onsets, audio_duration_sec=duration_sec, config=self._config)

        candidates: list[OnsetNoteCandidate] = []
        for region in regions:
            estimate = estimate_pitch_for_region(audio, sr, region=region, config=self._config)
            if estimate is None:
                continue
            pitch_midi, confidence = estimate
            candidates.append(
                OnsetNoteCandidate(
                    pitch_midi=int(pitch_midi),
                    start_sec=float(region[0]),
                    end_sec=float(region[1]),
                    confidence=float(confidence),
                    support={"region_start_sec": float(region[0]), "region_end_sec": float(region[1])},
                )
            )
        return candidates


def _moving_average(values: np.ndarray, *, window: int) -> np.ndarray:
    if window <= 1 or values.size <= 1:
        return values
    kernel = np.ones(window, dtype=np.float32) / float(window)
    return np.convolve(values, kernel, mode="same")


def _load_audio_mono(path: Path | str) -> tuple[list[float], int]:
    try:
        import librosa  # type: ignore
    except ModuleNotFoundError:
        return [], 22050

    audio, sr = librosa.load(str(path), sr=22050, mono=True)
    return [float(sample) for sample in audio], int(sr)
