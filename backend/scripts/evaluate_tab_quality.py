#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.gp5_reference import ReferenceNote, ReferenceTab, parse_gp5_bass_track
from app.services.tab_comparator import compare_tabs
from app.services.tab_pipeline import TabPipeline
from app.stems import split_to_stems

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
SONG_OVERRIDES: dict[str, dict[str, float | str | None]] = {
    "muse - hysteria": {"bpm": 94.0, "gp5_encoding": None},
    "iron maiden - the trooper": {"bpm": 162.0, "gp5_encoding": "latin1"},
}


@dataclass(frozen=True)
class ResolvedInputs:
    song_name: str
    mp3_path: Path
    gp5_path: Path


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


def _octave_confusion_metrics(source: dict[str, int]) -> dict[str, int]:
    return {
        "exact": int(source.get("exact", 0)),
        "+12": int(source.get("octave_plus_12", source.get("+12", 0))),
        "-12": int(source.get("octave_minus_12", source.get("-12", 0))),
        "other": int(source.get("other", 0)),
    }


def evaluate_inputs(resolved: ResolvedInputs, *, quality: str) -> dict[str, object]:
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

    stems = split_to_stems(str(resolved.mp3_path), stem_dir)
    bass = next(Path(stem.relative_path) for stem in stems if stem.stem_key == "bass")
    drums = next(Path(stem.relative_path) for stem in stems if stem.stem_key == "drums")

    result = TabPipeline().run(
        bass,
        drums,
        bpm_hint=float(bpm_hint) if isinstance(bpm_hint, float) else None,
        tab_generation_quality_mode=quality,
    )

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

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    metrics_path = REPORTS_DIR / f"{prefix}_metrics.json"
    debug_path = REPORTS_DIR / f"{prefix}_debug.json"
    alphatex_path = REPORTS_DIR / f"{prefix}_output.alphatex"

    metrics = {
        "song": song_name,
        "quality": quality,
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
    }

    evaluation_context = {
        "resolved_mp3_path": str(resolved.mp3_path),
        "resolved_gp5_path": str(resolved.gp5_path),
        "quality_mode": quality,
        "onset_recovery_enabled": onset_recovery_enabled,
        "derived_tempo": derived_tempo,
        "grid_source": grid_source,
    }

    debug_info = {
        "song": song_name,
        "evaluation_context": evaluation_context,
        "track": {
            "mp3": str(resolved.mp3_path),
            "gp5": str(resolved.gp5_path),
            "bass_stem": str(bass),
            "drums_stem": str(drums),
        },
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

    metrics_path.write_text(json.dumps(metrics, indent=2, sort_keys=True))
    debug_path.write_text(json.dumps(debug_info, indent=2, sort_keys=True))
    alphatex_path.write_text(result.alphatex)

    return {
        "metrics_path": str(metrics_path),
        "debug_path": str(debug_path),
        "alphatex_path": str(alphatex_path),
        "metrics": metrics,
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_cli_args(argv)
    resolved = resolve_input_paths(args)
    output = evaluate_inputs(resolved, quality=args.quality)
    print(json.dumps(output["metrics"], indent=2, sort_keys=True))
    print(f"metrics: {output['metrics_path']}")
    print(f"debug: {output['debug_path']}")
    print(f"alphatex: {output['alphatex_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
