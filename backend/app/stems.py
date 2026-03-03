from __future__ import annotations

import logging
import mimetypes
import os
import subprocess
import tempfile
from importlib import import_module
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import torch
from dotenv import load_dotenv

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


@dataclass
class SeparationConfig:
    device: str
    segment: float
    overlap: float
    shifts: int
    input_gain_db: float
    output_gain_db: float
    jobs: int | None


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
        "device": "auto",
        "segment": 7.8,
        "overlap": 0.25,
        "shifts": 0,
        "input_gain_db": 0.0,
        "output_gain_db": 0.0,
    }


def _parse_float_env(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        logger.warning("Invalid float for %s=%r. Using default %s", name, raw, default)
        return default


def _parse_int_env(name: str, default: int | None) -> int | None:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        logger.warning("Invalid int for %s=%r. Using default %s", name, raw, default)
        return default


def _get_separation_config(model_name: str = DEMUCS_MODEL) -> SeparationConfig:
    load_dotenv(dotenv_path=Path.cwd() / ".env", override=False)

    defaults = _get_model_params(model_name)
    device = os.getenv("DECHORD_STEM_DEVICE", defaults["device"]).strip().lower()
    if device not in {"auto", "cpu", "mps", "cuda"}:
        logger.warning("Invalid DECHORD_STEM_DEVICE=%r. Falling back to 'auto'.", device)
        device = "auto"

    segment = _parse_float_env("DECHORD_STEM_SEGMENT", defaults["segment"])
    if segment <= 0:
        logger.warning("DECHORD_STEM_SEGMENT must be > 0. Falling back to %s", defaults["segment"])
        segment = defaults["segment"]

    overlap = _parse_float_env("DECHORD_STEM_OVERLAP", defaults["overlap"])
    if overlap < 0 or overlap >= 1:
        logger.warning(
            "DECHORD_STEM_OVERLAP must be in [0.0, 1.0). Falling back to %s",
            defaults["overlap"],
        )
        overlap = defaults["overlap"]

    shifts = _parse_int_env("DECHORD_STEM_SHIFTS", defaults["shifts"])
    if shifts is None or shifts < 0:
        logger.warning("DECHORD_STEM_SHIFTS must be >= 0. Falling back to %s", defaults["shifts"])
        shifts = defaults["shifts"]

    input_gain_db = _parse_float_env("DECHORD_STEM_INPUT_GAIN_DB", defaults["input_gain_db"])
    output_gain_db = _parse_float_env("DECHORD_STEM_OUTPUT_GAIN_DB", defaults["output_gain_db"])

    jobs = _parse_int_env("DECHORD_STEM_JOBS", None)
    if jobs is not None and jobs < 0:
        logger.warning("DECHORD_STEM_JOBS must be >= 0. Ignoring value %s", jobs)
        jobs = None

    return SeparationConfig(
        device=device,
        segment=segment,
        overlap=overlap,
        shifts=shifts,
        input_gain_db=input_gain_db,
        output_gain_db=output_gain_db,
        jobs=jobs,
    )


def _db_to_linear(gain_db: float) -> float:
    return 10 ** (gain_db / 20.0)


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
    config = _get_separation_config()
    device = _detect_device() if config.device == "auto" else config.device
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

    params = _get_separation_config(model_name)
    callback = None
    if progress_callback:
        def callback(data: dict) -> None:
            audio_length = data.get("audio_length")
            segment_offset = data.get("segment_offset")
            if audio_length and isinstance(segment_offset, int):
                stage_progress = min(max(segment_offset / max(audio_length, 1), 0.0), 1.0)
                progress_callback(stage_progress, "Separating stems...")

    separator.update_parameter(
        device=device,
        segment=params.segment,
        overlap=params.overlap,
        shifts=params.shifts,
        callback=callback,
        jobs=params.jobs if params.jobs is not None else 0,
    )

    progress_callback(0.05, f"Loaded model {model_name} on {device}")
    logger.info("Demucs: separating audio file %s", input_audio)

    separate_input = Path(input_audio)
    temp_input: tempfile.NamedTemporaryFile | None = None
    if params.input_gain_db != 0.0:
        temp_input = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        temp_path = Path(temp_input.name)
        temp_input.close()
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(separate_input),
            "-af",
            f"volume={params.input_gain_db}dB",
            str(temp_path),
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        separate_input = temp_path

    try:
        _, separated = separator.separate_audio_file(separate_input)
    finally:
        if temp_input is not None:
            try:
                Path(temp_input.name).unlink(missing_ok=True)
            except OSError:
                logger.warning("Failed to remove temporary gain-adjusted input: %s", temp_input.name)
    progress_callback(0.9, "Saving stems...")

    import numpy as np
    from scipy.io import wavfile as scipy_wav

    outputs: dict[str, Path] = {}
    output_gain = _db_to_linear(params.output_gain_db)
    for stem_key, tensor in separated.items():
        out_path = output_dir / f"{stem_key}.wav"
        # tensor shape: (channels, samples) → transpose to (samples, channels)
        audio_np = tensor.cpu().numpy().T * output_gain
        # Convert float32 to int16 for WAV compatibility
        audio_int16 = np.clip(audio_np * 32767, -32768, 32767).astype(np.int16)
        scipy_wav.write(str(out_path), separator.samplerate, audio_int16)
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
