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
    onset_region_pitch_enable: bool = True
    onset_region_pitch_method: str = "bass_harmonic_weighted"
    onset_region_octave_suppression_enable: bool = True
    onset_region_octave_penalty: float = 0.40
    onset_region_lowband_support_weight: float = 0.60
    onset_region_harmonic_penalty_weight: float = 0.35
    onset_region_pitch_floor_midi: int = 24
    onset_region_pitch_ceiling_midi: int = 64


@dataclass(frozen=True)
class OnsetRegionPitchEstimate:
    pitch_midi: int
    confidence: float
    support: dict[str, object] = field(default_factory=dict)


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

    ordered = _collapse_onset_times(
        sorted(max(0.0, float(onset)) for onset in onset_times),
        minimum_gap_sec=max(float(config.onset_min_spacing_ms) / 1000.0, 0.0),
    )
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
) -> OnsetRegionPitchEstimate | None:
    if not audio or sr <= 0:
        return None
    if not config.onset_region_pitch_enable:
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
    if rms <= 3e-3:
        return None

    centered = segment - float(np.mean(segment))
    min_midi = max(12, int(config.onset_region_pitch_floor_midi))
    max_midi = max(min_midi, int(config.onset_region_pitch_ceiling_midi))
    scored_candidates = _score_pitch_candidates(centered, sr=sr, config=config, limit=6)
    if not scored_candidates:
        return None
    frame_consensus = _frame_pitch_consensus(centered, sr=sr, config=config)
    scored_candidates = _merge_frame_consensus(scored_candidates, frame_consensus)
    if not scored_candidates:
        return None

    initial_candidate = dict(scored_candidates[0])
    final_candidate = dict(initial_candidate)
    octave_suppressed = False

    if config.onset_region_octave_suppression_enable:
        lower_octave_midi = int(initial_candidate["pitch_midi"]) - 12
        lower_candidate = next(
            (candidate for candidate in scored_candidates if int(candidate["pitch_midi"]) == lower_octave_midi),
            None,
        )
        if lower_candidate is not None and _should_prefer_lower_octave(
            initial_candidate=initial_candidate,
            lower_candidate=lower_candidate,
            config=config,
        ):
            final_candidate = dict(lower_candidate)
            octave_suppressed = True

    confidence = max(
        0.0,
        min(
            1.0,
            (0.55 * float(final_candidate["total_score"])) + (0.45 * float(final_candidate["autocorr_score"])),
        ),
    )
    if confidence < config.minimum_pitch_confidence:
        return None
    if float(final_candidate["lowband_support"]) < 0.02:
        return None

    support = {
        "region_start_sec": float(region[0]),
        "region_end_sec": float(region[1]),
        "initial_pitch_midi": int(initial_candidate["pitch_midi"]),
        "octave_suppressed": bool(octave_suppressed),
        "pitch_corrected": bool(int(final_candidate["pitch_midi"]) != int(initial_candidate["pitch_midi"])),
        "region_pitch_confidence": float(confidence),
        "evaluated_candidate_count": int(len(scored_candidates)),
        "autocorr_score": float(final_candidate["autocorr_score"]),
        "lowband_support": float(final_candidate["lowband_support"]),
        "harmonic_penalty": float(final_candidate["harmonic_penalty"]),
        "composite_score": float(final_candidate["total_score"]),
        "frame_primary_pitch_midi": frame_consensus["primary_pitch_midi"],
        "frame_support_ratio": float(final_candidate.get("frame_support_ratio", 0.0)),
        "frame_candidate_count": int(frame_consensus["frame_candidate_count"]),
        "method": str(config.onset_region_pitch_method),
    }
    return OnsetRegionPitchEstimate(
        pitch_midi=int(final_candidate["pitch_midi"]),
        confidence=float(confidence),
        support=support,
    )


class OnsetNoteGenerator:
    def __init__(
        self,
        *,
        audio_loader: AudioLoadFn | None = None,
        config: OnsetNoteGeneratorConfig | None = None,
    ) -> None:
        self._audio_loader = audio_loader or _load_audio_mono
        self._config = config or OnsetNoteGeneratorConfig()
        self.last_generation_summary: dict[str, object] = {
            "analyzed_region_count": 0,
            "accepted_pitch_count": 0,
            "rejected_weak_region_count": 0,
            "average_region_pitch_confidence": None,
            "octave_suppressed_count": 0,
            "pitch_corrected_region_count": 0,
            "accepted_pitch_range": {"min": None, "max": None},
        }

    def generate(
        self,
        bass_wav: Path | str,
        *,
        onset_times: list[float] | None = None,
    ) -> list[OnsetNoteCandidate]:
        audio, sr = self._audio_loader(bass_wav)
        if not audio or sr <= 0:
            self.last_generation_summary = {
                "analyzed_region_count": 0,
                "accepted_pitch_count": 0,
                "rejected_weak_region_count": 0,
                "average_region_pitch_confidence": None,
                "octave_suppressed_count": 0,
                "pitch_corrected_region_count": 0,
                "accepted_pitch_range": {"min": None, "max": None},
            }
            return []

        duration_sec = float(len(audio)) / float(sr)
        bounded_detected_onsets = detect_bass_onsets(audio, sr, config=self._config)
        detected_onsets = (
            list(onset_times)
            if onset_times is not None
            else list(bounded_detected_onsets)
        )
        if onset_times is not None and bounded_detected_onsets:
            if len(detected_onsets) > max(64, len(bounded_detected_onsets) * 2):
                detected_onsets = list(bounded_detected_onsets)
        regions = build_onset_regions(detected_onsets, audio_duration_sec=duration_sec, config=self._config)

        candidates: list[OnsetNoteCandidate] = []
        octave_suppressed_count = 0
        pitch_corrected_count = 0
        for region in regions:
            estimate = estimate_pitch_for_region(audio, sr, region=region, config=self._config)
            if estimate is None:
                continue
            if bool(estimate.support.get("octave_suppressed")):
                octave_suppressed_count += 1
            if bool(estimate.support.get("pitch_corrected")):
                pitch_corrected_count += 1
            candidates.append(
                OnsetNoteCandidate(
                    pitch_midi=int(estimate.pitch_midi),
                    start_sec=float(region[0]),
                    end_sec=float(region[1]),
                    confidence=float(estimate.confidence),
                    support=dict(estimate.support),
                )
            )
        accepted_confidences = [float(candidate.confidence) for candidate in candidates]
        accepted_pitches = [int(candidate.pitch_midi) for candidate in candidates]
        summary = {
            "analyzed_region_count": int(len(regions)),
            "accepted_pitch_count": int(len(candidates)),
            "rejected_weak_region_count": int(max(0, len(regions) - len(candidates))),
            "average_region_pitch_confidence": (
                float(sum(accepted_confidences) / len(accepted_confidences)) if accepted_confidences else None
            ),
            "octave_suppressed_count": int(octave_suppressed_count),
            "pitch_corrected_region_count": int(pitch_corrected_count),
            "accepted_pitch_range": {
                "min": int(min(accepted_pitches)) if accepted_pitches else None,
                "max": int(max(accepted_pitches)) if accepted_pitches else None,
            },
        }
        self.last_generation_summary = summary
        for candidate in candidates:
            candidate.support.update(summary)
        return candidates


def _moving_average(values: np.ndarray, *, window: int) -> np.ndarray:
    if window <= 1 or values.size <= 1:
        return values
    kernel = np.ones(window, dtype=np.float32) / float(window)
    return np.convolve(values, kernel, mode="same")


def _collapse_onset_times(onset_times: list[float], *, minimum_gap_sec: float) -> list[float]:
    if minimum_gap_sec <= 0.0:
        return [float(onset) for onset in onset_times]
    collapsed: list[float] = []
    for onset in onset_times:
        onset = float(onset)
        if not collapsed or (onset - collapsed[-1]) >= minimum_gap_sec:
            collapsed.append(onset)
    return collapsed


def _top_lag_candidates(
    autocorr: np.ndarray,
    *,
    min_lag: int,
    max_lag: int,
    limit: int,
) -> list[int]:
    peaks: list[tuple[float, int]] = []
    for lag in range(min_lag, max_lag + 1):
        current = float(autocorr[lag])
        if lag > min_lag and current < float(autocorr[lag - 1]):
            continue
        if lag < max_lag and current < float(autocorr[lag + 1]):
            continue
        peaks.append((current, lag))
    if not peaks:
        peaks = [(float(autocorr[lag]), lag) for lag in range(min_lag, max_lag + 1)]
    peaks.sort(key=lambda item: (-item[0], item[1]))
    return [lag for _score, lag in peaks[: max(1, limit)]]


def _score_pitch_candidates(
    signal: np.ndarray,
    *,
    sr: int,
    config: OnsetNoteGeneratorConfig,
    limit: int,
) -> list[dict[str, float | int | bool]]:
    windowed = signal * np.hanning(signal.size)
    n_fft = 1 << max(8, int(np.ceil(np.log2(max(2, windowed.size * 2)))))
    spectrum = np.fft.rfft(windowed, n=n_fft)
    power_spectrum = np.abs(spectrum) ** 2
    autocorr = np.fft.irfft(power_spectrum)
    autocorr = autocorr[: windowed.size]
    if autocorr.size < 4 or autocorr[0] <= 0.0:
        return []
    autocorr = autocorr / float(autocorr[0])

    min_midi = max(12, int(config.onset_region_pitch_floor_midi))
    max_midi = max(min_midi, int(config.onset_region_pitch_ceiling_midi))
    max_freq_hz = 440.0 * (2.0 ** ((max_midi - 69) / 12.0))
    min_freq_hz = 440.0 * (2.0 ** ((min_midi - 69) / 12.0))
    min_lag = max(1, int(sr / max_freq_hz))
    max_lag = min(autocorr.size - 1, int(sr / min_freq_hz))
    if max_lag <= min_lag:
        return []

    lag_candidates = _top_lag_candidates(autocorr, min_lag=min_lag, max_lag=max_lag, limit=4)
    if not lag_candidates:
        return []

    freqs = np.fft.rfftfreq(n_fft, d=1.0 / float(sr))
    spectral_magnitude = np.abs(spectrum)
    lowband_mask = freqs <= max(180.0, min_freq_hz * 3.2)
    lowband_peak = float(np.max(spectral_magnitude[lowband_mask])) if np.any(lowband_mask) else float(np.max(spectral_magnitude))
    candidate_by_midi: dict[int, dict[str, float | int | bool]] = {}
    for lag in lag_candidates:
        score = _score_pitch_candidate(
            lag=lag,
            sr=sr,
            autocorr=autocorr,
            freqs=freqs,
            spectral_magnitude=spectral_magnitude,
            lowband_peak=lowband_peak,
            config=config,
        )
        if score is None:
            continue
        midi_pitch = int(score["pitch_midi"])
        existing = candidate_by_midi.get(midi_pitch)
        if existing is None or float(score["total_score"]) > float(existing["total_score"]):
            candidate_by_midi[midi_pitch] = score
        if config.onset_region_octave_suppression_enable:
            lower_lag = int(lag * 2)
            if lower_lag <= max_lag:
                lower_score = _score_pitch_candidate(
                    lag=lower_lag,
                    sr=sr,
                    autocorr=autocorr,
                    freqs=freqs,
                    spectral_magnitude=spectral_magnitude,
                    lowband_peak=lowband_peak,
                    config=config,
                )
                if lower_score is not None:
                    lower_midi = int(lower_score["pitch_midi"])
                    existing_lower = candidate_by_midi.get(lower_midi)
                    if existing_lower is None or float(lower_score["total_score"]) > float(existing_lower["total_score"]):
                        candidate_by_midi[lower_midi] = lower_score

    ranked = sorted(
        candidate_by_midi.values(),
        key=lambda candidate: (
            -float(candidate["total_score"]),
            -float(candidate["autocorr_score"]),
            int(candidate["pitch_midi"]),
        ),
    )
    return ranked[: max(1, limit)]


def _frame_pitch_consensus(
    signal: np.ndarray,
    *,
    sr: int,
    config: OnsetNoteGeneratorConfig,
) -> dict[str, object]:
    frame_size = min(signal.size, max(int(sr * 0.050), 192))
    hop_size = max(int(frame_size * 0.4), int(sr * 0.012))
    if frame_size <= 0 or hop_size <= 0 or signal.size < frame_size:
        return {"primary_pitch_midi": None, "frame_candidate_count": 0, "by_midi": {}}

    vote_accumulator: dict[int, dict[str, float | int]] = {}
    frame_candidate_count = 0
    for start in range(0, signal.size - frame_size + 1, hop_size):
        frame = signal[start : start + frame_size]
        frame_rms = float(np.sqrt(np.mean(np.square(frame), dtype=np.float64)))
        if frame_rms <= 2e-3:
            continue
        candidates = _score_pitch_candidates(frame, sr=sr, config=config, limit=3)
        if not candidates:
            continue
        frame_candidate_count += 1
        best = candidates[0]
        if config.onset_region_octave_suppression_enable:
            lower_octave_midi = int(best["pitch_midi"]) - 12
            lower_candidate = next(
                (candidate for candidate in candidates if int(candidate["pitch_midi"]) == lower_octave_midi),
                None,
            )
            if lower_candidate is not None and _should_prefer_lower_octave(
                initial_candidate=best,
                lower_candidate=lower_candidate,
                config=config,
            ):
                best = lower_candidate
        midi_pitch = int(best["pitch_midi"])
        bucket = vote_accumulator.setdefault(
            midi_pitch,
            {
                "vote_count": 0,
                "sum_total_score": 0.0,
                "sum_autocorr_score": 0.0,
                "sum_lowband_support": 0.0,
            },
        )
        bucket["vote_count"] = int(bucket["vote_count"]) + 1
        bucket["sum_total_score"] = float(bucket["sum_total_score"]) + float(best["total_score"])
        bucket["sum_autocorr_score"] = float(bucket["sum_autocorr_score"]) + float(best["autocorr_score"])
        bucket["sum_lowband_support"] = float(bucket["sum_lowband_support"]) + float(best["lowband_support"])

    if frame_candidate_count <= 0:
        return {"primary_pitch_midi": None, "frame_candidate_count": 0, "by_midi": {}}

    primary_pitch_midi = None
    ranked_votes = sorted(
        vote_accumulator.items(),
        key=lambda item: (
            -int(item[1]["vote_count"]),
            -(float(item[1]["sum_total_score"]) / max(1, int(item[1]["vote_count"]))),
            int(item[0]),
        ),
    )
    if ranked_votes:
        primary_pitch_midi = int(ranked_votes[0][0])

    by_midi: dict[int, dict[str, float | int]] = {}
    for midi_pitch, bucket in vote_accumulator.items():
        vote_count = int(bucket["vote_count"])
        by_midi[midi_pitch] = {
            "vote_count": vote_count,
            "support_ratio": float(vote_count) / float(frame_candidate_count),
            "mean_total_score": float(bucket["sum_total_score"]) / float(vote_count),
            "mean_autocorr_score": float(bucket["sum_autocorr_score"]) / float(vote_count),
            "mean_lowband_support": float(bucket["sum_lowband_support"]) / float(vote_count),
        }
    return {
        "primary_pitch_midi": primary_pitch_midi,
        "frame_candidate_count": frame_candidate_count,
        "by_midi": by_midi,
    }


def _merge_frame_consensus(
    scored_candidates: list[dict[str, float | int | bool]],
    frame_consensus: dict[str, object],
) -> list[dict[str, float | int | bool]]:
    by_midi = frame_consensus.get("by_midi")
    if not isinstance(by_midi, dict):
        return scored_candidates
    primary_pitch_midi = frame_consensus.get("primary_pitch_midi")
    merged: list[dict[str, float | int | bool]] = []
    for candidate in scored_candidates:
        midi_pitch = int(candidate["pitch_midi"])
        frame_entry = by_midi.get(midi_pitch)
        merged_candidate = dict(candidate)
        if isinstance(frame_entry, dict):
            support_ratio = float(frame_entry.get("support_ratio", 0.0))
            mean_total_score = float(frame_entry.get("mean_total_score", 0.0))
            merged_candidate["frame_vote_count"] = int(frame_entry.get("vote_count", 0))
            merged_candidate["frame_support_ratio"] = support_ratio
            merged_candidate["frame_mean_total_score"] = mean_total_score
            merged_candidate["frame_mean_lowband_support"] = float(frame_entry.get("mean_lowband_support", 0.0))
            merged_candidate["combined_score"] = (
                (0.58 * float(candidate["total_score"]))
                + (0.24 * mean_total_score)
                + (0.18 * support_ratio)
                + (0.05 if primary_pitch_midi == midi_pitch else 0.0)
            )
        else:
            merged_candidate["frame_vote_count"] = 0
            merged_candidate["frame_support_ratio"] = 0.0
            merged_candidate["frame_mean_total_score"] = 0.0
            merged_candidate["frame_mean_lowband_support"] = 0.0
            merged_candidate["combined_score"] = float(candidate["total_score"])
        merged.append(merged_candidate)
    return sorted(
        merged,
        key=lambda candidate: (
            -float(candidate.get("combined_score", candidate["total_score"])),
            -float(candidate["total_score"]),
            -float(candidate["autocorr_score"]),
            int(candidate["pitch_midi"]),
        ),
    )[:6]


def _score_pitch_candidate(
    *,
    lag: int,
    sr: int,
    autocorr: np.ndarray,
    freqs: np.ndarray,
    spectral_magnitude: np.ndarray,
    lowband_peak: float,
    config: OnsetNoteGeneratorConfig,
) -> dict[str, float | int | bool] | None:
    if lag <= 0:
        return None
    frequency_hz = sr / float(lag)
    pitch_midi = int(round(69 + (12.0 * np.log2(frequency_hz / 440.0))))
    if not (config.onset_region_pitch_floor_midi <= pitch_midi <= config.onset_region_pitch_ceiling_midi):
        return None

    autocorr_score = max(0.0, float(autocorr[lag]))
    if autocorr_score <= 0.0:
        return None

    fundamental_energy = _band_energy(freqs, spectral_magnitude, frequency_hz)
    second_energy = _band_energy(freqs, spectral_magnitude, frequency_hz * 2.0)
    third_energy = _band_energy(freqs, spectral_magnitude, frequency_hz * 3.0)
    lowband_support = (
        (fundamental_energy + (0.60 * second_energy) + (0.30 * third_energy)) / max(lowband_peak, 1e-6)
    )
    harmonic_penalty = max(0.0, second_energy - (1.10 * fundamental_energy)) / max(lowband_peak, 1e-6)
    total_score = (
        (0.52 * autocorr_score)
        + (float(config.onset_region_lowband_support_weight) * min(1.0, lowband_support))
        - (float(config.onset_region_harmonic_penalty_weight) * min(1.0, harmonic_penalty))
    )
    return {
        "lag": int(lag),
        "pitch_midi": int(pitch_midi),
        "frequency_hz": float(frequency_hz),
        "autocorr_score": float(autocorr_score),
        "fundamental_energy": float(fundamental_energy),
        "second_energy": float(second_energy),
        "third_energy": float(third_energy),
        "lowband_support": float(lowband_support),
        "harmonic_penalty": float(harmonic_penalty),
        "total_score": float(total_score),
    }


def _should_prefer_lower_octave(
    *,
    initial_candidate: dict[str, float | int | bool],
    lower_candidate: dict[str, float | int | bool],
    config: OnsetNoteGeneratorConfig,
) -> bool:
    lower_fundamental = float(lower_candidate["fundamental_energy"])
    lower_harmonic_support = float(lower_candidate["second_energy"])
    initial_fundamental = float(initial_candidate["fundamental_energy"])
    lower_autocorr = float(lower_candidate["autocorr_score"])
    initial_autocorr = float(initial_candidate["autocorr_score"])
    lower_total = float(lower_candidate.get("combined_score", lower_candidate["total_score"]))
    initial_total = float(initial_candidate.get("combined_score", initial_candidate["total_score"]))
    lower_frame_support = float(lower_candidate.get("frame_support_ratio", 0.0))
    initial_frame_support = float(initial_candidate.get("frame_support_ratio", 0.0))

    lower_supported = lower_fundamental >= (initial_fundamental * 0.18) or lower_harmonic_support >= (initial_fundamental * 0.85)
    if not lower_supported:
        return False

    suppression_bonus = (
        float(config.onset_region_octave_penalty)
        * (
            (0.55 * float(lower_candidate["lowband_support"]))
            + (0.25 * lower_autocorr)
            + (0.20 * max(0.0, lower_frame_support - initial_frame_support))
        )
    )
    return (lower_total + suppression_bonus) >= (initial_total - (0.12 * initial_autocorr))


def _band_energy(freqs: np.ndarray, spectral_magnitude: np.ndarray, target_hz: float) -> float:
    if target_hz <= 0.0 or freqs.size == 0:
        return 0.0
    bandwidth_hz = max(2.5, target_hz * 0.055)
    band = (freqs >= (target_hz - bandwidth_hz)) & (freqs <= (target_hz + bandwidth_hz))
    if not np.any(band):
        return 0.0
    return float(np.max(spectral_magnitude[band]))


def _load_audio_mono(path: Path | str) -> tuple[list[float], int]:
    try:
        import librosa  # type: ignore
    except ModuleNotFoundError:
        return [], 22050

    audio, sr = librosa.load(str(path), sr=22050, mono=True)
    return [float(sample) for sample in audio], int(sr)
