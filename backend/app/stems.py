from __future__ import annotations

import logging
import mimetypes
import os
import subprocess
from importlib import import_module
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import torch

logger = logging.getLogger(__name__)

# Model preference order: fine-tuned first, then standard
DEMUCS_MODEL = os.getenv("DECHORD_DEMUCS_MODEL", "htdemucs_ft")
DEMUCS_FALLBACK_MODEL = "htdemucs"


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


def _detect_device() -> str:
    """Auto-detect best available compute device."""
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        logger.info("Demucs: using MPS (Apple Silicon)")
        return "mps"
    if torch.cuda.is_available():
        logger.info("Demucs: using CUDA")
        return "cuda"
    logger.info("Demucs: using CPU")
    return "cpu"


def _get_model_params(model_name: str) -> dict:
    """Return DemucsGUI-quality separation parameters."""
    return {
        "overlap": 0.25,
        "shifts": 1,  # 1 shift improves SDR ~0.2 points
    }


def _separate_with_demucs(
    input_audio: str,
    output_dir: Path,
    progress_callback: DemucsProgressCallback,
) -> dict[str, Path]:
    logger.info("Demucs: checking runtime dependencies")
    check_stem_runtime_ready()
    logger.info("Demucs: importing demucs.api")
    import demucs.api

    output_dir.mkdir(parents=True, exist_ok=True)
    device = _detect_device()
    model_name = DEMUCS_MODEL

    logger.info("Demucs: initializing separator model=%s device=%s", model_name, device)
    try:
        separator = demucs.api.Separator(model=model_name, device=device)
    except Exception:
        logger.warning(
            "Demucs: model %s unavailable, falling back to %s",
            model_name, DEMUCS_FALLBACK_MODEL,
        )
        model_name = DEMUCS_FALLBACK_MODEL
        separator = demucs.api.Separator(model=model_name, device=device)

    params = _get_model_params(model_name)
    separator.update_parameter(
        overlap=params["overlap"],
        shifts=params["shifts"],
    )

    progress_callback(0.05, f"Loaded model {model_name} on {device}")
    logger.info("Demucs: separating audio file %s", input_audio)

    _, separated = separator.separate_audio_file(input_audio)
    progress_callback(0.9, "Saving stems...")

    outputs: dict[str, Path] = {}
    for stem_key, tensor in separated.items():
        out_path = output_dir / f"{stem_key}.wav"
        separator.save_audio(tensor, str(out_path))
        logger.info("Demucs: saved stem %s -> %s", stem_key, out_path)
        outputs[stem_key] = out_path

    progress_callback(1.0, "Separated stems")
    return outputs


def _split_with_ffmpeg_fallback(
    input_audio: str,
    output_dir: Path,
    progress_callback: DemucsProgressCallback,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    stems_and_filters = [
        ("bass", "lowpass=f=220"),
        ("drums", "highpass=f=120,lowpass=f=5000"),
        ("vocals", "highpass=f=300"),
        ("other", "anull"),
    ]

    outputs: dict[str, Path] = {}
    total = len(stems_and_filters)
    for idx, (stem_key, audio_filter) in enumerate(stems_and_filters, start=1):
        out_path = output_dir / f"{stem_key}.wav"
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            input_audio,
            "-vn",
            "-af",
            audio_filter,
            "-acodec",
            "pcm_s16le",
            str(out_path),
        ]
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as exc:
            raise RuntimeError(f"Fallback stem extraction failed for '{stem_key}': {exc}") from exc
        outputs[stem_key] = out_path
        progress_callback(idx / total, f"Fallback extracting {stem_key}...")
    progress_callback(1.0, "Fallback stem split complete")
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

    engine = os.getenv("DECHORD_STEM_ENGINE", "demucs").lower()
    fallback_on_error = os.getenv("DECHORD_STEM_FALLBACK_ON_ERROR", "0") == "1"
    logger.info("split_to_stems: engine=%s, fallback_on_error=%s", engine, fallback_on_error)

    if separate_fn is None and engine == "fallback":
        separated = _split_with_ffmpeg_fallback(audio_path, output_dir, report)
    else:
        runner = separate_fn or _separate_with_demucs
        try:
            separated = runner(audio_path, output_dir, report)
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                f"Stem runtime dependency missing: {exc}. Run `cd backend && uv sync`."
            ) from exc
        except Exception as exc:
            if separate_fn is not None:
                raise
            if fallback_on_error:
                if on_progress:
                    on_progress(2.0, f"Demucs unavailable ({exc}). Using fallback stem extraction...")
                separated = _split_with_ffmpeg_fallback(audio_path, output_dir, report)
            else:
                raise RuntimeError(f"Demucs stem separation failed: {exc}") from exc

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
