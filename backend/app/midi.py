from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Callable

import numpy as np
from mido import Message, MetaMessage, MidiFile, MidiTrack, second2tick

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


def _estimate_monophonic_notes_from_wav(
    wav_path: Path,
    *,
    min_note_duration: float = 0.05,
) -> list[tuple[float, float, int]]:
    import librosa

    sr = 22050
    y, sr = librosa.load(str(wav_path), sr=sr, mono=True)
    if y.size == 0:
        return []

    # --- Pitch detection with pyin (designed for monophonic sources) ---
    fmin = 40.0   # E1 ≈ 41 Hz
    fmax = 400.0  # G4 ≈ 392 Hz
    f0, voiced_flag, _voiced_probs = librosa.pyin(
        y, fmin=fmin, fmax=fmax, sr=sr, fill_na=0.0,
    )
    times = librosa.times_like(f0, sr=sr)

    if f0 is None or not np.any(voiced_flag):
        return []

    # --- Onset detection ---
    onset_frames = librosa.onset.onset_detect(y=y, sr=sr, units="frames")
    onset_times = librosa.frames_to_time(onset_frames, sr=sr)

    # If no onsets detected but we have voiced frames, treat the first voiced
    # frame as the single onset.
    if len(onset_times) == 0:
        first_voiced = np.argmax(voiced_flag)
        onset_times = np.array([times[first_voiced]])

    # --- Build note events from onset windows ---
    duration = float(len(y) / sr)
    events: list[tuple[float, float, int]] = []

    for i, onset in enumerate(onset_times):
        end_time = float(onset_times[i + 1]) if i + 1 < len(onset_times) else duration

        # Select pyin frames within this onset window
        mask = (times >= onset) & (times < end_time) & voiced_flag
        if not np.any(mask):
            continue

        pitches_hz = f0[mask]
        valid = pitches_hz > 0
        if not np.any(valid):
            continue

        # Median pitch is more robust than mean against octave errors
        median_hz = float(np.median(pitches_hz[valid]))
        midi_note = int(round(69 + 12 * np.log2(median_hz / 440.0)))
        midi_note = max(28, min(67, midi_note))

        note_start = float(onset)
        note_end = float(end_time)
        if note_end - note_start < min_note_duration:
            continue

        events.append((note_start, note_end, midi_note))

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
