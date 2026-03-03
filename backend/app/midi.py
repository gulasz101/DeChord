from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Callable

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


def transcribe_bass_stem_to_midi(
    input_wav: Path,
    transcribe_fn: MidiTranscribeFn | None = None,
) -> bytes:
    if not input_wav.exists():
        raise RuntimeError(f"Bass stem file missing: {input_wav}")

    runner = transcribe_fn or _transcribe_with_basic_pitch

    try:
        with TemporaryDirectory(prefix="dechord-midi-") as tmp_dir:
            output_path = Path(tmp_dir) / "bass.mid"
            runner(input_wav, output_path)
            midi_bytes = output_path.read_bytes()
    except Exception as exc:
        raise RuntimeError(f"Bass MIDI transcription failed: {exc}") from exc

    if not midi_bytes:
        raise RuntimeError("Bass MIDI transcription failed: generated MIDI is empty")

    return midi_bytes
