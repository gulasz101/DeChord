#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.gp5_reference import ReferenceNote, parse_gp5_bass_track
from app.services.tab_comparator import compare_tabs
from app.services.tab_pipeline import TabPipeline
from app.stems import split_to_stems

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
TEST_SONGS = REPO_ROOT / "test songs"
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

SONGS = {
    "hysteria": {
        "name": "Muse - Hysteria",
        "mp3": TEST_SONGS / "Muse - Hysteria.mp3",
        "gp5": TEST_SONGS / "Muse - Hysteria.gp5",
        "gp5_encoding": None,
        "bpm": 94.0,
    },
    "trooper": {
        "name": "Iron Maiden - The Trooper",
        "mp3": TEST_SONGS / "Iron Maiden - The Trooper.mp3",
        "gp5": TEST_SONGS / "Iron Maiden - The Trooper.gp5",
        "gp5_encoding": "latin1",
        "bpm": 162.0,
    },
}


def _safe_name(name: str) -> str:
    return name.lower().replace(" ", "_").replace("-", "")


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


@dataclass(frozen=True)
class ResolvedInputs:
    song_name: str
    mp3_path: Path
    gp5_path: Path


def evaluate_song(song_key: str, *, quality: str, phase: str) -> dict[str, object]:
    spec = SONGS[song_key]
    song_name = spec["name"]
    safe_name = _safe_name(song_name)

    if not spec["mp3"].exists():
        raise FileNotFoundError(f"Missing song MP3: {spec['mp3']}")
    if not spec["gp5"].exists():
        raise FileNotFoundError(f"Missing song GP5: {spec['gp5']}")

    reference = parse_gp5_bass_track(spec["gp5"], encoding=spec["gp5_encoding"])

    stem_dir = STEMS_CACHE / safe_name
    stem_dir.mkdir(parents=True, exist_ok=True)
    stems = split_to_stems(str(spec["mp3"]), stem_dir)
    bass = next(Path(stem.relative_path) for stem in stems if stem.stem_key == "bass")
    drums = next(Path(stem.relative_path) for stem in stems if stem.stem_key == "drums")

    result = TabPipeline().run(
        bass,
        drums,
        bpm_hint=float(spec["bpm"]),
        tab_generation_quality_mode=quality,
    )

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
    suffix = f"{safe_name}_after_{phase}"
    metrics_path = REPORTS_DIR / f"{suffix}_metrics.json"
    debug_path = REPORTS_DIR / f"{suffix}_debug.json"
    alphatex_path = REPORTS_DIR / f"{suffix}.alphatex"

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
        "onset_precision_ms": comparison.onset_precision_ms,
        "onset_recall_ms": comparison.onset_recall_ms,
        "onset_f1_ms": comparison.onset_f1_ms,
        "onset_precision_grid": comparison.onset_precision_grid,
        "onset_recall_grid": comparison.onset_recall_grid,
        "onset_f1_grid": comparison.onset_f1_grid,
        "octave_confusion": comparison.octave_confusion,
        "total_ref_notes": comparison.total_ref_notes,
        "total_gen_notes": comparison.total_gen_notes,
        "total_matched": comparison.total_matched,
    }

    debug_info = {
        "song": song_name,
        "quality": quality,
        "track": {
            "mp3": str(spec["mp3"]),
            "gp5": str(spec["gp5"]),
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


def main() -> int:
    args = parse_cli_args()

    output = evaluate_song(args.song, quality=args.quality, phase="deterministic")
    print(json.dumps(output["metrics"], indent=2, sort_keys=True))
    print(f"metrics: {output['metrics_path']}")
    print(f"debug: {output['debug_path']}")
    print(f"alphatex: {output['alphatex_path']}")
    return 0


def parse_cli_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate DeChord tab quality with full TabPipeline")
    parser.add_argument("--song")
    parser.add_argument("--song-dir")
    parser.add_argument("--mp3")
    parser.add_argument("--gp5")
    parser.add_argument("--quality", choices=["standard", "high_accuracy", "high_accuracy_aggressive"], default="high_accuracy_aggressive")
    args = parser.parse_args(argv)

    has_mp3 = bool(args.mp3)
    has_gp5 = bool(args.gp5)
    if has_mp3 ^ has_gp5:
        parser.error("--mp3 and --gp5 must be provided together")
    has_song = bool(args.song)
    has_song_dir = bool(args.song_dir)
    if has_song ^ has_song_dir:
        parser.error("--song-dir and --song must be provided together")
    if (has_mp3 or has_gp5) and (has_song or has_song_dir):
        parser.error("Use either --mp3/--gp5 or --song-dir/--song, not both")
    if not ((has_mp3 and has_gp5) or (has_song and has_song_dir)):
        parser.error("Provide either --mp3/--gp5 or --song-dir/--song")

    return args


def resolve_input_paths(args: argparse.Namespace) -> ResolvedInputs:
    if args.mp3 and args.gp5:
        mp3_path = Path(args.mp3).expanduser().resolve()
        gp5_path = Path(args.gp5).expanduser().resolve()
        song_name = Path(args.mp3).stem
        return ResolvedInputs(song_name=song_name, mp3_path=mp3_path, gp5_path=gp5_path)

    song_dir = Path(args.song_dir).expanduser().resolve()
    song_name = args.song
    mp3_path = song_dir / f"{song_name}.mp3"
    gp5_path = song_dir / f"{song_name}.gp5"
    if not mp3_path.exists():
        raise FileNotFoundError(f"Missing song MP3: {mp3_path}")
    if not gp5_path.exists():
        raise FileNotFoundError(f"Missing song GP5: {gp5_path}")
    return ResolvedInputs(song_name=song_name, mp3_path=mp3_path, gp5_path=gp5_path)


if __name__ == "__main__":
    raise SystemExit(main())
