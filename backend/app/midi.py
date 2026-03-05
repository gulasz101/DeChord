from __future__ import annotations

import subprocess
import tempfile
import wave
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Callable

import numpy as np
from mido import Message, MetaMessage, MidiFile, MidiTrack, second2tick
from scipy import signal

MidiTranscribeFn = Callable[[Path, Path], None]


def _transcribe_with_basic_pitch(input_path: Path, output_path: Path) -> None:
    try:
        from basic_pitch.inference import predict  # type: ignore
    except ModuleNotFoundError as exc:  # pragma: no cover - depends on optional runtime dep
        raise RuntimeError(
            f"Stem runtime dependency missing: {exc}. Run `cd backend && uv sync`."
        ) from exc

    _model_output, midi_data, _note_events = predict(str(input_path))
    midi_data.write(str(output_path))


def _estimate_monophonic_notes_from_wav(wav_path: Path) -> list[tuple[float, float, int]]:
    with wave.open(str(wav_path), "rb") as wav:
        channels = wav.getnchannels()
        sample_rate = wav.getframerate()
        sample_width = wav.getsampwidth()
        frames = wav.readframes(wav.getnframes())

    if sample_width != 2:
        raise RuntimeError(f"Unsupported PCM width: {sample_width}")

    audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32)
    if channels > 1:
        audio = audio.reshape(-1, channels).mean(axis=1)
    if audio.size == 0:
        return []

    audio /= max(np.max(np.abs(audio)), 1.0)

    nperseg = 4096
    noverlap = 3072
    freqs, times, zxx = signal.stft(
        audio,
        fs=sample_rate,
        window="hann",
        nperseg=nperseg,
        noverlap=noverlap,
        padded=False,
        boundary=None,
    )
    magnitude = np.abs(zxx)
    band = (freqs >= 35.0) & (freqs <= 350.0)
    if not np.any(band):
        return []

    band_freqs = freqs[band]
    band_mag = magnitude[band, :]
    peak_idx = np.argmax(band_mag, axis=0)
    peak_freq = band_freqs[peak_idx]
    peak_power = np.max(band_mag, axis=0)

    power_threshold = np.percentile(peak_power, 60)
    events: list[tuple[float, float, int]] = []
    active_note: int | None = None
    active_start = 0.0

    for idx, t in enumerate(times):
        if peak_power[idx] < power_threshold or peak_freq[idx] <= 0:
            note = None
        else:
            midi_note = int(round(69 + 12 * np.log2(peak_freq[idx] / 440.0)))
            note = max(28, min(76, midi_note))

        if note != active_note:
            if active_note is not None:
                end = float(t)
                if end - active_start >= 0.08:
                    events.append((active_start, end, active_note))
            if note is not None:
                active_start = float(t)
            active_note = note

    if active_note is not None and times.size > 0:
        end = float(times[-1] + (times[1] - times[0] if times.size > 1 else 0.1))
        if end - active_start >= 0.08:
            events.append((active_start, end, active_note))

    return events


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

        events = _estimate_monophonic_notes_from_wav(wav_path)
        if not events:
            raise RuntimeError("No monophonic bass notes detected for fallback transcription.")

        _write_note_events_to_midi(events, output_path)


def transcribe_bass_stem_to_midi(
    input_wav: Path,
    transcribe_fn: MidiTranscribeFn | None = None,
    fallback_fn: MidiTranscribeFn | None = None,
) -> bytes:
    if not input_wav.exists():
        raise RuntimeError(f"Bass stem file missing: {input_wav}")

    runner = transcribe_fn or _transcribe_with_basic_pitch
    fallback_runner = fallback_fn or _transcribe_with_frequency_fallback

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
                fallback_runner(input_wav, output_path)
            midi_bytes = output_path.read_bytes()
    except Exception as exc:
        raise RuntimeError(f"Bass MIDI transcription failed: {exc}") from exc

    if not midi_bytes:
        raise RuntimeError("Bass MIDI transcription failed: generated MIDI is empty")

    return midi_bytes
