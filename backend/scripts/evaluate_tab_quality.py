#!/usr/bin/env python
"""
End-to-end tab quality evaluation.

Usage:
    cd backend && uv run python scripts/evaluate_tab_quality.py

Runs Demucs stem separation (cached), full TabPipeline, and compares
against GP5 reference tabs. Writes quality reports to docs/reports/.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

# Ensure backend is on the path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.fingering import STANDARD_BASS_TUNING_MIDI, FingeredNote
from app.services.gp5_reference import parse_gp5_bass_track
from app.services.tab_comparator import compare_tabs
from app.services.tab_report import generate_comparison_report

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
TEST_SONGS = REPO_ROOT / "test songs"
STEMS_CACHE = REPO_ROOT / "backend" / "stems" / "test_songs"
REPORTS_DIR = REPO_ROOT / "docs" / "reports"

SONGS = [
    {
        "name": "Muse - Hysteria",
        "mp3": TEST_SONGS / "Muse - Hysteria.mp3",
        "gp5": TEST_SONGS / "Muse - Hysteria.gp5",
        "gp5_encoding": None,
        "bpm": 94,
    },
    {
        "name": "Iron Maiden - The Trooper",
        "mp3": TEST_SONGS / "Iron Maiden - The Trooper.mp3",
        "gp5": TEST_SONGS / "Iron Maiden - The Trooper.gp5",
        "gp5_encoding": "latin1",
        "bpm": 162,
    },
]


def separate_stems(mp3_path: Path, output_dir: Path) -> tuple[Path, Path]:
    """Run Demucs stem separation, caching results."""
    bass_wav = output_dir / "bass.wav"
    drums_wav = output_dir / "drums.wav"
    if bass_wav.exists() and drums_wav.exists():
        print(f"  Using cached stems: {output_dir}")
        return bass_wav, drums_wav

    output_dir.mkdir(parents=True, exist_ok=True)
    stem_name = mp3_path.stem

    # Separate bass
    print(f"  Running Demucs (bass) on {mp3_path.name}...")
    demucs_bass_out = output_dir / "demucs_bass"
    cmd_bass = [
        sys.executable, "-m", "demucs",
        "--two-stems", "bass",
        "-o", str(demucs_bass_out),
        str(mp3_path),
    ]
    result = subprocess.run(cmd_bass, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Demucs bass failed: {result.stderr[:500]}")

    # Find bass output
    src_bass = _find_demucs_output(demucs_bass_out, stem_name, "bass.wav")
    if src_bass is None:
        raise RuntimeError(f"bass.wav not found in demucs output")
    shutil.copy2(src_bass, bass_wav)

    # Separate drums
    print(f"  Running Demucs (drums) on {mp3_path.name}...")
    demucs_drums_out = output_dir / "demucs_drums"
    cmd_drums = [
        sys.executable, "-m", "demucs",
        "--two-stems", "drums",
        "-o", str(demucs_drums_out),
        str(mp3_path),
    ]
    result_drums = subprocess.run(cmd_drums, capture_output=True, text=True)
    if result_drums.returncode != 0:
        print(f"  WARNING: Demucs drums failed, creating silent fallback")
        _create_silent_wav(drums_wav)
    else:
        src_drums = _find_demucs_output(demucs_drums_out, stem_name, "drums.wav")
        if src_drums is None:
            print(f"  WARNING: drums.wav not found, creating silent fallback")
            _create_silent_wav(drums_wav)
        else:
            shutil.copy2(src_drums, drums_wav)

    return bass_wav, drums_wav


def _find_demucs_output(demucs_dir: Path, stem_name: str, target: str) -> Path | None:
    """Find a specific stem file in demucs output (handles different model names)."""
    for model_dir in demucs_dir.iterdir():
        if not model_dir.is_dir():
            continue
        candidate = model_dir / stem_name / target
        if candidate.exists():
            return candidate
    return None


def _create_silent_wav(path: Path) -> None:
    """Create a short silent WAV file as fallback."""
    import wave

    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(44100)
        w.writeframes(b"\x00" * 44100 * 2)


def run_pipeline(bass_wav: Path, drums_wav: Path, *, bpm: int) -> object:
    """Run the TabPipeline and return the result."""
    from app.services.tab_pipeline import TabPipeline

    pipeline = TabPipeline()
    return pipeline.run(
        bass_wav,
        drums_wav,
        bpm_hint=float(bpm),
        tab_generation_quality_mode="high_accuracy_aggressive",
    )


def parse_alphatex_to_fingered_notes(alphatex: str) -> list[FingeredNote]:
    """Parse alphatex back into FingeredNote objects for comparison."""
    dur_map = {"1": 4.0, "2": 2.0, "4": 1.0, "8": 0.5, "16": 0.25,
               "1d": 6.0, "2d": 3.0, "4d": 1.5, "8d": 0.75, "16d": 0.375}

    # Find the body line (measures separated by |)
    body_line = ""
    for line in alphatex.strip().split("\n"):
        if "|" in line:
            body_line = line
            break

    if not body_line:
        return []

    measures = body_line.split("|")
    notes: list[FingeredNote] = []

    for bar_idx, measure in enumerate(measures):
        measure = measure.strip()
        if not measure or measure.startswith("r"):
            continue
        tokens = measure.split()
        beat_pos = 0.0
        for token in tokens:
            if token.startswith("r"):
                parts = token.split(".")
                if len(parts) >= 2:
                    dur = dur_map.get(parts[1], 0.25)
                    beat_pos += dur
                continue
            parts = token.split(".")
            if len(parts) >= 3:
                try:
                    fret = int(parts[0])
                    string = int(parts[1])
                    dur = dur_map.get(parts[2], 0.25)
                except ValueError:
                    continue
                open_midi = STANDARD_BASS_TUNING_MIDI.get(string, 0)
                pitch_midi = open_midi + fret
                notes.append(FingeredNote(
                    bar_index=bar_idx,
                    beat_position=round(beat_pos, 6),
                    duration_beats=dur,
                    pitch_midi=pitch_midi,
                    start_sec=0.0,
                    end_sec=0.0,
                    string=string,
                    fret=fret,
                ))
                beat_pos += dur

    return notes


def main() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    STEMS_CACHE.mkdir(parents=True, exist_ok=True)

    for song in SONGS:
        name = song["name"]
        print(f"\n{'='*60}")
        print(f"Evaluating: {name}")
        print(f"{'='*60}")

        if not song["mp3"].exists():
            print(f"  SKIP: MP3 not found at {song['mp3']}")
            continue
        if not song["gp5"].exists():
            print(f"  SKIP: GP5 not found at {song['gp5']}")
            continue

        # 1. Parse reference
        print("  Parsing GP5 reference...")
        ref_tab = parse_gp5_bass_track(
            song["gp5"],
            encoding=song["gp5_encoding"],
        )
        print(f"  Reference: {len(ref_tab.notes)} notes, {len(ref_tab.bars)} bars, tempo={ref_tab.tempo}")

        # 2. Separate stems
        stem_dir = STEMS_CACHE / name.replace(" ", "_").replace("-", "")
        try:
            bass_wav, drums_wav = separate_stems(song["mp3"], stem_dir)
        except Exception as e:
            print(f"  FAIL: Stem separation failed: {e}")
            continue

        # 3. Run pipeline
        print("  Running TabPipeline...")
        try:
            result = run_pipeline(bass_wav, drums_wav, bpm=song["bpm"])
        except Exception as e:
            print(f"  FAIL: Pipeline failed: {e}")
            import traceback
            traceback.print_exc()
            continue

        print(f"  Pipeline: tempo={result.tempo_used}, bars={len(result.bars)}")
        stage_keys = ["raw_note_count", "cleaned_note_count", "quantized_note_count", "fingered_note_count"]
        stage_info = {k: v for k, v in result.debug_info.items() if k in stage_keys}
        print(f"  Debug: {json.dumps(stage_info, indent=2)}")

        # 4. Get generated notes (prefer direct if available, else parse alphatex)
        if hasattr(result, "fingered_notes") and result.fingered_notes:
            gen_notes = result.fingered_notes
            print(f"  Generated: {len(gen_notes)} notes (direct from pipeline)")
        else:
            gen_notes = parse_alphatex_to_fingered_notes(result.alphatex)
            print(f"  Generated: {len(gen_notes)} notes (parsed from alphatex)")

        # 5. Compare
        print("  Comparing...")
        report = generate_comparison_report(
            ref_tab.notes,
            gen_notes,
            song_name=name,
        )

        # 6. Write reports
        safe_name = name.replace(" ", "_").replace("-", "").lower()
        report_path = REPORTS_DIR / f"{safe_name}_quality_report.md"
        report_path.write_text(report)
        print(f"  Report written to: {report_path}")

        comparison = compare_tabs(ref_tab.notes, gen_notes)
        json_path = REPORTS_DIR / f"{safe_name}_quality_metrics.json"
        json_path.write_text(json.dumps({
            "song": name,
            "precision": comparison.precision,
            "recall": comparison.recall,
            "f1_score": comparison.f1_score,
            "pitch_accuracy": comparison.pitch_accuracy,
            "fingering_accuracy": comparison.fingering_accuracy,
            "note_density_correlation": comparison.note_density_correlation,
            "mean_timing_offset": comparison.mean_timing_offset,
            "total_ref_notes": comparison.total_ref_notes,
            "total_gen_notes": comparison.total_gen_notes,
            "total_matched": comparison.total_matched,
        }, indent=2))
        print(f"  Metrics JSON: {json_path}")

        # Print summary
        print(f"\n  RESULTS:")
        print(f"    F1 Score:      {comparison.f1_score:.2%}")
        print(f"    Precision:     {comparison.precision:.2%}")
        print(f"    Recall:        {comparison.recall:.2%}")
        print(f"    Pitch Acc:     {comparison.pitch_accuracy:.2%}")
        print(f"    Fingering Acc: {comparison.fingering_accuracy:.2%}")
        print(f"    Density Corr:  {comparison.note_density_correlation:.3f}")


if __name__ == "__main__":
    main()
