from __future__ import annotations

import mimetypes
from importlib import import_module
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


@dataclass
class StemResult:
    stem_key: str
    relative_path: str
    mime_type: str
    duration: float | None = None


DemucsProgressCallback = Callable[[float, str], None]
DemucsSeparateFn = Callable[[str, Path, DemucsProgressCallback], dict[str, Path]]


def check_stem_runtime_ready(
    import_module: Callable[[str], object] = import_module,
) -> None:
    try:
        import_module("demucs.api")
        import_module("lameenc")
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            f"Stem runtime dependency missing: {exc}. Run `cd backend && uv sync`."
        ) from exc


def _separate_with_demucs(
    input_audio: str,
    output_dir: Path,
    progress_callback: DemucsProgressCallback,
) -> dict[str, Path]:
    check_stem_runtime_ready()
    import demucs.api

    output_dir.mkdir(parents=True, exist_ok=True)
    separator = demucs.api.Separator(model="htdemucs")

    # Demucs callback is surfaced in later tasks with richer stage composition.
    progress_callback(0.05, "Loaded model")
    _, separated = separator.separate_audio_file(input_audio)

    outputs: dict[str, Path] = {}
    for stem_key, tensor in separated.items():
        out_path = output_dir / f"{stem_key}.wav"
        separator.save_audio(tensor, str(out_path))
        outputs[stem_key] = out_path
    progress_callback(1.0, "Separated stems")
    return outputs


def split_to_stems(
    audio_path: str,
    output_dir: Path,
    on_progress: Callable[[float, str], None] | None = None,
    separate_fn: DemucsSeparateFn | None = None,
) -> list[StemResult]:
    if on_progress:
        on_progress(0.0, "Preparing stem separation...")

    def report(progress: float, message: str) -> None:
        if on_progress:
            pct = max(0.0, min(progress * 100.0, 100.0))
            on_progress(pct, message)

    runner = separate_fn or _separate_with_demucs
    try:
        separated = runner(audio_path, output_dir, report)
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            f"Stem runtime dependency missing: {exc}. Run `cd backend && uv sync`."
        ) from exc

    stems: list[StemResult] = []
    for stem_key in sorted(separated.keys()):
        stem_path = separated[stem_key]
        mime_type, _ = mimetypes.guess_type(stem_path.name)
        stems.append(
            StemResult(
                stem_key=stem_key,
                relative_path=str(stem_path),
                mime_type=mime_type or "audio/mpeg",
            )
        )

    if on_progress:
        on_progress(100.0, "Stem separation complete")

    return stems
