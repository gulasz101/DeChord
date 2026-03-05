#!/usr/bin/env python
"""Quick evaluation that avoids madmom (12GB memory usage).

Runs the pipeline stages manually with librosa-only rhythm extraction.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import librosa
import numpy as np

# Import only lightweight modules (avoid madmom via rhythm_grid)
from app.services.gp5_reference import parse_gp5_bass_track
from app.services.tab_comparator import compare_tabs
from app.services.tab_report import generate_comparison_report
from app.services.bass_transcriber import BasicPitchTranscriber, RawNoteEvent
from app.services.note_cleanup import cleanup_note_events
from app.services.quantization import quantize_note_events, QuantizedNote
from app.services.fingering import optimize_fingering_with_debug, FingeredNote
from app.services.alphatex_exporter import export_alphatex

# Inline Bar and BarGrid to avoid importing rhythm_grid (which imports madmom)
from dataclasses import dataclass

@dataclass(frozen=True)
class Bar:
    index: int
    start_sec: float
    end_sec: float
    beats_sec: list[float]

@dataclass(frozen=True)
class BarGrid:
    bars: list[Bar]


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
TEST_SONGS = REPO_ROOT / "test songs"
STEMS_DIR = REPO_ROOT / "backend" / "stems" / "test_songs"
REPORTS_DIR = REPO_ROOT / "docs" / "reports"


def extract_beats_librosa(audio_path: Path) -> list[float]:
    y, sr = librosa.load(str(audio_path), sr=None, mono=True)
    _tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    return [float(t) for t in librosa.frames_to_time(beat_frames, sr=sr)]


def build_bars(beats: list[float], *, numerator: int = 4) -> list[Bar]:
    from statistics import median
    bars = []
    if not beats:
        return bars
    default_interval = median([beats[i] - beats[i-1] for i in range(1, len(beats))]) if len(beats) > 1 else 0.5
    bar_index = 0
    for idx in range(0, len(beats), numerator):
        group = beats[idx:idx+numerator]
        if not group:
            continue
        start = group[0]
        end = beats[idx+numerator] if idx+numerator < len(beats) else group[-1] + default_interval
        bars.append(Bar(index=bar_index, start_sec=start, end_sec=end, beats_sec=group))
        bar_index += 1
    return bars


def reconcile_tempo(beats: list[float], bpm_hint: float | None) -> float:
    if len(beats) < 2:
        return bpm_hint or 120.0
    from statistics import median
    diffs = [beats[i] - beats[i-1] for i in range(1, len(beats)) if beats[i] > beats[i-1]]
    if not diffs:
        return bpm_hint or 120.0
    derived = 60.0 / median(diffs)
    if bpm_hint is None:
        return derived
    candidates = [derived * 0.5, derived, derived * 2.0]
    return min(candidates, key=lambda t: abs(t - bpm_hint))


def evaluate_song(name: str, bass_wav: Path, drums_wav: Path, gp5_path: Path, *, bpm: int, gp5_encoding: str | None = None):
    print(f"\n{'='*60}")
    print(f"Evaluating: {name}")
    print(f"{'='*60}")

    # 1. Parse reference
    ref_tab = parse_gp5_bass_track(gp5_path, encoding=gp5_encoding)
    print(f"  Reference: {len(ref_tab.notes)} notes, {len(ref_tab.bars)} bars")

    t0 = time.time()

    # 2. Extract rhythm from drums (librosa only)
    print("  Extracting rhythm...")
    beats = extract_beats_librosa(drums_wav)
    bars = build_bars(beats)
    tempo = reconcile_tempo(beats, float(bpm))
    print(f"  Rhythm: {len(beats)} beats, {len(bars)} bars, tempo={tempo:.0f}")

    # 3. Transcribe bass
    print("  Transcribing bass...")
    transcriber = BasicPitchTranscriber()
    transcription = transcriber.transcribe(bass_wav)
    print(f"  Raw notes: {len(transcription.raw_notes)}")

    # 4. Cleanup
    cleaned = cleanup_note_events(transcription.raw_notes, apply_octave_correction=True)
    print(f"  After cleanup: {len(cleaned)}")

    # 5. Quantize
    grid = BarGrid(bars=bars)
    quantized = quantize_note_events(cleaned, grid, subdivision=16)
    print(f"  After quantization: {len(quantized)}")

    # 6. Fingering
    fingered, debug = optimize_fingering_with_debug(quantized, max_fret=24)
    print(f"  After fingering: {len(fingered)}")

    t1 = time.time()
    print(f"  Pipeline took {t1-t0:.1f}s")

    # 7. Compare
    comparison = compare_tabs(ref_tab.notes, fingered)
    print(f"\n  RESULTS:")
    print(f"    F1 Score:      {comparison.f1_score:.2%}")
    print(f"    Precision:     {comparison.precision:.2%}")
    print(f"    Recall:        {comparison.recall:.2%}")
    print(f"    Pitch Acc:     {comparison.pitch_accuracy:.2%}")
    print(f"    Fingering Acc: {comparison.fingering_accuracy:.2%}")
    print(f"    Density Corr:  {comparison.note_density_correlation:.3f}")

    # 8. Write reports
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = name.replace(" ", "_").replace("-", "").lower()

    report = generate_comparison_report(ref_tab.notes, fingered, song_name=name)
    (REPORTS_DIR / f"{safe_name}_quality_report.md").write_text(report)

    (REPORTS_DIR / f"{safe_name}_quality_metrics.json").write_text(json.dumps({
        "song": name,
        "f1_score": comparison.f1_score,
        "precision": comparison.precision,
        "recall": comparison.recall,
        "pitch_accuracy": comparison.pitch_accuracy,
        "fingering_accuracy": comparison.fingering_accuracy,
        "note_density_correlation": comparison.note_density_correlation,
        "total_ref_notes": comparison.total_ref_notes,
        "total_gen_notes": comparison.total_gen_notes,
        "total_matched": comparison.total_matched,
        "pipeline_time_sec": t1 - t0,
    }, indent=2))
    print(f"  Reports written to docs/reports/")
    return comparison


if __name__ == "__main__":
    songs = [
        {
            "name": "Muse - Hysteria",
            "bass": STEMS_DIR / "Muse__Hysteria" / "bass.wav",
            "drums": STEMS_DIR / "Muse__Hysteria" / "drums.wav",
            "gp5": TEST_SONGS / "Muse - Hysteria.gp5",
            "bpm": 94,
            "gp5_encoding": None,
        },
        {
            "name": "Iron Maiden - The Trooper",
            "bass": STEMS_DIR / "Iron_Maiden__The_Trooper" / "bass.wav",
            "drums": STEMS_DIR / "Iron_Maiden__The_Trooper" / "drums.wav",
            "gp5": TEST_SONGS / "Iron Maiden - The Trooper.gp5",
            "bpm": 162,
            "gp5_encoding": "latin1",
        },
    ]

    for song in songs:
        if not song["bass"].exists():
            print(f"\nSKIP: {song['name']} - stems not cached at {song['bass']}")
            continue
        evaluate_song(
            song["name"],
            song["bass"],
            song["drums"],
            song["gp5"],
            bpm=song["bpm"],
            gp5_encoding=song["gp5_encoding"],
        )
