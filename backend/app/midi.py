from __future__ import annotations

import subprocess
import tempfile
import os
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Callable

import numpy as np
from mido import Message, MetaMessage, MidiFile, MidiTrack, second2tick

from app.stems import StemAnalysisConfig, _get_stem_analysis_config
from app.stems import _load_stem_env, _parse_bool_env, _parse_float_env_bounded, _parse_int_env

MidiTranscribeFn = Callable[[Path, Path], None]
FallbackTranscribeFn = Callable[[Path, Path], dict[str, object] | None]


@dataclass(frozen=True)
class MidiTranscriptionResult:
    midi_bytes: bytes
    engine_used: str
    diagnostics: dict[str, object]


DEFAULT_PITCH_STABILITY_ENABLE = True
DEFAULT_PITCH_MIN_CONFIDENCE = 0.55
DEFAULT_PITCH_TRANSITION_HYSTERESIS_FRAMES = 3
DEFAULT_PITCH_OCTAVE_JUMP_PENALTY = 0.8
DEFAULT_PITCH_MAX_CENTS_DRIFT_WITHIN_NOTE = 45.0
DEFAULT_PITCH_MIN_NOTE_DURATION_MS = 70
DEFAULT_PITCH_MERGE_GAP_MS = 40
DEFAULT_PITCH_SMOOTHING_WINDOW_FRAMES = 5
DEFAULT_PITCH_HARMONIC_RECHECK_ENABLE = True
DEFAULT_NOTE_ADMISSION_ENABLE = True
DEFAULT_NOTE_MIN_DURATION_MS = 60
DEFAULT_NOTE_LOW_CONFIDENCE_THRESHOLD = 0.45
DEFAULT_NOTE_OCTAVE_INTRUSION_MAX_DURATION_MS = 90
DEFAULT_NOTE_MERGE_GAP_MS = 45
DEFAULT_NOTE_DENSE_CANDIDATE_MIN_DURATION_MS = 55
DEFAULT_NOTE_DENSE_UNSTABLE_CONTEXT_PENALTY = 0.20
DEFAULT_NOTE_DENSE_OCTAVE_NEIGHBOR_PENALTY = 0.25
DEFAULT_RAW_NOTE_RECALL_ENABLE = False
DEFAULT_RAW_NOTE_MIN_CONFIDENCE = 0.15
DEFAULT_RAW_NOTE_MIN_DURATION_MS = 35
DEFAULT_RAW_NOTE_ALLOW_WEAK_BASS_CANDIDATES = False
DEFAULT_RAW_NOTE_SPARSE_REGION_BOOST_ENABLE = False
DEFAULT_DENSE_CANDIDATE_SPARSE_REGION_THRESHOLD_MS = 180
DEFAULT_DENSE_CANDIDATE_SUPPORT_RELAXATION = 0.20
DEFAULT_ONSET_NOTE_GENERATOR_ENABLE = False
DEFAULT_ONSET_NOTE_GENERATOR_MODE = "fallback"
DEFAULT_ONSET_MIN_SPACING_MS = 70
DEFAULT_ONSET_STRENGTH_THRESHOLD = 0.35
DEFAULT_ONSET_REGION_MAX_DURATION_MS = 220
DEFAULT_ONSET_REGION_MIN_DURATION_MS = 40
DEFAULT_ONSET_DENSITY_NOTES_PER_SEC_THRESHOLD = 4.5


@dataclass(frozen=True)
class PitchStabilityConfig:
    pitch_stability_enable: bool = DEFAULT_PITCH_STABILITY_ENABLE
    pitch_min_confidence: float = DEFAULT_PITCH_MIN_CONFIDENCE
    pitch_transition_hysteresis_frames: int = DEFAULT_PITCH_TRANSITION_HYSTERESIS_FRAMES
    pitch_octave_jump_penalty: float = DEFAULT_PITCH_OCTAVE_JUMP_PENALTY
    pitch_max_cents_drift_within_note: float = DEFAULT_PITCH_MAX_CENTS_DRIFT_WITHIN_NOTE
    pitch_min_note_duration_ms: int = DEFAULT_PITCH_MIN_NOTE_DURATION_MS
    pitch_merge_gap_ms: int = DEFAULT_PITCH_MERGE_GAP_MS
    pitch_smoothing_window_frames: int = DEFAULT_PITCH_SMOOTHING_WINDOW_FRAMES
    pitch_harmonic_recheck_enable: bool = DEFAULT_PITCH_HARMONIC_RECHECK_ENABLE
    note_admission_enable: bool = DEFAULT_NOTE_ADMISSION_ENABLE
    note_min_duration_ms: int = DEFAULT_NOTE_MIN_DURATION_MS
    note_low_confidence_threshold: float = DEFAULT_NOTE_LOW_CONFIDENCE_THRESHOLD
    note_octave_intrusion_max_duration_ms: int = DEFAULT_NOTE_OCTAVE_INTRUSION_MAX_DURATION_MS
    note_merge_gap_ms: int = DEFAULT_NOTE_MERGE_GAP_MS
    note_dense_candidate_min_duration_ms: int = DEFAULT_NOTE_DENSE_CANDIDATE_MIN_DURATION_MS
    note_dense_unstable_context_penalty: float = DEFAULT_NOTE_DENSE_UNSTABLE_CONTEXT_PENALTY
    note_dense_octave_neighbor_penalty: float = DEFAULT_NOTE_DENSE_OCTAVE_NEIGHBOR_PENALTY
    raw_note_recall_enable: bool = DEFAULT_RAW_NOTE_RECALL_ENABLE
    raw_note_min_confidence: float = DEFAULT_RAW_NOTE_MIN_CONFIDENCE
    raw_note_min_duration_ms: int = DEFAULT_RAW_NOTE_MIN_DURATION_MS
    raw_note_allow_weak_bass_candidates: bool = DEFAULT_RAW_NOTE_ALLOW_WEAK_BASS_CANDIDATES
    raw_note_sparse_region_boost_enable: bool = DEFAULT_RAW_NOTE_SPARSE_REGION_BOOST_ENABLE
    dense_candidate_sparse_region_threshold_ms: int = DEFAULT_DENSE_CANDIDATE_SPARSE_REGION_THRESHOLD_MS
    dense_candidate_support_relaxation: float = DEFAULT_DENSE_CANDIDATE_SUPPORT_RELAXATION
    onset_note_generator_enable: bool = DEFAULT_ONSET_NOTE_GENERATOR_ENABLE
    onset_note_generator_mode: str = DEFAULT_ONSET_NOTE_GENERATOR_MODE
    onset_min_spacing_ms: int = DEFAULT_ONSET_MIN_SPACING_MS
    onset_strength_threshold: float = DEFAULT_ONSET_STRENGTH_THRESHOLD
    onset_region_max_duration_ms: int = DEFAULT_ONSET_REGION_MAX_DURATION_MS
    onset_region_min_duration_ms: int = DEFAULT_ONSET_REGION_MIN_DURATION_MS
    onset_density_notes_per_sec_threshold: float = DEFAULT_ONSET_DENSITY_NOTES_PER_SEC_THRESHOLD


def _get_pitch_stability_config() -> PitchStabilityConfig:
    _load_stem_env()
    min_confidence = _parse_float_env_bounded(
        "DECHORD_PITCH_MIN_CONFIDENCE",
        DEFAULT_PITCH_MIN_CONFIDENCE,
        minimum=0.0,
        maximum=1.0,
    )
    hysteresis_frames = _parse_int_env(
        "DECHORD_PITCH_TRANSITION_HYSTERESIS_FRAMES",
        DEFAULT_PITCH_TRANSITION_HYSTERESIS_FRAMES,
    )
    if hysteresis_frames is None or hysteresis_frames < 1:
        hysteresis_frames = DEFAULT_PITCH_TRANSITION_HYSTERESIS_FRAMES
    octave_jump_penalty = _parse_float_env_bounded(
        "DECHORD_PITCH_OCTAVE_JUMP_PENALTY",
        DEFAULT_PITCH_OCTAVE_JUMP_PENALTY,
        minimum=0.0,
        maximum=4.0,
    )
    max_cents_drift = _parse_float_env_bounded(
        "DECHORD_PITCH_MAX_CENTS_DRIFT_WITHIN_NOTE",
        DEFAULT_PITCH_MAX_CENTS_DRIFT_WITHIN_NOTE,
        minimum=1.0,
        maximum=2400.0,
    )
    min_note_duration_ms = _parse_int_env(
        "DECHORD_PITCH_MIN_NOTE_DURATION_MS",
        DEFAULT_PITCH_MIN_NOTE_DURATION_MS,
    )
    if min_note_duration_ms is None or min_note_duration_ms < 1:
        min_note_duration_ms = DEFAULT_PITCH_MIN_NOTE_DURATION_MS
    merge_gap_ms = _parse_int_env("DECHORD_PITCH_MERGE_GAP_MS", DEFAULT_PITCH_MERGE_GAP_MS)
    if merge_gap_ms is None or merge_gap_ms < 0:
        merge_gap_ms = DEFAULT_PITCH_MERGE_GAP_MS
    smoothing_window = _parse_int_env(
        "DECHORD_PITCH_SMOOTHING_WINDOW_FRAMES",
        DEFAULT_PITCH_SMOOTHING_WINDOW_FRAMES,
    )
    if smoothing_window is None or smoothing_window < 1:
        smoothing_window = DEFAULT_PITCH_SMOOTHING_WINDOW_FRAMES
    note_min_duration_ms = _parse_int_env(
        "DECHORD_NOTE_MIN_DURATION_MS",
        DEFAULT_NOTE_MIN_DURATION_MS,
    )
    if note_min_duration_ms is None or note_min_duration_ms < 1:
        note_min_duration_ms = DEFAULT_NOTE_MIN_DURATION_MS
    note_octave_intrusion_max_duration_ms = _parse_int_env(
        "DECHORD_NOTE_OCTAVE_INTRUSION_MAX_DURATION_MS",
        DEFAULT_NOTE_OCTAVE_INTRUSION_MAX_DURATION_MS,
    )
    if note_octave_intrusion_max_duration_ms is None or note_octave_intrusion_max_duration_ms < 1:
        note_octave_intrusion_max_duration_ms = DEFAULT_NOTE_OCTAVE_INTRUSION_MAX_DURATION_MS
    note_merge_gap_ms = _parse_int_env(
        "DECHORD_NOTE_MERGE_GAP_MS",
        DEFAULT_NOTE_MERGE_GAP_MS,
    )
    if note_merge_gap_ms is None or note_merge_gap_ms < 0:
        note_merge_gap_ms = DEFAULT_NOTE_MERGE_GAP_MS
    note_dense_candidate_min_duration_ms = _parse_int_env(
        "DECHORD_DENSE_CANDIDATE_MIN_DURATION_MS",
        DEFAULT_NOTE_DENSE_CANDIDATE_MIN_DURATION_MS,
    )
    if note_dense_candidate_min_duration_ms is None or note_dense_candidate_min_duration_ms < 1:
        note_dense_candidate_min_duration_ms = DEFAULT_NOTE_DENSE_CANDIDATE_MIN_DURATION_MS
    raw_note_min_duration_ms = _parse_int_env(
        "DECHORD_RAW_NOTE_MIN_DURATION_MS",
        DEFAULT_RAW_NOTE_MIN_DURATION_MS,
    )
    if raw_note_min_duration_ms is None or raw_note_min_duration_ms < 1:
        raw_note_min_duration_ms = DEFAULT_RAW_NOTE_MIN_DURATION_MS
    dense_candidate_sparse_region_threshold_ms = _parse_int_env(
        "DECHORD_DENSE_CANDIDATE_SPARSE_REGION_THRESHOLD_MS",
        DEFAULT_DENSE_CANDIDATE_SPARSE_REGION_THRESHOLD_MS,
    )
    if dense_candidate_sparse_region_threshold_ms is None or dense_candidate_sparse_region_threshold_ms < 1:
        dense_candidate_sparse_region_threshold_ms = DEFAULT_DENSE_CANDIDATE_SPARSE_REGION_THRESHOLD_MS
    onset_min_spacing_ms = _parse_int_env(
        "DECHORD_ONSET_MIN_SPACING_MS",
        DEFAULT_ONSET_MIN_SPACING_MS,
    )
    if onset_min_spacing_ms is None or onset_min_spacing_ms < 1:
        onset_min_spacing_ms = DEFAULT_ONSET_MIN_SPACING_MS
    onset_region_max_duration_ms = _parse_int_env(
        "DECHORD_ONSET_REGION_MAX_DURATION_MS",
        DEFAULT_ONSET_REGION_MAX_DURATION_MS,
    )
    if onset_region_max_duration_ms is None or onset_region_max_duration_ms < 1:
        onset_region_max_duration_ms = DEFAULT_ONSET_REGION_MAX_DURATION_MS
    onset_region_min_duration_ms = _parse_int_env(
        "DECHORD_ONSET_REGION_MIN_DURATION_MS",
        DEFAULT_ONSET_REGION_MIN_DURATION_MS,
    )
    if onset_region_min_duration_ms is None or onset_region_min_duration_ms < 1:
        onset_region_min_duration_ms = DEFAULT_ONSET_REGION_MIN_DURATION_MS
    if onset_region_min_duration_ms > onset_region_max_duration_ms:
        onset_region_min_duration_ms = onset_region_max_duration_ms
    onset_note_generator_mode = str(
        os.getenv("DECHORD_ONSET_NOTE_GENERATOR_MODE", DEFAULT_ONSET_NOTE_GENERATOR_MODE)
    ).strip().lower()
    if onset_note_generator_mode not in {"fallback", "merged", "primary"}:
        onset_note_generator_mode = DEFAULT_ONSET_NOTE_GENERATOR_MODE
    return PitchStabilityConfig(
        pitch_stability_enable=_parse_bool_env(
            "DECHORD_PITCH_STABILITY_ENABLE",
            DEFAULT_PITCH_STABILITY_ENABLE,
        ),
        pitch_min_confidence=min_confidence,
        pitch_transition_hysteresis_frames=hysteresis_frames,
        pitch_octave_jump_penalty=octave_jump_penalty,
        pitch_max_cents_drift_within_note=max_cents_drift,
        pitch_min_note_duration_ms=min_note_duration_ms,
        pitch_merge_gap_ms=merge_gap_ms,
        pitch_smoothing_window_frames=smoothing_window,
        pitch_harmonic_recheck_enable=_parse_bool_env(
            "DECHORD_PITCH_HARMONIC_RECHECK_ENABLE",
            DEFAULT_PITCH_HARMONIC_RECHECK_ENABLE,
        ),
        note_admission_enable=_parse_bool_env(
            "DECHORD_NOTE_ADMISSION_ENABLE",
            DEFAULT_NOTE_ADMISSION_ENABLE,
        ),
        note_min_duration_ms=note_min_duration_ms,
        note_low_confidence_threshold=_parse_float_env_bounded(
            "DECHORD_NOTE_LOW_CONFIDENCE_THRESHOLD",
            DEFAULT_NOTE_LOW_CONFIDENCE_THRESHOLD,
            minimum=0.0,
            maximum=1.0,
        ),
        note_octave_intrusion_max_duration_ms=note_octave_intrusion_max_duration_ms,
        note_merge_gap_ms=note_merge_gap_ms,
        note_dense_candidate_min_duration_ms=note_dense_candidate_min_duration_ms,
        note_dense_unstable_context_penalty=_parse_float_env_bounded(
            "DECHORD_DENSE_UNSTABLE_CONTEXT_PENALTY",
            DEFAULT_NOTE_DENSE_UNSTABLE_CONTEXT_PENALTY,
            minimum=0.0,
            maximum=1.0,
        ),
        note_dense_octave_neighbor_penalty=_parse_float_env_bounded(
            "DECHORD_DENSE_OCTAVE_NEIGHBOR_PENALTY",
            DEFAULT_NOTE_DENSE_OCTAVE_NEIGHBOR_PENALTY,
            minimum=0.0,
            maximum=1.0,
        ),
        raw_note_recall_enable=_parse_bool_env(
            "DECHORD_RAW_NOTE_RECALL_ENABLE",
            DEFAULT_RAW_NOTE_RECALL_ENABLE,
        ),
        raw_note_min_confidence=_parse_float_env_bounded(
            "DECHORD_RAW_NOTE_MIN_CONFIDENCE",
            DEFAULT_RAW_NOTE_MIN_CONFIDENCE,
            minimum=0.0,
            maximum=1.0,
        ),
        raw_note_min_duration_ms=raw_note_min_duration_ms,
        raw_note_allow_weak_bass_candidates=_parse_bool_env(
            "DECHORD_RAW_NOTE_ALLOW_WEAK_BASS_CANDIDATES",
            DEFAULT_RAW_NOTE_ALLOW_WEAK_BASS_CANDIDATES,
        ),
        raw_note_sparse_region_boost_enable=_parse_bool_env(
            "DECHORD_RAW_NOTE_SPARSE_REGION_BOOST_ENABLE",
            DEFAULT_RAW_NOTE_SPARSE_REGION_BOOST_ENABLE,
        ),
        dense_candidate_sparse_region_threshold_ms=dense_candidate_sparse_region_threshold_ms,
        dense_candidate_support_relaxation=_parse_float_env_bounded(
            "DECHORD_DENSE_CANDIDATE_SUPPORT_RELAXATION",
            DEFAULT_DENSE_CANDIDATE_SUPPORT_RELAXATION,
            minimum=0.0,
            maximum=1.0,
        ),
        onset_note_generator_enable=_parse_bool_env(
            "DECHORD_ONSET_NOTE_GENERATOR_ENABLE",
            DEFAULT_ONSET_NOTE_GENERATOR_ENABLE,
        ),
        onset_note_generator_mode=onset_note_generator_mode,
        onset_min_spacing_ms=onset_min_spacing_ms,
        onset_strength_threshold=_parse_float_env_bounded(
            "DECHORD_ONSET_STRENGTH_THRESHOLD",
            DEFAULT_ONSET_STRENGTH_THRESHOLD,
            minimum=0.0,
            maximum=1.0,
        ),
        onset_region_max_duration_ms=onset_region_max_duration_ms,
        onset_region_min_duration_ms=onset_region_min_duration_ms,
        onset_density_notes_per_sec_threshold=_parse_float_env_bounded(
            "DECHORD_ONSET_DENSITY_NOTES_PER_SEC_THRESHOLD",
            DEFAULT_ONSET_DENSITY_NOTES_PER_SEC_THRESHOLD,
            minimum=0.1,
            maximum=64.0,
        ),
    )


def _serialize_basic_pitch_note_events(note_events: object) -> list[dict[str, float | int]]:
    serialized: list[dict[str, float | int]] = []
    if not isinstance(note_events, list):
        return serialized
    for event in note_events:
        start_sec: float | None = None
        end_sec: float | None = None
        pitch_midi: int | None = None
        confidence: float | None = None
        if isinstance(event, dict):
            start_value = event.get("start_time") if "start_time" in event else event.get("start_sec")
            end_value = event.get("end_time") if "end_time" in event else event.get("end_sec")
            pitch_value = event.get("pitch_midi") if "pitch_midi" in event else event.get("pitch")
            confidence_value = event.get("confidence") if "confidence" in event else event.get("amplitude")
            if isinstance(start_value, int | float) and isinstance(end_value, int | float) and isinstance(pitch_value, int | float):
                start_sec = float(start_value)
                end_sec = float(end_value)
                pitch_midi = int(round(float(pitch_value)))
                if isinstance(confidence_value, int | float):
                    confidence = float(confidence_value)
        elif isinstance(event, tuple | list) and len(event) >= 3:
            start_value, end_value, pitch_value = event[0], event[1], event[2]
            confidence_value = event[3] if len(event) >= 4 else 0.0
            if isinstance(start_value, int | float) and isinstance(end_value, int | float) and isinstance(pitch_value, int | float):
                start_sec = float(start_value)
                end_sec = float(end_value)
                pitch_midi = int(round(float(pitch_value)))
                if isinstance(confidence_value, int | float):
                    confidence = float(confidence_value)
        if start_sec is None or end_sec is None or pitch_midi is None:
            continue
        serialized.append(
            {
                "start_sec": start_sec,
                "end_sec": end_sec,
                "pitch_midi": int(pitch_midi),
                "confidence": float(confidence if confidence is not None else 0.0),
            }
        )
    return serialized


def _preprocess_bass_for_basic_pitch_transcription(input_path: Path, output_path: Path) -> None:
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_path),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "22050",
        "-af",
        "highpass=f=30,lowpass=f=650",
        "-f",
        "wav",
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg preprocessing failed: {result.stderr.strip()}")


def _transcribe_with_basic_pitch(input_path: Path, output_path: Path) -> dict[str, object] | None:
    try:
        from basic_pitch.inference import predict  # type: ignore
    except ModuleNotFoundError as exc:  # pragma: no cover - depends on optional runtime dep
        raise RuntimeError(
            f"Stem runtime dependency missing: {exc}. Run `cd backend && uv sync`."
        ) from exc

    prepared_input = input_path
    preprocessing_applied = False
    with TemporaryDirectory(prefix="dechord-basic-pitch-") as tmp_dir:
        preprocessed_path = Path(tmp_dir) / "basic_pitch_bass.wav"
        try:
            _preprocess_bass_for_basic_pitch_transcription(input_path, preprocessed_path)
            prepared_input = preprocessed_path
            preprocessing_applied = True
        except Exception:
            prepared_input = input_path
            preprocessing_applied = False
        _model_output, midi_data, note_events = predict(str(prepared_input))
    midi_data.write(str(output_path))
    return {
        "basic_pitch_note_events": _serialize_basic_pitch_note_events(note_events),
        "basic_pitch_preprocessed_input": int(preprocessing_applied),
    }


def _midi_to_hz(midi_note: int) -> float:
    return 440.0 * (2.0 ** ((float(midi_note) - 69.0) / 12.0))


def _hz_to_midi(hz: np.ndarray) -> np.ndarray:
    with np.errstate(divide="ignore", invalid="ignore"):
        return 69.0 + 12.0 * np.log2(hz / 440.0)


def _transition_cost(prev_midi: int, curr_midi: int) -> float:
    delta = abs(curr_midi - prev_midi)
    if delta == 0:
        return 0.0
    cost = min(delta, 12) * 0.35 + max(0, delta - 5) * 0.8
    if delta == 12:
        cost += 8.0
    elif delta > 12:
        cost += 12.0
    if delta <= 2:
        cost -= 0.4
    return max(cost, 0.0)


def _smooth_midi_track_viterbi(midi_track: np.ndarray, voiced_prob: np.ndarray) -> np.ndarray:
    if midi_track.size == 0:
        return np.array([], dtype=int)

    valid = np.isfinite(midi_track) & (voiced_prob >= 0.2)
    smoothed = np.full(midi_track.shape, -1, dtype=int)
    idx = 0
    while idx < midi_track.size:
        if not valid[idx]:
            idx += 1
            continue
        seg_start = idx
        while idx < midi_track.size and valid[idx]:
            idx += 1
        seg_end = idx
        segment = midi_track[seg_start:seg_end]
        segment_prob = voiced_prob[seg_start:seg_end]
        if segment.size == 1:
            smoothed[seg_start] = int(np.clip(round(float(segment[0])), 28, 76))
            continue

        candidates: list[list[int]] = []
        for raw in segment:
            center = int(round(float(raw)))
            cands = sorted({center - 12, center, center + 12})
            cands = [cand for cand in cands if 28 <= cand <= 76]
            if not cands:
                cands = [int(np.clip(center, 28, 76))]
            candidates.append(cands)

        scores: list[dict[int, float]] = []
        paths: list[dict[int, int]] = []
        first_scores: dict[int, float] = {}
        for cand in candidates[0]:
            first_scores[cand] = abs(cand - float(segment[0]))
        scores.append(first_scores)
        paths.append({})

        for pos in range(1, len(candidates)):
            cur_scores: dict[int, float] = {}
            cur_path: dict[int, int] = {}
            emission_weight = 1.0 - min(float(segment_prob[pos]), 0.99) * 0.4
            for cand in candidates[pos]:
                emission = abs(cand - float(segment[pos])) * emission_weight
                best_prev = min(
                    candidates[pos - 1],
                    key=lambda prev: scores[pos - 1][prev] + _transition_cost(prev, cand),
                )
                cur_scores[cand] = scores[pos - 1][best_prev] + _transition_cost(best_prev, cand) + emission
                cur_path[cand] = best_prev
            scores.append(cur_scores)
            paths.append(cur_path)

        last_cand = min(scores[-1], key=scores[-1].get)
        best_path = [last_cand]
        for pos in range(len(candidates) - 1, 0, -1):
            last_cand = paths[pos][last_cand]
            best_path.append(last_cand)
        best_path.reverse()
        smoothed[seg_start:seg_end] = np.array(best_path, dtype=int)

    return smoothed


def _band_energy(freqs: np.ndarray, spectrogram: np.ndarray, frame_idx: int, target_hz: float) -> float:
    if target_hz <= 0:
        return 0.0
    lower = target_hz * 0.97
    upper = target_hz * 1.03
    band = (freqs >= lower) & (freqs <= upper)
    if not np.any(band):
        return 0.0
    return float(np.mean(spectrogram[band, frame_idx]))


def _apply_spectral_octave_verification(
    midi_track: np.ndarray,
    freqs: np.ndarray,
    spectrogram: np.ndarray,
) -> tuple[np.ndarray, int]:
    corrected = np.array(midi_track, copy=True)
    correction_count = 0
    frame_count = min(corrected.size, spectrogram.shape[1])
    for idx in range(frame_count):
        midi_note = int(corrected[idx])
        if midi_note <= 0:
            continue
        f0 = _midi_to_hz(midi_note)
        if f0 <= 80.0:
            continue
        f0_energy = _band_energy(freqs, spectrogram, idx, f0)
        half_energy = _band_energy(freqs, spectrogram, idx, f0 / 2.0)
        if half_energy > (f0_energy * 1.2) and midi_note - 12 >= 28:
            corrected[idx] = midi_note - 12
            correction_count += 1
    return corrected, correction_count


def _frame_step_seconds(times: np.ndarray) -> float:
    if times.size <= 1:
        return 0.1
    step = float(np.median(np.diff(times)))
    return max(step, 1e-3)


def _pitch_distance_semitones(a: int, b: int) -> float:
    return float(abs(a - b))


def _resolve_pitch_near_reference(
    raw_pitch: int,
    reference_pitch: int | None,
    *,
    max_pitch: int = 64,
) -> tuple[int, int]:
    if reference_pitch is None:
        clipped = int(np.clip(raw_pitch, 28, max_pitch))
        return clipped, int(clipped != raw_pitch)

    candidates = [raw_pitch + (12 * shift) for shift in (-2, -1, 0, 1, 2)]
    candidates = [candidate for candidate in candidates if 28 <= candidate <= max_pitch]
    if not candidates:
        clipped = int(np.clip(raw_pitch, 28, max_pitch))
        return clipped, int(clipped != raw_pitch)
    best = min(candidates, key=lambda candidate: (_pitch_distance_semitones(candidate, reference_pitch), abs(candidate - raw_pitch)))
    return int(best), int(best != raw_pitch)


def _majority_pitch(window: np.ndarray) -> int | None:
    valid = [int(value) for value in window if int(value) > 0]
    if not valid:
        return None
    counts = np.bincount(np.array(valid, dtype=int))
    return int(np.argmax(counts))


def _segment_pitch_regions(
    stabilized: np.ndarray,
    voiced_prob: np.ndarray,
    times: np.ndarray,
    *,
    min_note_duration_ms: int,
    merge_gap_ms: int,
) -> tuple[list[tuple[float, float, int, float]], int]:
    if stabilized.size == 0 or times.size == 0:
        return [], 0

    step_sec = _frame_step_seconds(times)
    min_note_duration_sec = max(float(min_note_duration_ms) / 1000.0, step_sec * 0.5)
    merge_gap_frames = max(int(round((float(merge_gap_ms) / 1000.0) / step_sec)), 0)
    merged_gap_regions = 0
    working = np.array(stabilized, copy=True)

    if merge_gap_frames > 0 and working.size >= 3:
        idx = 1
        while idx < working.size - 1:
            if working[idx] > 0:
                idx += 1
                continue
            gap_start = idx
            while idx < working.size and working[idx] <= 0:
                idx += 1
            gap_end = idx
            gap_frames = gap_end - gap_start
            if gap_start == 0 or gap_end >= working.size:
                continue
            left = int(working[gap_start - 1])
            right = int(working[gap_end])
            if left <= 0 or right <= 0 or left != right or gap_frames > merge_gap_frames:
                continue
            working[gap_start:gap_end] = left
            merged_gap_regions += 1

    events: list[tuple[float, float, int, float]] = []
    idx = 0
    while idx < working.size:
        pitch = int(working[idx])
        if pitch <= 0:
            idx += 1
            continue
        start_idx = idx
        while idx < working.size and int(working[idx]) == pitch:
            idx += 1
        end_idx = idx
        start_sec = round(float(times[start_idx]), 6)
        end_sec = round(float(times[end_idx - 1] + step_sec), 6)
        if (end_sec - start_sec) < min_note_duration_sec:
            continue
        segment_conf = float(np.median(voiced_prob[start_idx:end_idx])) if end_idx > start_idx else 0.0
        events.append((start_sec, end_sec, pitch, max(0.1, min(segment_conf, 1.0))))

    return events, merged_gap_regions


def _raw_pitch_frames_to_segments(
    frame_midi: np.ndarray,
    voiced_prob: np.ndarray,
    times: np.ndarray,
    *,
    min_confidence: float,
    min_note_duration_ms: int,
) -> tuple[np.ndarray, list[tuple[float, float, int, float]]]:
    if frame_midi.size == 0:
        return np.array([], dtype=int), []
    raw = np.full(frame_midi.shape, -1, dtype=int)
    valid = np.isfinite(frame_midi) & (voiced_prob >= min_confidence)
    raw[valid] = np.clip(np.rint(frame_midi[valid]).astype(int), 28, 64)
    events, _ = _segment_pitch_regions(
        raw,
        voiced_prob,
        times,
        min_note_duration_ms=min_note_duration_ms,
        merge_gap_ms=0,
    )
    return raw, events


def stabilize_bass_pitch_track(
    *,
    frame_midi: np.ndarray,
    voiced_prob: np.ndarray,
    times: np.ndarray,
    onset_frames: np.ndarray,
    config: PitchStabilityConfig | None = None,
    freqs: np.ndarray | None = None,
    spectrogram: np.ndarray | None = None,
) -> tuple[np.ndarray, list[tuple[float, float, int, float]], dict[str, object]]:
    resolved_config = config or _get_pitch_stability_config()
    frame_midi = np.asarray(frame_midi, dtype=float)
    voiced_prob = np.asarray(voiced_prob, dtype=float)
    times = np.asarray(times, dtype=float)
    onset_frame_set = {int(frame) for frame in np.asarray(onset_frames, dtype=int).tolist() if int(frame) >= 0}

    raw_track, raw_events = _raw_pitch_frames_to_segments(
        frame_midi,
        voiced_prob,
        times,
        min_confidence=resolved_config.pitch_min_confidence,
        min_note_duration_ms=resolved_config.pitch_min_note_duration_ms,
    )
    if not resolved_config.pitch_stability_enable:
        return raw_track, raw_events, {"stabilizer_enabled": False}

    smoothed = _smooth_midi_track_viterbi(frame_midi, voiced_prob)
    working = np.array(smoothed, copy=True)
    octave_corrections = 0
    harmonic_rechecks_applied = 0
    smoothing_adjustments = int(
        np.sum(
            (raw_track > 0)
            & (working > 0)
            & (np.abs(raw_track - working) >= 12)
        )
    )
    octave_corrections += smoothing_adjustments
    if (
        resolved_config.pitch_harmonic_recheck_enable
        and freqs is not None
        and spectrogram is not None
        and working.size > 0
    ):
        spectral_corrected, spectral_corrections = _apply_spectral_octave_verification(
            working,
            np.asarray(freqs, dtype=float),
            np.asarray(spectrogram, dtype=float),
        )
        working = spectral_corrected
        harmonic_rechecks_applied = int(spectral_corrections)
        octave_corrections += int(spectral_corrections)

    step_sec = _frame_step_seconds(times)
    merge_gap_frames = max(int(round((resolved_config.pitch_merge_gap_ms / 1000.0) / step_sec)), 0)
    drift_semitones = max(resolved_config.pitch_max_cents_drift_within_note / 100.0, 0.1)
    stabilized = np.full(frame_midi.shape, -1, dtype=int)
    stable_pitch: int | None = None
    candidate_pitch: int | None = None
    candidate_frames = 0
    weak_gap_frames = 0
    active_gap_region = False
    bridged_gap_regions = 0
    octave_remaps = 0
    continuity_holds = 0

    for idx in range(frame_midi.size):
        conf = float(voiced_prob[idx]) if idx < voiced_prob.size else 0.0
        raw_pitch = int(working[idx]) if idx < working.size else -1
        if raw_pitch <= 0 or conf < resolved_config.pitch_min_confidence:
            if stable_pitch is not None and weak_gap_frames < merge_gap_frames:
                stabilized[idx] = stable_pitch
                weak_gap_frames += 1
                if not active_gap_region:
                    bridged_gap_regions += 1
                    active_gap_region = True
            else:
                stabilized[idx] = -1
            continue

        weak_gap_frames = 0
        active_gap_region = False
        adjusted_pitch = raw_pitch
        if stable_pitch is not None:
            adjusted_pitch, remapped = _resolve_pitch_near_reference(raw_pitch, stable_pitch)
            octave_remaps += remapped
            if remapped:
                octave_corrections += 1

        if stable_pitch is None:
            stable_pitch = adjusted_pitch
            stabilized[idx] = adjusted_pitch
            candidate_pitch = None
            candidate_frames = 0
            continue

        pitch_delta = _pitch_distance_semitones(adjusted_pitch, stable_pitch)
        if pitch_delta <= drift_semitones:
            stabilized[idx] = stable_pitch
            if np.isfinite(frame_midi[idx]) and abs(float(frame_midi[idx]) - float(stable_pitch)) >= 0.2:
                continuity_holds += 1
            candidate_pitch = None
            candidate_frames = 0
            continue

        if candidate_pitch == adjusted_pitch:
            candidate_frames += 1
        else:
            candidate_pitch = adjusted_pitch
            candidate_frames = 1

        hysteresis_frames = resolved_config.pitch_transition_hysteresis_frames
        if idx in onset_frame_set:
            hysteresis_frames = max(1, hysteresis_frames - 1)
        if pitch_delta >= 12.0:
            hysteresis_frames += max(1, int(round(resolved_config.pitch_octave_jump_penalty)))

        local_window_start = max(0, idx - resolved_config.pitch_smoothing_window_frames + 1)
        local_majority = _majority_pitch(stabilized[local_window_start:idx])
        if local_majority is not None and local_majority == stable_pitch and pitch_delta >= 5.0:
            hysteresis_frames += 1

        if candidate_frames >= hysteresis_frames:
            stable_pitch = adjusted_pitch
            stabilized[idx] = stable_pitch
            candidate_pitch = None
            candidate_frames = 0
        else:
            stabilized[idx] = stable_pitch

    suppressed_short_transitions = 0
    if stabilized.size >= 3:
        idx = 1
        while idx < stabilized.size - 1:
            pitch = int(stabilized[idx])
            if pitch <= 0:
                idx += 1
                continue
            start_idx = idx
            while idx < stabilized.size and int(stabilized[idx]) == pitch:
                idx += 1
            end_idx = idx
            left_pitch = int(stabilized[start_idx - 1]) if start_idx > 0 else -1
            right_pitch = int(stabilized[end_idx]) if end_idx < stabilized.size else -1
            if (
                left_pitch > 0
                and left_pitch == right_pitch
                and left_pitch != pitch
                and (end_idx - start_idx) < resolved_config.pitch_transition_hysteresis_frames
                and start_idx not in onset_frame_set
            ):
                stabilized[start_idx:end_idx] = left_pitch
                suppressed_short_transitions += 1
                if abs(pitch - left_pitch) == 12:
                    octave_corrections += 1

    events, merged_gap_regions = _segment_pitch_regions(
        stabilized,
        voiced_prob,
        times,
        min_note_duration_ms=resolved_config.pitch_min_note_duration_ms,
        merge_gap_ms=resolved_config.pitch_merge_gap_ms,
    )
    return stabilized, events, {
        "stabilizer_enabled": True,
        "octave_corrections_applied": int(octave_corrections),
        "harmonic_rechecks_applied": int(harmonic_rechecks_applied),
        "suppressed_short_transitions": int(
            suppressed_short_transitions + continuity_holds + max(0, octave_remaps - harmonic_rechecks_applied)
        ),
        "merged_gap_regions": int(merged_gap_regions + bridged_gap_regions),
    }


def _stabilize_octaves_sequence(
    events: list[tuple[float, float, int, float]],
    *,
    window_sec: float = 1.5,
) -> tuple[list[tuple[float, float, int, float]], int]:
    if len(events) < 3:
        return events, 0

    corrected = list(events)
    corrections = 0
    for idx in range(1, len(corrected) - 1):
        start, end, pitch, conf = corrected[idx]
        center = (start + end) / 2.0
        neighbor_pitches: list[int] = []
        for jdx, (n_start, n_end, n_pitch, _n_conf) in enumerate(corrected):
            if jdx == idx:
                continue
            n_center = (n_start + n_end) / 2.0
            if abs(n_center - center) <= (window_sec / 2.0):
                neighbor_pitches.append(n_pitch)
        if len(neighbor_pitches) < 2:
            continue

        prev_pitch = corrected[idx - 1][2]
        next_pitch = corrected[idx + 1][2]
        if abs(pitch - prev_pitch) <= 5 and abs(pitch - next_pitch) <= 5:
            continue

        local_median = int(round(float(np.median(np.array(neighbor_pitches, dtype=float)))))
        delta = pitch - local_median
        if abs(delta) != 12:
            continue

        target = pitch - 12 if delta > 0 else pitch + 12
        if target < 28 or target > 64:
            continue
        if abs(target - prev_pitch) > 4 or abs(target - next_pitch) > 4:
            continue

        neighbor_support = sum(1 for n_pitch in neighbor_pitches if abs(n_pitch - target) <= 4)
        if neighbor_support < 2:
            continue

        corrected[idx] = (start, end, int(target), conf)
        corrections += 1

    return corrected, corrections


def _estimate_monophonic_notes_legacy_from_audio(
    audio: np.ndarray,
    *,
    sr: int,
) -> list[tuple[float, float, int, float]]:
    if audio.size == 0:
        return []
    try:
        import librosa
    except ModuleNotFoundError:
        return []

    n_fft = 4096
    hop_length = 1024
    stft = librosa.stft(audio, n_fft=n_fft, hop_length=hop_length)
    magnitude = np.abs(stft)
    freqs = librosa.fft_frequencies(sr=sr, n_fft=n_fft)
    times = librosa.times_like(np.arange(magnitude.shape[1]), sr=sr, hop_length=hop_length)
    band = (freqs >= 35.0) & (freqs <= 350.0)
    if not np.any(band) or magnitude.shape[1] == 0:
        return []

    band_freqs = freqs[band]
    band_mag = magnitude[band, :]
    peak_idx = np.argmax(band_mag, axis=0)
    peak_freq = band_freqs[peak_idx]
    peak_power = np.max(band_mag, axis=0)
    threshold = float(np.percentile(peak_power, 55))

    events: list[tuple[float, float, int, float]] = []
    active_note: int | None = None
    active_start = 0.0
    active_conf: list[float] = []
    for idx, t in enumerate(times):
        if peak_power[idx] < threshold or peak_freq[idx] <= 0:
            note = None
            confidence = 0.0
        else:
            midi_note = int(round(69 + 12 * np.log2(float(peak_freq[idx]) / 440.0)))
            note = int(np.clip(midi_note, 28, 76))
            confidence = float(min(1.0, peak_power[idx] / max(threshold * 2.0, 1e-6)))
        if note != active_note:
            if active_note is not None:
                end = float(t)
                if end - active_start >= 0.08:
                    events.append((active_start, end, active_note, float(np.mean(active_conf) if active_conf else 0.35)))
            active_note = note
            if note is not None:
                active_start = float(t)
                active_conf = [confidence]
            else:
                active_conf = []
            continue
        if note is not None:
            active_conf.append(confidence)
    if active_note is not None and times.size > 0:
        end = float(times[-1] + float(hop_length / sr))
        if end - active_start >= 0.08:
            events.append((active_start, end, active_note, float(np.mean(active_conf) if active_conf else 0.35)))
    return events


def _estimate_monophonic_notes_from_wav(
    wav_path: Path,
) -> tuple[list[tuple[float, float, int, float]], dict[str, object]]:
    try:
        import librosa
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            f"Stem runtime dependency missing: {exc}. Run `cd backend && uv sync`."
        ) from exc

    audio, sr = librosa.load(str(wav_path), sr=22050, mono=True)
    if audio.size == 0:
        return [], {
            "fallback_octave_corrections_applied": 0,
            "fallback_spectral_octave_corrections_applied": 0,
            "fallback_sequence_octave_corrections_applied": 0,
        }
    if (audio.size / float(sr)) <= 3.5:
        legacy_events = _estimate_monophonic_notes_legacy_from_audio(audio, sr=sr)
        return legacy_events, {
            "fallback_octave_corrections_applied": 0,
            "fallback_spectral_octave_corrections_applied": 0,
            "fallback_sequence_octave_corrections_applied": 0,
            "fallback_legacy_backstop_used": int(bool(legacy_events)),
        }

    duration_sec = audio.size / float(sr)
    if duration_sec > 90.0:
        hop_length = 1024
        frame_length = 4096
    else:
        hop_length = 256
        frame_length = 2048
    f0, _voiced_flag, voiced_prob = librosa.pyin(
        audio,
        fmin=35.0,
        fmax=350.0,
        sr=sr,
        frame_length=frame_length,
        hop_length=hop_length,
        fill_na=np.nan,
    )
    if f0 is None or voiced_prob is None:
        return [], {
            "fallback_octave_corrections_applied": 0,
            "fallback_spectral_octave_corrections_applied": 0,
            "fallback_sequence_octave_corrections_applied": 0,
            "fallback_pitch_stability_enabled": int(_get_pitch_stability_config().pitch_stability_enable),
        }

    frame_midi = _hz_to_midi(np.asarray(f0, dtype=float))
    voiced_prob_arr = np.nan_to_num(np.asarray(voiced_prob, dtype=float), nan=0.0)

    stft = librosa.stft(audio, n_fft=frame_length, hop_length=hop_length)
    spectrogram = np.abs(stft)
    freqs = librosa.fft_frequencies(sr=sr, n_fft=frame_length)
    times = librosa.times_like(np.asarray(f0), sr=sr, hop_length=hop_length)
    if times.size == 0:
        return [], {
            "fallback_octave_corrections_applied": 0,
            "fallback_spectral_octave_corrections_applied": 0,
            "fallback_sequence_octave_corrections_applied": 0,
            "fallback_pitch_stability_enabled": int(_get_pitch_stability_config().pitch_stability_enable),
        }

    onset_frames = librosa.onset.onset_detect(y=audio, sr=sr, hop_length=hop_length, units="frames")
    pitch_stability_config = _get_pitch_stability_config()
    _stabilized_frames, stabilized_events, stability_diagnostics = stabilize_bass_pitch_track(
        frame_midi=frame_midi,
        voiced_prob=voiced_prob_arr,
        times=times,
        onset_frames=np.asarray(onset_frames, dtype=int),
        config=pitch_stability_config,
        freqs=freqs,
        spectrogram=spectrogram,
    )
    stabilized_events, sequence_corrections = _stabilize_octaves_sequence(stabilized_events, window_sec=1.5)
    if not stabilized_events:
        stabilized_events = _estimate_monophonic_notes_legacy_from_audio(audio, sr=sr)

    diagnostics = {
        "fallback_octave_corrections_applied": int(stability_diagnostics.get("octave_corrections_applied", 0) + sequence_corrections),
        "fallback_spectral_octave_corrections_applied": int(stability_diagnostics.get("harmonic_rechecks_applied", 0)),
        "fallback_sequence_octave_corrections_applied": int(sequence_corrections),
        "fallback_pitch_stability_enabled": int(pitch_stability_config.pitch_stability_enable),
        "fallback_pitch_short_transition_suppressions": int(stability_diagnostics.get("suppressed_short_transitions", 0)),
        "fallback_pitch_gap_merges": int(stability_diagnostics.get("merged_gap_regions", 0)),
        "fallback_legacy_backstop_used": int(not stabilized_events),
    }
    return stabilized_events, diagnostics


def _write_note_events_to_midi(events: list[tuple[float, float, int]], output_path: Path) -> None:
    midi = MidiFile(ticks_per_beat=480)
    track = MidiTrack()
    midi.tracks.append(track)
    tempo = 500000
    track.append(MetaMessage("set_tempo", tempo=tempo, time=0))

    timeline: list[tuple[float, Message]] = []
    for start, end, note in events:
        timeline.append((start, Message("note_on", note=note, velocity=80, time=0)))
        timeline.append((end, Message("note_off", note=note, velocity=0, time=0)))
    timeline.sort(key=lambda item: (item[0], 0 if item[1].type == "note_off" else 1))

    last_sec = 0.0
    for sec, msg in timeline:
        delta_sec = max(sec - last_sec, 0.0)
        delta_ticks = int(round(second2tick(delta_sec, midi.ticks_per_beat, tempo)))
        msg.time = delta_ticks
        track.append(msg)
        last_sec = sec

    track.append(MetaMessage("end_of_track", time=0))
    midi.save(str(output_path))


def _transcribe_with_frequency_fallback(input_path: Path, output_path: Path) -> None:
    _transcribe_with_frequency_fallback_detailed(input_path, output_path)


def _preprocess_bass_for_fallback_transcription(
    input_path: Path,
    output_path: Path,
    analysis_config: StemAnalysisConfig | None = None,
) -> None:
    config = analysis_config or _get_stem_analysis_config()
    filters = [
        f"highpass=f={int(round(config.analysis_highpass_hz))}",
        f"lowpass=f={int(round(config.analysis_lowpass_hz))}",
    ]
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_path),
        "-vn",
        "-ac",
        "1",
        "-ar",
        str(config.analysis_sample_rate),
        "-af",
        ",".join(filters),
        "-f",
        "wav",
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg preprocessing failed: {result.stderr.strip()}")


def _transcribe_with_frequency_fallback_detailed(input_path: Path, output_path: Path) -> dict[str, object]:
    config = _get_stem_analysis_config()
    with tempfile.TemporaryDirectory(prefix="dechord-midi-wav-") as tmp_dir:
        wav_path = Path(tmp_dir) / "bass_mono.wav"
        _preprocess_bass_for_fallback_transcription(input_path, wav_path, analysis_config=config)

        events, diagnostics = _estimate_monophonic_notes_from_wav(wav_path)
        if not events:
            raise RuntimeError("No monophonic bass notes detected for fallback transcription.")

        _write_note_events_to_midi([(start, end, pitch) for start, end, pitch, _confidence in events], output_path)
        return {
            **diagnostics,
            "fallback_preprocess_highpass_hz": config.analysis_highpass_hz,
            "fallback_preprocess_lowpass_hz": config.analysis_lowpass_hz,
            "fallback_preprocess_sample_rate": config.analysis_sample_rate,
        }


def transcribe_bass_stem_to_midi_detailed(
    input_wav: Path,
    transcribe_fn: MidiTranscribeFn | None = None,
    fallback_fn: FallbackTranscribeFn | MidiTranscribeFn | None = None,
) -> MidiTranscriptionResult:
    if not input_wav.exists():
        raise RuntimeError(f"Bass stem file missing: {input_wav}")

    runner = transcribe_fn or _transcribe_with_basic_pitch
    fallback_runner = fallback_fn or _transcribe_with_frequency_fallback_detailed
    engine_used = "basic_pitch"
    diagnostics: dict[str, object] = {"transcription_engine_used": "basic_pitch"}

    try:
        with TemporaryDirectory(prefix="dechord-midi-") as tmp_dir:
            output_path = Path(tmp_dir) / "bass.mid"
            try:
                primary_result = runner(input_wav, output_path)
                if isinstance(primary_result, dict):
                    diagnostics.update(primary_result)
            except Exception as primary_exc:
                missing_dep = isinstance(primary_exc, ModuleNotFoundError) or (
                    isinstance(primary_exc, RuntimeError)
                    and "Stem runtime dependency missing" in str(primary_exc)
                )
                if not missing_dep:
                    raise
                fallback_result = fallback_runner(input_wav, output_path)
                engine_used = "fallback_frequency"
                diagnostics["transcription_engine_used"] = engine_used
                if isinstance(fallback_result, dict):
                    diagnostics.update(fallback_result)
            midi_bytes = output_path.read_bytes()
    except Exception as exc:
        raise RuntimeError(f"Bass MIDI transcription failed: {exc}") from exc

    if not midi_bytes:
        raise RuntimeError("Bass MIDI transcription failed: generated MIDI is empty")

    return MidiTranscriptionResult(
        midi_bytes=midi_bytes,
        engine_used=engine_used,
        diagnostics=diagnostics,
    )


def transcribe_bass_stem_to_midi(
    input_wav: Path,
    transcribe_fn: MidiTranscribeFn | None = None,
    fallback_fn: MidiTranscribeFn | None = None,
) -> bytes:
    return transcribe_bass_stem_to_midi_detailed(
        input_wav,
        transcribe_fn=transcribe_fn,
        fallback_fn=fallback_fn,
    ).midi_bytes
