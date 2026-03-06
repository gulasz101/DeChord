from __future__ import annotations

import logging
import mimetypes
import os
import shutil
import subprocess
import tempfile
from importlib import import_module
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import torch
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

DEFAULT_DEMUCS_MODEL = "htdemucs_ft"
DEFAULT_DEMUCS_FALLBACK_MODEL = "htdemucs"
DEFAULT_ANALYSIS_HIGHPASS_HZ = 35.0
DEFAULT_ANALYSIS_LOWPASS_HZ = 300.0
DEFAULT_ANALYSIS_SAMPLE_RATE = 22050


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


@dataclass(frozen=True)
class StemAnalysisConfig:
    demucs_model: str
    demucs_fallback_model: str
    enable_bass_refinement: bool
    analysis_highpass_hz: float
    analysis_lowpass_hz: float
    analysis_sample_rate: int
    enable_model_ensemble: bool
    candidate_models: list[str]


@dataclass(frozen=True)
class BassAnalysisStemResult:
    path: Path
    source_model: str
    diagnostics: dict[str, object]


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


def _load_stem_env() -> None:
    load_dotenv(dotenv_path=Path.cwd() / ".env", override=False)


def _parse_bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    logger.warning("Invalid bool for %s=%r. Using default %s", name, raw, default)
    return default


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


def _get_nonempty_env(name: str, default: str) -> str:
    _load_stem_env()
    raw = os.getenv(name)
    if raw is None:
        return default
    value = raw.strip()
    if value:
        return value
    logger.warning("Invalid empty value for %s. Using default %s", name, default)
    return default


def _get_demucs_model_name() -> str:
    return _get_nonempty_env("DECHORD_DEMUCS_MODEL", DEFAULT_DEMUCS_MODEL)


def _get_demucs_fallback_model_name() -> str:
    return _get_nonempty_env("DECHORD_DEMUCS_FALLBACK_MODEL", DEFAULT_DEMUCS_FALLBACK_MODEL)


def _parse_candidate_models_env(primary_model: str) -> list[str]:
    raw = os.getenv("DECHORD_STEM_ANALYSIS_CANDIDATE_MODELS")
    if raw is None:
        return [primary_model]
    candidates = [value.strip() for value in raw.split(",") if value.strip()]
    if not candidates:
        logger.warning(
            "Invalid empty value for DECHORD_STEM_ANALYSIS_CANDIDATE_MODELS. Using default %s",
            primary_model,
        )
        return [primary_model]
    deduped: list[str] = []
    for candidate in [primary_model, *candidates]:
        if candidate not in deduped:
            deduped.append(candidate)
    return deduped


def _get_stem_analysis_config() -> StemAnalysisConfig:
    _load_stem_env()
    demucs_model = _get_demucs_model_name()
    demucs_fallback_model = _get_demucs_fallback_model_name()
    analysis_highpass_hz = _parse_float_env(
        "DECHORD_STEM_ANALYSIS_HIGHPASS_HZ",
        DEFAULT_ANALYSIS_HIGHPASS_HZ,
    )
    if analysis_highpass_hz <= 0:
        logger.warning(
            "DECHORD_STEM_ANALYSIS_HIGHPASS_HZ must be > 0. Falling back to %s",
            DEFAULT_ANALYSIS_HIGHPASS_HZ,
        )
        analysis_highpass_hz = DEFAULT_ANALYSIS_HIGHPASS_HZ

    analysis_lowpass_hz = _parse_float_env(
        "DECHORD_STEM_ANALYSIS_LOWPASS_HZ",
        DEFAULT_ANALYSIS_LOWPASS_HZ,
    )
    if analysis_lowpass_hz <= analysis_highpass_hz:
        logger.warning(
            "DECHORD_STEM_ANALYSIS_LOWPASS_HZ must be > analysis highpass (%s). Falling back to %s",
            analysis_highpass_hz,
            DEFAULT_ANALYSIS_LOWPASS_HZ,
        )
        analysis_lowpass_hz = DEFAULT_ANALYSIS_LOWPASS_HZ

    analysis_sample_rate = _parse_int_env(
        "DECHORD_STEM_ANALYSIS_SAMPLE_RATE",
        DEFAULT_ANALYSIS_SAMPLE_RATE,
    )
    if analysis_sample_rate is None or analysis_sample_rate <= 0:
        logger.warning(
            "DECHORD_STEM_ANALYSIS_SAMPLE_RATE must be > 0. Falling back to %s",
            DEFAULT_ANALYSIS_SAMPLE_RATE,
        )
        analysis_sample_rate = DEFAULT_ANALYSIS_SAMPLE_RATE

    return StemAnalysisConfig(
        demucs_model=demucs_model,
        demucs_fallback_model=demucs_fallback_model,
        enable_bass_refinement=_parse_bool_env("DECHORD_STEM_ANALYSIS_ENABLE", True),
        analysis_highpass_hz=analysis_highpass_hz,
        analysis_lowpass_hz=analysis_lowpass_hz,
        analysis_sample_rate=analysis_sample_rate,
        enable_model_ensemble=_parse_bool_env("DECHORD_STEM_ANALYSIS_ENSEMBLE", False),
        candidate_models=_parse_candidate_models_env(demucs_model),
    )


def _get_separation_config(model_name: str | None = None) -> SeparationConfig:
    _load_stem_env()
    resolved_model_name = model_name or _get_demucs_model_name()

    defaults = _get_model_params(resolved_model_name)
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


def _read_wav_mono(path: Path) -> tuple[int, "np.ndarray"]:
    import numpy as np
    from scipy.io import wavfile as scipy_wav

    sample_rate, audio = scipy_wav.read(str(path))
    audio_f32 = audio.astype(np.float32)
    if np.issubdtype(audio.dtype, np.integer):
        audio_f32 /= max(float(np.iinfo(audio.dtype).max), 1.0)
    elif audio_f32.size:
        audio_f32 = np.clip(audio_f32, -1.0, 1.0)
    if audio_f32.ndim == 2:
        audio_f32 = np.mean(audio_f32, axis=1)
    return int(sample_rate), np.asarray(audio_f32, dtype=np.float32)


def _resample_audio(audio: "np.ndarray", source_rate: int, target_rate: int) -> "np.ndarray":
    if source_rate == target_rate:
        return audio
    from scipy.signal import resample_poly

    return resample_poly(audio, target_rate, source_rate).astype("float32")


def _apply_analysis_filters(
    audio: "np.ndarray",
    *,
    sample_rate: int,
    highpass_hz: float,
    lowpass_hz: float,
) -> "np.ndarray":
    from scipy.signal import butter, sosfiltfilt

    nyquist = max(sample_rate / 2.0, 1.0)
    hp = min(max(highpass_hz, 1.0), nyquist * 0.95)
    lp = min(max(lowpass_hz, hp + 1.0), nyquist * 0.99)
    highpass = butter(4, hp, btype="highpass", fs=sample_rate, output="sos")
    lowpass = butter(4, lp, btype="lowpass", fs=sample_rate, output="sos")
    filtered = sosfiltfilt(highpass, audio)
    filtered = sosfiltfilt(lowpass, filtered)
    return filtered.astype("float32")


def _maybe_subtract_bleed(target: "np.ndarray", bleed: "np.ndarray | None") -> tuple["np.ndarray", int]:
    import numpy as np

    if bleed is None or bleed.size == 0 or target.size == 0:
        return target, 0
    frame_count = min(target.size, bleed.size)
    target_view = target[:frame_count]
    bleed_view = bleed[:frame_count]
    target_rms = float(np.sqrt(np.mean(np.square(target_view))) + 1e-9)
    bleed_rms = float(np.sqrt(np.mean(np.square(bleed_view))) + 1e-9)
    if bleed_rms <= 1e-6:
        return target, 0
    subtraction_gain = min(0.35, max(0.0, bleed_rms / max(target_rms, 1e-6)) * 0.2)
    adjusted = np.array(target, copy=True)
    adjusted[:frame_count] = target_view - (bleed_view * subtraction_gain)
    return adjusted.astype("float32"), int(subtraction_gain > 0.0)


def _apply_noise_gate(audio: "np.ndarray") -> tuple["np.ndarray", int]:
    import numpy as np

    if audio.size == 0:
        return audio, 0
    rms = float(np.sqrt(np.mean(np.square(audio))) + 1e-9)
    threshold = max(rms * 0.08, 1e-4)
    gated = np.where(np.abs(audio) >= threshold, audio, 0.0).astype("float32")
    return gated, int(np.any(gated != audio))


def _score_bass_analysis_candidate(
    audio: "np.ndarray",
    *,
    sample_rate: int,
    bleed_audio: "np.ndarray | None" = None,
) -> float:
    import numpy as np

    if audio.size == 0:
        return 0.0

    spectrum = np.abs(np.fft.rfft(audio))
    freqs = np.fft.rfftfreq(audio.size, d=1.0 / sample_rate)
    bass_band = (freqs >= 35.0) & (freqs <= 320.0)
    low_band = (freqs >= 35.0) & (freqs <= 120.0)
    bleed_band = (freqs >= 120.0) & (freqs <= 320.0)
    total_energy = float(np.sum(spectrum) + 1e-9)
    bass_energy = float(np.sum(spectrum[bass_band]))
    low_energy = float(np.sum(spectrum[low_band]))
    bleed_energy = float(np.sum(spectrum[bleed_band]))
    normalized_spectrum = spectrum[bass_band]
    spectral_flatness = 1.0
    if normalized_spectrum.size and float(np.mean(normalized_spectrum)) > 0.0:
        spectral_flatness = float(
            np.exp(np.mean(np.log(np.maximum(normalized_spectrum, 1e-9))))
            / np.mean(np.maximum(normalized_spectrum, 1e-9))
        )

    bleed_penalty = 0.0
    if bleed_audio is not None and bleed_audio.size:
        frame_count = min(audio.size, bleed_audio.size)
        if frame_count > 8:
            corr = float(
                np.corrcoef(
                    audio[:frame_count],
                    bleed_audio[:frame_count],
                )[0, 1]
            )
            if np.isfinite(corr):
                bleed_penalty = max(corr, 0.0)

    score = (
        (bass_energy / total_energy) * 3.0
        + (low_energy / max(bass_energy, 1e-9)) * 1.5
        - (bleed_energy / total_energy) * 1.5
        - spectral_flatness * 1.25
        - bleed_penalty
    )
    return float(score)


def _select_best_candidate_model(candidate_scores: dict[str, float]) -> str:
    if not candidate_scores:
        return DEFAULT_DEMUCS_MODEL
    return max(candidate_scores.items(), key=lambda item: (item[1], item[0]))[0]


def _write_wav_mono(path: Path, *, sample_rate: int, audio: "np.ndarray") -> None:
    import numpy as np
    from scipy.io import wavfile as scipy_wav

    clipped = np.clip(audio, -1.0, 1.0)
    pcm = (clipped * 32767.0).astype(np.int16)
    scipy_wav.write(str(path), sample_rate, pcm)


def build_bass_analysis_stem(
    *,
    stems: dict[str, Path],
    output_dir: Path,
    analysis_config: StemAnalysisConfig | None = None,
) -> BassAnalysisStemResult:
    config = analysis_config or _get_stem_analysis_config()
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "bass_analysis.wav"
    bass_path = stems.get("bass")
    if bass_path is None:
        raise RuntimeError("Bass stem missing; cannot build analysis stem.")

    if not config.enable_bass_refinement:
        bass_rate, bass_audio = _read_wav_mono(bass_path)
        bass_audio = _resample_audio(bass_audio, bass_rate, config.analysis_sample_rate)
        candidate_score = _score_bass_analysis_candidate(
            bass_audio,
            sample_rate=config.analysis_sample_rate,
        )
        candidate_scores = {config.demucs_model: candidate_score}
        selected_model = _select_best_candidate_model(candidate_scores)
        shutil.copyfile(bass_path, output_path)
        diagnostics = {
            "selected_model": selected_model,
            "analysis_highpass_hz": config.analysis_highpass_hz,
            "analysis_lowpass_hz": config.analysis_lowpass_hz,
            "analysis_sample_rate": config.analysis_sample_rate,
            "bleed_subtraction_applied": 0,
            "noise_gate_applied": 0,
            "ensemble_requested": int(config.enable_model_ensemble),
            "unavailable_candidate_models": [
                candidate for candidate in config.candidate_models if candidate not in candidate_scores
            ],
            "candidate_scores": candidate_scores,
        }
        return BassAnalysisStemResult(
            path=output_path,
            source_model=selected_model,
            diagnostics=diagnostics,
        )

    bass_rate, bass_audio = _read_wav_mono(bass_path)
    bass_audio = _resample_audio(bass_audio, bass_rate, config.analysis_sample_rate)
    refined = _apply_analysis_filters(
        bass_audio,
        sample_rate=config.analysis_sample_rate,
        highpass_hz=config.analysis_highpass_hz,
        lowpass_hz=config.analysis_lowpass_hz,
    )

    bleed_audio = None
    other_path = stems.get("other")
    if other_path is not None and other_path.exists():
        other_rate, other_audio = _read_wav_mono(other_path)
        other_audio = _resample_audio(other_audio, other_rate, config.analysis_sample_rate)
        bleed_audio = _apply_analysis_filters(
            other_audio,
            sample_rate=config.analysis_sample_rate,
            highpass_hz=config.analysis_highpass_hz,
            lowpass_hz=config.analysis_lowpass_hz,
        )
    refined, bleed_applied = _maybe_subtract_bleed(refined, bleed_audio)
    refined, gate_applied = _apply_noise_gate(refined)
    _write_wav_mono(output_path, sample_rate=config.analysis_sample_rate, audio=refined)

    import numpy as np

    candidate_score = _score_bass_analysis_candidate(
        refined,
        sample_rate=config.analysis_sample_rate,
        bleed_audio=bleed_audio,
    )
    candidate_scores = {config.demucs_model: candidate_score}
    selected_model = _select_best_candidate_model(candidate_scores)

    diagnostics = {
        "selected_model": selected_model,
        "analysis_highpass_hz": config.analysis_highpass_hz,
        "analysis_lowpass_hz": config.analysis_lowpass_hz,
        "analysis_sample_rate": config.analysis_sample_rate,
        "bleed_subtraction_applied": bleed_applied,
        "noise_gate_applied": gate_applied,
        "analysis_rms": float(np.sqrt(np.mean(np.square(refined))) if refined.size else 0.0),
        "ensemble_requested": int(config.enable_model_ensemble),
        "unavailable_candidate_models": [
            candidate for candidate in config.candidate_models if candidate not in candidate_scores
        ],
        "candidate_scores": candidate_scores,
    }
    return BassAnalysisStemResult(
        path=output_path,
        source_model=selected_model,
        diagnostics=diagnostics,
    )


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
    model_name = _get_demucs_model_name()
    fallback_model_name = _get_demucs_fallback_model_name()

    logger.info(
        "Demucs: initializing separator model=%s fallback_model=%s device=%s config=%s",
        model_name,
        fallback_model_name,
        device,
        config,
    )
    try:
        separator = demucs.api.Separator(model=model_name, device=device)
    except Exception:
        logger.warning(
            "Demucs: model %s unavailable, falling back to %s",
            model_name,
            fallback_model_name,
        )
        model_name = fallback_model_name
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
