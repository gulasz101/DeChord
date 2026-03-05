from __future__ import annotations

import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Callable

import numpy as np
from mido import Message, MetaMessage, MidiFile, MidiTrack, second2tick

MidiTranscribeFn = Callable[[Path, Path], None]
FallbackTranscribeFn = Callable[[Path, Path], dict[str, object] | None]


@dataclass(frozen=True)
class MidiTranscriptionResult:
    midi_bytes: bytes
    engine_used: str
    diagnostics: dict[str, object]


def _transcribe_with_basic_pitch(input_path: Path, output_path: Path) -> None:
    try:
        from basic_pitch.inference import predict  # type: ignore
    except ModuleNotFoundError as exc:  # pragma: no cover - depends on optional runtime dep
        raise RuntimeError(
            f"Stem runtime dependency missing: {exc}. Run `cd backend && uv sync`."
        ) from exc

    _model_output, midi_data, _note_events = predict(str(input_path))
    midi_data.write(str(output_path))


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
        }

    frame_midi = _hz_to_midi(np.asarray(f0, dtype=float))
    voiced_prob_arr = np.nan_to_num(np.asarray(voiced_prob, dtype=float), nan=0.0)
    smoothed_midi = _smooth_midi_track_viterbi(frame_midi, voiced_prob_arr)

    stft = librosa.stft(audio, n_fft=frame_length, hop_length=hop_length)
    spectrogram = np.abs(stft)
    freqs = librosa.fft_frequencies(sr=sr, n_fft=frame_length)
    spectral_midi, spectral_corrections = _apply_spectral_octave_verification(smoothed_midi, freqs, spectrogram)
    times = librosa.times_like(np.asarray(f0), sr=sr, hop_length=hop_length)
    if times.size == 0:
        return [], {
            "fallback_octave_corrections_applied": spectral_corrections,
            "fallback_spectral_octave_corrections_applied": spectral_corrections,
            "fallback_sequence_octave_corrections_applied": 0,
        }

    onset_frames = librosa.onset.onset_detect(y=audio, sr=sr, hop_length=hop_length, units="frames")
    boundaries = {0, len(spectral_midi)}
    boundaries.update(int(frame) for frame in onset_frames if 0 <= int(frame) < len(spectral_midi))
    for idx in range(1, len(spectral_midi)):
        if (spectral_midi[idx] <= 0) != (spectral_midi[idx - 1] <= 0):
            boundaries.add(idx)
    ordered_bounds = sorted(boundaries)

    raw_events: list[tuple[float, float, int, float]] = []
    for start_idx, end_idx in zip(ordered_bounds, ordered_bounds[1:]):
        if end_idx <= start_idx:
            continue
        segment = spectral_midi[start_idx:end_idx]
        voiced_mask = segment > 0
        if np.sum(voiced_mask) < 1:
            continue
        voiced_ratio = float(np.mean(voiced_mask))
        if voiced_ratio < 0.35:
            continue

        pitch = int(round(float(np.median(segment[voiced_mask]))))
        if pitch < 28 or pitch > 76:
            continue
        start_sec = float(times[start_idx])
        end_base = float(times[end_idx - 1])
        end_sec = end_base + float(hop_length / sr)
        if end_sec - start_sec < 0.08:
            continue
        seg_conf = float(np.median(voiced_prob_arr[start_idx:end_idx][voiced_mask]))
        raw_events.append((start_sec, end_sec, pitch, max(0.1, min(seg_conf, 1.0))))

    stabilized_events, sequence_corrections = _stabilize_octaves_sequence(raw_events, window_sec=1.5)
    if not stabilized_events:
        stabilized_events = _estimate_monophonic_notes_legacy_from_audio(audio, sr=sr)

    diagnostics = {
        "fallback_octave_corrections_applied": int(spectral_corrections + sequence_corrections),
        "fallback_spectral_octave_corrections_applied": int(spectral_corrections),
        "fallback_sequence_octave_corrections_applied": int(sequence_corrections),
        "fallback_legacy_backstop_used": int(not raw_events),
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


def _transcribe_with_frequency_fallback_detailed(input_path: Path, output_path: Path) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="dechord-midi-wav-") as tmp_dir:
        wav_path = Path(tmp_dir) / "bass_mono.wav"
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
            "-f",
            "wav",
            str(wav_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg preprocessing failed: {result.stderr.strip()}")

        events, diagnostics = _estimate_monophonic_notes_from_wav(wav_path)
        if not events:
            raise RuntimeError("No monophonic bass notes detected for fallback transcription.")

        _write_note_events_to_midi([(start, end, pitch) for start, end, pitch, _confidence in events], output_path)
        return diagnostics


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
                runner(input_wav, output_path)
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
