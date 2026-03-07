#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from collections import Counter
from dataclasses import dataclass, replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.bass_transcriber import BasicPitchTranscriber, RawNoteEvent
from app.services.gp5_reference import ReferenceNote, ReferenceTab, parse_gp5_bass_track
from app.services.pipeline_trace import build_pipeline_trace_report
from app.services.tab_comparator import compare_tabs
from app.services.tab_pipeline import TabPipeline
from app.stems import build_bass_analysis_stem, split_to_stems

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
STEMS_CACHE = REPO_ROOT / "backend" / "stems" / "test_songs"
REPORTS_DIR = REPO_ROOT / "docs" / "reports"

DURATION_MAP = {
    "1": 4.0,
    "2": 2.0,
    "4": 1.0,
    "8": 0.5,
    "16": 0.25,
    "1d": 6.0,
    "2d": 3.0,
    "4d": 1.5,
    "8d": 0.75,
    "16d": 0.375,
}
OPEN_MIDI_BY_STRING = {1: 43, 2: 38, 3: 33, 4: 28}
QUALITY_CHOICES = ["standard", "high_accuracy", "high_accuracy_aggressive"]
BENCHMARK_CONFIG_CHOICES = ["baseline", "refinement", "full"]
SONG_OVERRIDES: dict[str, dict[str, float | str | None]] = {
    "muse - hysteria": {"bpm": 94.0, "gp5_encoding": None},
    "iron maiden - the trooper": {"bpm": 162.0, "gp5_encoding": "latin1"},
}


@dataclass(frozen=True)
class ResolvedInputs:
    song_name: str
    mp3_path: Path
    gp5_path: Path


@dataclass(frozen=True)
class BenchmarkConfig:
    name: str
    use_analysis_stem: bool
    analysis_config: object | None


def _slug_part(value: str) -> str:
    normalized = re.sub(r"\s+", "_", value.strip().lower())
    normalized = re.sub(r"[^a-z0-9_]", "", normalized)
    normalized = re.sub(r"_+", "_", normalized)
    return normalized.strip("_")


def prefix_for_song_name(song_name: str) -> str:
    if " - " in song_name:
        artist, title = song_name.split(" - ", 1)
        artist_slug = _slug_part(artist)
        title_slug = _slug_part(title)
        return f"{artist_slug}__{title_slug}".strip("_")
    return _slug_part(song_name)


def parse_alphatex_to_reference_notes(alphatex: str) -> list[ReferenceNote]:
    body_line = ""
    for line in alphatex.strip().splitlines():
        if "|" in line:
            body_line = line
            break

    if not body_line:
        return []

    notes: list[ReferenceNote] = []
    measures = body_line.split("|")
    for bar_idx, measure in enumerate(measures):
        tokens = [token for token in measure.strip().split() if token]
        beat_cursor = 0.0
        for token in tokens:
            if token.startswith("r."):
                _, duration_token = token.split(".", 1)
                beat_cursor += DURATION_MAP.get(duration_token, 0.25)
                continue

            parts = token.split(".")
            if len(parts) < 3:
                continue
            fret_str, string_str, duration_token = parts[0], parts[1], parts[2]
            try:
                fret = int(fret_str)
                string = int(string_str)
            except ValueError:
                continue

            duration_beats = DURATION_MAP.get(duration_token, 0.25)
            open_midi = OPEN_MIDI_BY_STRING.get(string)
            if open_midi is None:
                beat_cursor += duration_beats
                continue

            notes.append(
                ReferenceNote(
                    bar_index=bar_idx,
                    beat_position=round(beat_cursor, 6),
                    duration_beats=duration_beats,
                    pitch_midi=open_midi + fret,
                    string=string,
                    fret=fret,
                )
            )
            beat_cursor += duration_beats

    return notes


def parse_cli_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate DeChord tab quality with full TabPipeline")
    parser.add_argument("--mp3")
    parser.add_argument("--gp5")
    parser.add_argument("--song-dir")
    parser.add_argument("--song")
    parser.add_argument("--quality", choices=QUALITY_CHOICES, default="high_accuracy_aggressive")
    parser.add_argument("--config", choices=BENCHMARK_CONFIG_CHOICES, default="baseline")
    parser.add_argument("--candidate-models")
    parser.add_argument("--phase")
    parser.add_argument("--trace-pipeline", action="store_true")
    args = parser.parse_args(argv)

    has_mp3 = bool(args.mp3)
    has_gp5 = bool(args.gp5)
    has_song_dir = bool(args.song_dir)
    has_song = bool(args.song)

    if has_mp3 ^ has_gp5:
        parser.error("--mp3 and --gp5 must be provided together")
    if has_song_dir ^ has_song:
        parser.error("--song-dir and --song must be provided together")
    if (has_mp3 or has_gp5) and (has_song_dir or has_song):
        parser.error("Use either --mp3/--gp5 or --song-dir/--song, not both")
    if not ((has_mp3 and has_gp5) or (has_song_dir and has_song)):
        parser.error("Provide either --mp3/--gp5 or --song-dir/--song")

    return args


def resolve_input_paths(args: argparse.Namespace) -> ResolvedInputs:
    if args.mp3 and args.gp5:
        mp3_path = Path(args.mp3).expanduser().resolve()
        gp5_path = Path(args.gp5).expanduser().resolve()
        return ResolvedInputs(song_name=Path(args.mp3).stem, mp3_path=mp3_path, gp5_path=gp5_path)

    song_dir = Path(args.song_dir).expanduser().resolve()
    song_name = args.song
    mp3_path = song_dir / f"{song_name}.mp3"
    gp5_path = song_dir / f"{song_name}.gp5"
    if not mp3_path.exists():
        raise FileNotFoundError(f"Missing song MP3: {mp3_path}")
    if not gp5_path.exists():
        raise FileNotFoundError(f"Missing song GP5: {gp5_path}")
    return ResolvedInputs(song_name=song_name, mp3_path=mp3_path, gp5_path=gp5_path)


def probe_audio_duration_seconds(path: Path) -> float:
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    proc = subprocess.run(command, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        error = proc.stderr.strip() or proc.stdout.strip() or "ffprobe failed"
        raise RuntimeError(f"Unable to probe duration for {path}: {error}")

    try:
        return float(proc.stdout.strip())
    except ValueError as exc:
        raise RuntimeError(f"Unable to parse duration for {path}: {proc.stdout!r}") from exc


def _song_override(song_name: str) -> dict[str, float | str | None]:
    return SONG_OVERRIDES.get(song_name.lower(), {})


def validate_inputs(mp3_path: Path, gp5_path: Path) -> tuple[ReferenceTab, float]:
    if not mp3_path.exists():
        raise FileNotFoundError(f"Missing MP3 file: {mp3_path}")
    if not gp5_path.exists():
        raise FileNotFoundError(f"Missing GP5 file: {gp5_path}")

    duration_seconds = probe_audio_duration_seconds(mp3_path)
    if duration_seconds < 10.0:
        raise ValueError(f"MP3 duration must be at least 10 seconds: {duration_seconds:.3f}s ({mp3_path})")

    reference = parse_gp5_bass_track(gp5_path, encoding=_song_override(gp5_path.stem).get("gp5_encoding"))
    if not reference.notes:
        raise ValueError(f"GP5 parsing returned zero notes: {gp5_path}")

    return reference, duration_seconds


def resolve_benchmark_config(
    config_name: str,
    *,
    candidate_models_override: str | None = None,
) -> BenchmarkConfig:
    from app.stems import _get_stem_analysis_config

    if config_name == "baseline":
        return BenchmarkConfig(name=config_name, use_analysis_stem=False, analysis_config=None)

    base_config = _get_stem_analysis_config()
    if config_name == "refinement":
        return BenchmarkConfig(
            name=config_name,
            use_analysis_stem=True,
            analysis_config=replace(
                base_config,
                enable_bass_refinement=True,
                enable_model_ensemble=False,
                candidate_models=[base_config.demucs_model],
            ),
        )

    candidate_models: list[str]
    if candidate_models_override:
        candidate_models = [value.strip() for value in candidate_models_override.split(",") if value.strip()]
    else:
        candidate_models = [base_config.demucs_model, base_config.demucs_fallback_model]

    deduped_candidate_models: list[str] = []
    for candidate in [base_config.demucs_model, *candidate_models]:
        if candidate not in deduped_candidate_models:
            deduped_candidate_models.append(candidate)

    return BenchmarkConfig(
        name=config_name,
        use_analysis_stem=True,
        analysis_config=replace(
            base_config,
            enable_bass_refinement=True,
            enable_model_ensemble=True,
            candidate_models=deduped_candidate_models,
        ),
    )


def _octave_confusion_metrics(source: dict[str, int]) -> dict[str, int]:
    return {
        "exact": int(source.get("exact", 0)),
        "+12": int(source.get("octave_plus_12", source.get("+12", 0))),
        "-12": int(source.get("octave_minus_12", source.get("-12", 0))),
        "other": int(source.get("other", 0)),
    }


def _duration_bucket(duration: float) -> str:
    if duration < 0.1:
        return "<0.1s"
    if duration < 0.25:
        return "0.1-0.25s"
    if duration < 0.5:
        return "0.25-0.5s"
    if duration < 1.0:
        return "0.5-1.0s"
    return ">=1.0s"


def _reference_note_times_seconds(reference: ReferenceTab) -> list[tuple[float, int]]:
    numerator, _denominator = reference.time_signature
    sec_per_beat = 60.0 / float(reference.tempo)
    results: list[tuple[float, int]] = []
    for note in reference.notes:
        onset_beats = (float(note.bar_index) * float(numerator)) + float(note.beat_position)
        onset_sec = onset_beats * sec_per_beat
        results.append((onset_sec, int(note.pitch_midi)))
    results.sort(key=lambda item: item[0])
    return results


def _count_pitch_errors(
    reference: ReferenceTab,
    raw_notes: list[RawNoteEvent],
    *,
    onset_tolerance_sec: float = 0.12,
) -> tuple[int, int]:
    ref_notes = _reference_note_times_seconds(reference)
    used_ref: set[int] = set()
    octave_errors = 0
    non_octave_errors = 0
    for note in sorted(raw_notes, key=lambda event: event.start_sec):
        best_idx: int | None = None
        best_delta = float("inf")
        for idx, (ref_sec, _ref_pitch) in enumerate(ref_notes):
            if idx in used_ref:
                continue
            delta = abs(float(note.start_sec) - ref_sec)
            if delta <= onset_tolerance_sec and delta < best_delta:
                best_delta = delta
                best_idx = idx
        if best_idx is None:
            continue
        used_ref.add(best_idx)
        _ref_sec, ref_pitch = ref_notes[best_idx]
        pitch_delta = int(note.pitch_midi) - int(ref_pitch)
        if pitch_delta == 0:
            continue
        if abs(pitch_delta) == 12:
            octave_errors += 1
        else:
            non_octave_errors += 1
    return octave_errors, non_octave_errors


def build_transcription_audit(
    reference: ReferenceTab,
    transcription,
) -> dict[str, object]:
    raw_notes = list(transcription.raw_notes)
    pitch_hist = Counter(str(int(note.pitch_midi)) for note in raw_notes)
    duration_hist = Counter(_duration_bucket(float(note.end_sec - note.start_sec)) for note in raw_notes)
    mean_conf = (
        sum(float(note.confidence) for note in raw_notes) / float(len(raw_notes))
        if raw_notes
        else 0.0
    )
    octave_error_count, non_octave_pitch_error_count = _count_pitch_errors(reference, raw_notes)
    debug_info = dict(getattr(transcription, "debug_info", {}) or {})
    return {
        "transcription_engine_used": getattr(transcription, "engine", "unknown"),
        "raw_note_count": len(raw_notes),
        "pitch_histogram": dict(sorted(pitch_hist.items())),
        "note_duration_histogram": dict(sorted(duration_hist.items())),
        "mean_pitch_confidence": mean_conf,
        "octave_error_count": octave_error_count,
        "non_octave_pitch_error_count": non_octave_pitch_error_count,
        "fallback_octave_corrections_applied": int(debug_info.get("fallback_octave_corrections_applied", 0)),
        "basicpitch_octave_corrections_applied": int(debug_info.get("basicpitch_octave_corrections_applied", 0)),
    }


def _match_source_row_to_reference(
    reference: ReferenceTab,
    row: dict[str, object],
    *,
    onset_tolerance_sec: float = 0.12,
) -> dict[str, object]:
    ref_notes = _reference_note_times_seconds(reference)
    start_sec = float(row.get("start_sec", 0.0))
    pitch_midi = int(row.get("pitch_midi", -999))
    best_idx: int | None = None
    best_delta = float("inf")
    for idx, (ref_sec, _ref_pitch) in enumerate(ref_notes):
        delta = abs(start_sec - ref_sec)
        if delta <= onset_tolerance_sec and delta < best_delta:
            best_idx = idx
            best_delta = delta
    if best_idx is None:
        return {
            "matched_reference_onset": False,
            "matched_reference_pitch": False,
            "matched_reference_onset_pitch": False,
            "reference_pitch_midi": None,
            "reference_onset_sec": None,
        }
    ref_sec, ref_pitch = ref_notes[best_idx]
    pitch_match = int(ref_pitch) == pitch_midi
    return {
        "matched_reference_onset": True,
        "matched_reference_pitch": pitch_match,
        "matched_reference_onset_pitch": pitch_match,
        "reference_pitch_midi": int(ref_pitch),
        "reference_onset_sec": float(ref_sec),
    }


def build_transcription_source_audit(
    reference: ReferenceTab,
    pipeline_debug: dict[str, object],
) -> dict[str, object]:
    raw_rows = pipeline_debug.get("raw_note_source_rows")
    source_rows = list(raw_rows) if isinstance(raw_rows, list) else []
    enriched_rows: list[dict[str, object]] = []
    for row in source_rows:
        if not isinstance(row, dict):
            continue
        enriched = dict(row)
        enriched.update(_match_source_row_to_reference(reference, enriched))
        enriched_rows.append(enriched)

    source_counts = Counter(str(row.get("source", "unknown")) for row in enriched_rows)
    accepted_dense = [row for row in enriched_rows if str(row.get("source")) in {"dense_note_generator", "hybrid_merged"}]
    accepted_with_onset_match = sum(1 for row in accepted_dense if row.get("matched_reference_onset") is True)
    accepted_with_pitch_match = sum(1 for row in accepted_dense if row.get("matched_reference_onset_pitch") is True)
    accepted_pitch_mismatches = sum(
        1 for row in accepted_dense if row.get("matched_reference_onset") is True and row.get("matched_reference_pitch") is False
    )

    fusion_rows = pipeline_debug.get("dense_note_fusion_candidates")
    dense_fusion_candidates = list(fusion_rows) if isinstance(fusion_rows, list) else []
    rejected_dense = [row for row in dense_fusion_candidates if isinstance(row, dict) and row.get("accepted") is False]
    rejection_histogram = Counter(
        str(row.get("rejection_reason")) for row in rejected_dense if isinstance(row.get("rejection_reason"), str)
    )

    return {
        "raw_note_source_rows": enriched_rows,
        "source_counts": dict(sorted((key, int(value)) for key, value in source_counts.items())),
        "accepted_dense_candidates": len(accepted_dense),
        "rejected_dense_candidates": len(rejected_dense),
        "accepted_dense_with_reference_onset_match": int(accepted_with_onset_match),
        "accepted_dense_with_reference_onset_pitch_match": int(accepted_with_pitch_match),
        "accepted_dense_with_reference_pitch_mismatch": int(accepted_pitch_mismatches),
        "rejected_dense_reasons": dict(sorted((key, int(value)) for key, value in rejection_histogram.items())),
    }


def _per_bar_difference_metrics(comparison) -> dict[str, object]:
    per_bar = getattr(comparison, "per_bar", None)
    if not per_bar:
        return {
            "average_per_bar_note_density_difference": 0.0,
            "maximum_per_bar_difference": 0,
            "per_bar_note_count_differences": [],
        }

    differences = [
        {
            "bar_index": int(bar_index),
            "reference_note_count": int(metrics.ref_count),
            "generated_note_count": int(metrics.gen_count),
            "difference": int(metrics.gen_count - metrics.ref_count),
            "absolute_difference": int(abs(metrics.gen_count - metrics.ref_count)),
        }
        for bar_index, metrics in sorted(per_bar.items())
    ]
    average_abs_difference = sum(row["absolute_difference"] for row in differences) / len(differences)
    max_abs_difference = max(row["absolute_difference"] for row in differences)
    return {
        "average_per_bar_note_density_difference": average_abs_difference,
        "maximum_per_bar_difference": max_abs_difference,
        "per_bar_note_count_differences": differences,
    }


def evaluate_inputs(
    resolved: ResolvedInputs,
    *,
    quality: str,
    config_name: str = "baseline",
    candidate_models_override: str | None = None,
    phase: str | None = None,
    trace_pipeline: bool = False,
) -> dict[str, object]:
    reference, _duration_seconds = validate_inputs(resolved.mp3_path, resolved.gp5_path)
    song_name = resolved.song_name
    prefix = prefix_for_song_name(song_name)
    stem_dir = STEMS_CACHE / prefix
    stem_dir.mkdir(parents=True, exist_ok=True)

    overrides = _song_override(song_name)
    bpm_hint = overrides.get("bpm")
    onset_recovery_enabled = quality in {"high_accuracy", "high_accuracy_aggressive"}

    print(f"Resolved MP3 path: {resolved.mp3_path}")
    print(f"Resolved GP5 path: {resolved.gp5_path}")
    print(f"Quality mode: {quality}")
    print(f"onset_recovery: {'enabled' if onset_recovery_enabled else 'disabled'}")
    print(f"Benchmark config: {config_name}")

    split_started = time.perf_counter()
    stems = split_to_stems(str(resolved.mp3_path), stem_dir)
    split_runtime = time.perf_counter() - split_started
    bass = next(Path(stem.relative_path) for stem in stems if stem.stem_key == "bass")
    drums = next(Path(stem.relative_path) for stem in stems if stem.stem_key == "drums")
    benchmark_config = resolve_benchmark_config(config_name, candidate_models_override=candidate_models_override)
    analysis_diagnostics: dict[str, object]
    analysis_stem_path = bass
    analysis_runtime = 0.0
    if benchmark_config.use_analysis_stem:
        analysis_started = time.perf_counter()
        analysis_output_dir = stem_dir / "analysis" / benchmark_config.name
        analysis_stem_result = build_bass_analysis_stem(
            stems={stem.stem_key: Path(stem.relative_path) for stem in stems},
            output_dir=analysis_output_dir,
            analysis_config=benchmark_config.analysis_config,
            source_audio_path=resolved.mp3_path,
        )
        analysis_runtime = time.perf_counter() - analysis_started
        analysis_stem_path = analysis_stem_result.path
        analysis_diagnostics = dict(analysis_stem_result.diagnostics)
    else:
        analysis_diagnostics = {
            "selected_model": "raw_bass_stem",
            "candidate_scores": {"raw_bass_stem": 0.0},
            "ensemble_requested": 0,
            "attempted_candidate_models": ["raw_bass_stem"],
            "successful_candidate_models": ["raw_bass_stem"],
            "bleed_subtraction_applied": 0,
            "guitar_assisted_cancellation_available": 0,
            "refinement_fallback_used": 0,
        }

    transcribe_started = time.perf_counter()
    transcription = BasicPitchTranscriber().transcribe(analysis_stem_path)
    transcription_runtime = time.perf_counter() - transcribe_started
    transcription_audit = build_transcription_audit(reference, transcription)

    pipeline_started = time.perf_counter()
    result = TabPipeline().run(
        analysis_stem_path,
        drums,
        bpm_hint=float(bpm_hint) if isinstance(bpm_hint, float) else None,
        tab_generation_quality_mode=quality,
    )
    pipeline_runtime = time.perf_counter() - pipeline_started

    derived_tempo = float(result.debug_info.get("derived_bpm", result.tempo_used))
    grid_source = str(result.debug_info.get("rhythm_source", "unknown"))
    print(f"derived tempo: {derived_tempo}")
    print(f"grid source: {grid_source}")

    generated = parse_alphatex_to_reference_notes(result.alphatex)
    comparison = compare_tabs(
        reference.notes,
        generated,
        beat_tolerance=0.125,
        bpm=float(result.tempo_used),
        subdivision=16,
        onset_tolerance_ms=30.0,
    )
    per_bar_metrics = _per_bar_difference_metrics(comparison)

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    filename_prefix = f"{prefix}_{_slug_part(phase)}" if phase else prefix
    metrics_path = REPORTS_DIR / f"{filename_prefix}_metrics.json"
    debug_path = REPORTS_DIR / f"{filename_prefix}_debug.json"
    transcription_audit_path = REPORTS_DIR / f"{filename_prefix}_transcription_audit.json"
    transcription_sources_path = REPORTS_DIR / f"{filename_prefix}_transcription_sources.json"
    alphatex_path = REPORTS_DIR / f"{filename_prefix}_output.alphatex"
    pipeline_trace_path = REPORTS_DIR / f"{filename_prefix}_pipeline_trace.json"

    metrics = {
        "song": song_name,
        "quality": quality,
        "benchmark_config": benchmark_config.name,
        "tempo_used": result.tempo_used,
        "precision": comparison.precision,
        "recall": comparison.recall,
        "f1_score": comparison.f1_score,
        "pitch_accuracy": comparison.pitch_accuracy,
        "fingering_accuracy": comparison.fingering_accuracy,
        "note_density_correlation": comparison.note_density_correlation,
        "mean_timing_offset": comparison.mean_timing_offset,
        "onset_precision": comparison.onset_precision_ms,
        "onset_recall": comparison.onset_recall_ms,
        "onset_f1_ms": comparison.onset_f1_ms,
        "onset_f1_grid": comparison.onset_f1_grid,
        "onset_precision_ms": comparison.onset_precision_ms,
        "onset_recall_ms": comparison.onset_recall_ms,
        "onset_precision_grid": comparison.onset_precision_grid,
        "onset_recall_grid": comparison.onset_recall_grid,
        "octave_confusion": _octave_confusion_metrics(comparison.octave_confusion),
        "total_ref_notes": comparison.total_ref_notes,
        "total_gen_notes": comparison.total_gen_notes,
        "total_matched": comparison.total_matched,
        "total_note_count_difference": int(comparison.total_gen_notes - comparison.total_ref_notes),
        "pitch_mismatches": int(comparison.total_matched - int(getattr(comparison, "total_pitch_matches", 0))),
        "onset_mismatches": int(max(comparison.total_ref_notes - comparison.total_matched, 0)),
        "octave_errors": int(
            comparison.octave_confusion.get("octave_plus_12", 0) + comparison.octave_confusion.get("octave_minus_12", 0)
        ),
        "analysis_diagnostics": analysis_diagnostics,
        "runtime_seconds": {
            "split_to_stems": round(split_runtime, 4),
            "build_analysis_stem": round(analysis_runtime, 4),
            "transcribe_analysis_stem": round(transcription_runtime, 4),
            "tab_pipeline": round(pipeline_runtime, 4),
            "total": round(split_runtime + analysis_runtime + transcription_runtime + pipeline_runtime, 4),
        },
        **per_bar_metrics,
    }

    evaluation_context = {
        "resolved_mp3_path": str(resolved.mp3_path),
        "resolved_gp5_path": str(resolved.gp5_path),
        "quality_mode": quality,
        "benchmark_config": benchmark_config.name,
        "onset_recovery_enabled": onset_recovery_enabled,
        "derived_tempo": derived_tempo,
        "grid_source": grid_source,
        "analysis_stem_path": str(analysis_stem_path),
    }

    debug_info = {
        "song": song_name,
        "evaluation_context": evaluation_context,
        "transcription_audit": transcription_audit,
        "transcription_source_audit": build_transcription_source_audit(reference, dict(result.debug_info)),
        "track": {
            "mp3": str(resolved.mp3_path),
            "gp5": str(resolved.gp5_path),
            "bass_stem": str(bass),
            "analysis_stem": str(analysis_stem_path),
            "drums_stem": str(drums),
        },
        "analysis_diagnostics": analysis_diagnostics,
        "runtime_seconds": metrics["runtime_seconds"],
        "pipeline_debug": result.debug_info,
        "reference": {
            "tempo": reference.tempo,
            "time_signature": reference.time_signature,
            "bars": len(reference.bars),
            "notes": len(reference.notes),
        },
        "generated": {
            "notes": len(generated),
        },
    }
    pipeline_trace = result.debug_info.get("pipeline_trace")
    if not isinstance(pipeline_trace, dict):
        pipeline_trace = build_pipeline_trace_report(song_name=song_name, pipeline_stats={})

    metrics_path.write_text(json.dumps(metrics, indent=2, sort_keys=True))
    debug_path.write_text(json.dumps(debug_info, indent=2, sort_keys=True))
    transcription_audit_path.write_text(json.dumps(transcription_audit, indent=2, sort_keys=True))
    transcription_sources_path.write_text(json.dumps(debug_info["transcription_source_audit"], indent=2, sort_keys=True))
    alphatex_path.write_text(result.alphatex)
    if trace_pipeline:
        pipeline_trace_path.write_text(json.dumps(pipeline_trace, indent=2, sort_keys=True))

    output = {
        "metrics_path": str(metrics_path),
        "debug_path": str(debug_path),
        "transcription_audit_path": str(transcription_audit_path),
        "transcription_sources_path": str(transcription_sources_path),
        "alphatex_path": str(alphatex_path),
        "metrics": metrics,
    }
    if trace_pipeline:
        output["pipeline_trace_path"] = str(pipeline_trace_path)
    return output


def main(argv: list[str] | None = None) -> int:
    args = parse_cli_args(argv)
    resolved = resolve_input_paths(args)
    output = evaluate_inputs(
        resolved,
        quality=args.quality,
        config_name=args.config,
        candidate_models_override=args.candidate_models,
        phase=args.phase,
        trace_pipeline=args.trace_pipeline,
    )
    print(json.dumps(output["metrics"], indent=2, sort_keys=True))
    print(f"metrics: {output['metrics_path']}")
    print(f"debug: {output['debug_path']}")
    print(f"transcription_audit: {output['transcription_audit_path']}")
    print(f"transcription_sources: {output['transcription_sources_path']}")
    print(f"alphatex: {output['alphatex_path']}")
    if "pipeline_trace_path" in output:
        print(f"pipeline_trace: {output['pipeline_trace_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
