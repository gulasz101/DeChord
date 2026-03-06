from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable
import math

from app.services.bass_transcriber import RawNoteEvent

AudioLoadFn = Callable[[Path | str], tuple[list[float], int]]
PitchEstimateFn = Callable[[list[float], int, float, float, int | None], tuple[int, float] | None]


@dataclass(frozen=True)
class DenseNoteCandidate:
    pitch_midi: int
    start_sec: float
    end_sec: float
    confidence: float
    source_tag: str = "dense_note_generator"
    support: dict[str, object] = field(default_factory=dict)

    def to_raw_note(self) -> RawNoteEvent:
        return RawNoteEvent(
            pitch_midi=self.pitch_midi,
            start_sec=self.start_sec,
            end_sec=self.end_sec,
            confidence=self.confidence,
        )


class DenseNoteGenerator:
    def __init__(
        self,
        *,
        audio_loader: AudioLoadFn | None = None,
        pitch_estimator: PitchEstimateFn | None = None,
        minimum_confidence: float = 0.2,
        duplicate_tolerance_sec: float = 0.07,
    ) -> None:
        self._audio_loader = audio_loader or _load_audio_mono
        self._pitch_estimator = pitch_estimator or _estimate_pitch_with_yin
        self._minimum_confidence = minimum_confidence
        self._duplicate_tolerance_sec = duplicate_tolerance_sec

    def generate(
        self,
        *,
        bass_wav: Path | str,
        window_start: float,
        window_end: float,
        onset_times: list[float],
        base_notes: list[RawNoteEvent],
        context_notes: list[RawNoteEvent],
    ) -> list[DenseNoteCandidate]:
        if window_end <= window_start:
            return []

        window_onsets = sorted(t for t in onset_times if window_start <= float(t) < window_end)
        if not window_onsets:
            return []

        repeated_note_mode, anchor_pitch, anchor_strength = _repeated_note_anchor(context_notes, onset_count=len(window_onsets))
        audio, sr = self._audio_loader(bass_wav)
        candidates: list[DenseNoteCandidate] = []
        collision_pool = list(base_notes)

        for idx, onset in enumerate(window_onsets):
            onset = float(onset)
            if _has_nearby_note(collision_pool, onset, tolerance_sec=self._duplicate_tolerance_sec):
                continue
            next_onset = window_onsets[idx + 1] if idx + 1 < len(window_onsets) else window_end
            provisional_end = min(window_end, max(onset + 0.06, min(next_onset, onset + 0.18)))
            estimate = self._pitch_estimator(audio, sr, onset, provisional_end, anchor_pitch)
            if estimate is None:
                continue
            raw_pitch, raw_confidence = estimate
            raw_pitch = int(raw_pitch)
            raw_confidence = float(raw_confidence)
            if raw_confidence < self._minimum_confidence:
                continue

            adjusted_pitch = raw_pitch
            anchor_distance = abs(raw_pitch - anchor_pitch) if anchor_pitch is not None else None
            nearest_octave_distance = (
                _nearest_octave_distance(raw_pitch, anchor_pitch) if anchor_pitch is not None else None
            )
            anchor_bonus = 0.0
            if repeated_note_mode and anchor_pitch is not None:
                if anchor_distance is not None and (anchor_distance <= 2 or (nearest_octave_distance is not None and nearest_octave_distance <= 1)):
                    adjusted_pitch = anchor_pitch
                    anchor_bonus = 0.18
                elif anchor_distance is not None and anchor_distance >= 7:
                    adjusted_pitch = anchor_pitch
                    anchor_bonus = 0.12

            if not (28 <= adjusted_pitch <= 64):
                continue

            confidence = min(
                1.0,
                max(
                    raw_confidence,
                    (0.55 * raw_confidence) + (0.25 * anchor_strength) + anchor_bonus,
                ),
            )
            candidate = DenseNoteCandidate(
                pitch_midi=int(adjusted_pitch),
                start_sec=onset,
                end_sec=float(provisional_end),
                confidence=float(confidence),
                support={
                    "raw_pitch_midi": raw_pitch,
                    "anchor_pitch": anchor_pitch,
                    "anchor_strength": float(anchor_strength),
                    "repeated_note_mode": repeated_note_mode,
                    "anchor_distance_semitones": anchor_distance,
                    "nearest_octave_distance_semitones": nearest_octave_distance,
                },
            )
            candidates.append(candidate)
            collision_pool.append(candidate.to_raw_note())

        return candidates


def _repeated_note_anchor(context_notes: list[RawNoteEvent], *, onset_count: int) -> tuple[bool, int | None, float]:
    if onset_count < 3 or not context_notes:
        return False, None, 0.0
    local_counts = Counter(int(note.pitch_midi) for note in context_notes if 28 <= int(note.pitch_midi) <= 64)
    if not local_counts:
        return False, None, 0.0
    total = sum(local_counts.values())
    anchor_pitch, anchor_count = local_counts.most_common(1)[0]
    anchor_strength = float(anchor_count) / float(max(1, total))
    repeated_note_mode = onset_count >= 3 and len(local_counts) <= 2 and anchor_strength >= 0.6
    return repeated_note_mode, int(anchor_pitch), float(anchor_strength)


def _has_nearby_note(notes: list[RawNoteEvent], onset: float, *, tolerance_sec: float) -> bool:
    for note in notes:
        if abs(float(note.start_sec) - float(onset)) <= tolerance_sec:
            return True
    return False


def _nearest_octave_distance(pitch_midi: int, anchor_pitch: int | None) -> int | None:
    if anchor_pitch is None:
        return None
    distances = [abs((pitch_midi + (12 * offset)) - anchor_pitch) for offset in (-2, -1, 0, 1, 2)]
    return int(min(distances))


def _load_audio_mono(path: Path | str) -> tuple[list[float], int]:
    try:
        import librosa  # type: ignore
    except ModuleNotFoundError:
        return [], 22050

    audio, sr = librosa.load(str(path), sr=22050, mono=True)
    return [float(sample) for sample in audio], int(sr)


def _estimate_pitch_with_yin(
    audio: list[float],
    sr: int,
    onset_sec: float,
    end_sec: float,
    anchor_pitch: int | None,
) -> tuple[int, float] | None:
    if not audio or sr <= 0 or end_sec <= onset_sec:
        return None
    start_idx = max(0, int(onset_sec * sr))
    end_idx = min(len(audio), int(end_sec * sr))
    if end_idx - start_idx < max(128, int(sr * 0.03)):
        return None

    try:
        import librosa  # type: ignore
        import numpy as np  # type: ignore
    except ModuleNotFoundError:
        return None

    segment = np.asarray(audio[start_idx:end_idx], dtype=float)
    if segment.size == 0:
        return None
    if float(np.max(np.abs(segment))) < 1e-4:
        return None

    fmin_hz = librosa.note_to_hz("E1")
    fmax_hz = librosa.note_to_hz("C5")
    if anchor_pitch is not None:
        anchor_hz = librosa.midi_to_hz(anchor_pitch)
        fmin_hz = max(fmin_hz, anchor_hz / math.sqrt(2.0))
        fmax_hz = min(fmax_hz, anchor_hz * math.sqrt(2.0))
        if fmax_hz <= fmin_hz:
            fmin_hz = librosa.note_to_hz("E1")
            fmax_hz = librosa.note_to_hz("C5")

    frame_length = min(2048, max(512, int(2 ** math.ceil(math.log2(max(256, segment.size // 2))))))
    if segment.size < frame_length:
        frame_length = max(256, int(2 ** math.floor(math.log2(segment.size))))
    if frame_length < 256:
        return None

    try:
        f0 = librosa.yin(segment, fmin=fmin_hz, fmax=fmax_hz, sr=sr, frame_length=frame_length)
    except Exception:
        return None

    voiced = [float(value) for value in f0 if value == value and value > 0.0]
    if not voiced:
        return None
    median_hz = float(np.median(voiced))
    voiced_ratio = float(len(voiced)) / float(len(f0)) if len(f0) else 0.0
    midi = int(round(librosa.hz_to_midi(median_hz)))
    if midi < 28 or midi > 64:
        return None
    confidence = max(0.0, min(1.0, voiced_ratio))
    return midi, confidence
