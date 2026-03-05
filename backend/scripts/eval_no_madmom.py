#!/usr/bin/env python
"""Evaluate tab quality without TabPipeline/madmom imports."""
from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from statistics import median

# Allow running as a script: `cd backend && uv run python scripts/eval_no_madmom.py`
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import librosa

from app.midi import _estimate_monophonic_notes_from_wav
from app.services.bass_transcriber import RawNoteEvent
from app.services.fingering import FingeredNote, optimize_fingering_with_debug
from app.services.gp5_reference import parse_gp5_bass_track
from app.services.note_cleanup import cleanup_note_events, cleanup_params_for_bpm
from app.services.onset_recovery import recover_missing_onsets
from app.services.quantization import QuantizedNote, quantize_note_events
from app.services.tab_comparator import ComparisonResult, compare_tabs
from app.services.tab_report import generate_comparison_report


@dataclass(frozen=True)
class Bar:
    index: int
    start_sec: float
    end_sec: float
    beats_sec: list[float]


@dataclass(frozen=True)
class BarGrid:
    bars: list[Bar]


def extract_beats_librosa(audio_path: Path) -> list[float]:
    # Downsample for beat tracking to keep memory bounded during evaluation.
    y, sr = librosa.load(str(audio_path), sr=22050, mono=True)
    _tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    return [float(t) for t in librosa.frames_to_time(beat_frames, sr=sr)]


def detect_onsets_librosa(audio_path: Path) -> list[float]:
    y, sr = librosa.load(str(audio_path), sr=22050, mono=True)
    if y.size == 0:
        return []
    onset_frames = librosa.onset.onset_detect(y=y, sr=sr, units="frames")
    return [float(t) for t in librosa.frames_to_time(onset_frames, sr=sr)]


def build_bars(beats: list[float], *, numerator: int = 4) -> list[Bar]:
    if not beats:
        return []

    default_interval = median([beats[idx] - beats[idx - 1] for idx in range(1, len(beats))]) if len(beats) > 1 else 0.5
    bars: list[Bar] = []

    for idx in range(0, len(beats), max(numerator, 1)):
        group = beats[idx : idx + numerator]
        if not group:
            continue
        start = group[0]
        if idx + numerator < len(beats):
            end = beats[idx + numerator]
        else:
            end = group[-1] + default_interval
        bars.append(Bar(index=len(bars), start_sec=start, end_sec=end, beats_sec=group))

    return bars


def extend_bars_to_cover_duration(
    bars: list[Bar],
    *,
    target_end_sec: float,
    beats_per_bar: int = 4,
) -> list[Bar]:
    if not bars:
        return []
    if bars[-1].end_sec >= target_end_sec:
        return bars

    extended = list(bars)
    default_bar_duration = median([bar.end_sec - bar.start_sec for bar in bars if bar.end_sec > bar.start_sec]) if len(bars) > 1 else 2.0

    while extended[-1].end_sec < target_end_sec:
        previous = extended[-1]
        bar_duration = max(previous.end_sec - previous.start_sec, default_bar_duration, 1e-3)
        beat_step = bar_duration / max(beats_per_bar, 1)
        start = previous.end_sec
        end = start + bar_duration
        beats = [start + (idx * beat_step) for idx in range(beats_per_bar)]
        extended.append(Bar(index=len(extended), start_sec=start, end_sec=end, beats_sec=beats))

    return extended


def reconcile_tempo(beats: list[float], bpm_hint: float | None) -> float:
    if len(beats) < 2:
        return float(bpm_hint or 120.0)

    diffs = [beats[idx] - beats[idx - 1] for idx in range(1, len(beats)) if beats[idx] > beats[idx - 1]]
    if not diffs:
        return float(bpm_hint or 120.0)

    derived = 60.0 / median(diffs)
    if bpm_hint is None:
        return float(derived)

    candidates = [derived * 0.5, derived, derived * 2.0]
    return float(min(candidates, key=lambda tempo: abs(tempo - bpm_hint)))


def events_to_raw_notes(events: list[tuple[float, float, int]]) -> list[RawNoteEvent]:
    return [
        RawNoteEvent(
            pitch_midi=int(midi_note),
            start_sec=float(start),
            end_sec=float(end),
            confidence=1.0,
        )
        for start, end, midi_note in events
    ]


def _safe_name(song_name: str) -> str:
    return song_name.lower().replace(" ", "_").replace("-", "")


def evaluate_song(
    *,
    song_name: str,
    bass_wav: Path,
    drums_wav: Path,
    gp5_path: Path,
    reports_dir: Path,
    bpm_hint: float,
    gp5_encoding: str | None = None,
) -> tuple[ComparisonResult, list[FingeredNote], dict[str, float]]:
    if not bass_wav.exists():
        raise FileNotFoundError(f"Bass stem missing: {bass_wav}")
    if not drums_wav.exists():
        raise FileNotFoundError(f"Drums stem missing: {drums_wav}")

    reference = parse_gp5_bass_track(gp5_path, encoding=gp5_encoding)

    t0 = time.perf_counter()

    print("  transcribing bass via librosa.pyin...")
    note_events = _estimate_monophonic_notes_from_wav(bass_wav)
    raw_notes = events_to_raw_notes(note_events)
    print(f"    raw_notes={len(raw_notes)}")
    onset_times = detect_onsets_librosa(bass_wav)
    recovered_notes = recover_missing_onsets(raw_notes, onset_times)
    print(f"    onset_recovery: onsets={len(onset_times)} recovered_notes={len(recovered_notes)}")

    print("  extracting beats via librosa.beat_track...")
    beats = extract_beats_librosa(drums_wav)
    bars = build_bars(beats, numerator=reference.time_signature[0])
    max_note_end = max((note.end_sec for note in raw_notes), default=0.0)
    bars = extend_bars_to_cover_duration(
        bars,
        target_end_sec=max_note_end + 0.01,
        beats_per_bar=reference.time_signature[0],
    )
    grid = BarGrid(bars=bars)
    print(f"    beats={len(beats)} bars={len(bars)}")

    print("  running cleanup -> quantize -> fingering...")
    tempo_used = reconcile_tempo(beats, bpm_hint)
    cleanup_kwargs = cleanup_params_for_bpm(tempo_used)
    cleaned_notes = cleanup_note_events(recovered_notes, **cleanup_kwargs)
    print(f"    cleaned_notes={len(cleaned_notes)}")
    quantized_notes: list[QuantizedNote] = quantize_note_events(cleaned_notes, grid, subdivision=16)
    print(f"    quantized_notes={len(quantized_notes)}")
    fingered_notes, _debug = optimize_fingering_with_debug(quantized_notes, max_fret=24)
    print(f"    fingered_notes={len(fingered_notes)}")

    elapsed = time.perf_counter() - t0

    comparison = compare_tabs(reference.notes, fingered_notes)
    print("  generating report...")
    report = generate_comparison_report(reference.notes, fingered_notes, song_name=song_name)

    reports_dir.mkdir(parents=True, exist_ok=True)
    safe_name = _safe_name(song_name)
    (reports_dir / f"{safe_name}_quality_report.md").write_text(report)

    metrics = {
        "song": song_name,
        "tempo_used": tempo_used,
        "pipeline_time_sec": elapsed,
        "onset_count": len(onset_times),
        "cleanup_params": cleanup_kwargs,
        "f1_score": comparison.f1_score,
        "precision": comparison.precision,
        "recall": comparison.recall,
        "pitch_accuracy": comparison.pitch_accuracy,
        "fingering_accuracy": comparison.fingering_accuracy,
        "note_density_correlation": comparison.note_density_correlation,
        "total_ref_notes": comparison.total_ref_notes,
        "total_gen_notes": comparison.total_gen_notes,
        "total_matched": comparison.total_matched,
    }
    (reports_dir / f"{safe_name}_quality_metrics.json").write_text(json.dumps(metrics, indent=2))

    return comparison, fingered_notes, metrics


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate DeChord tab quality without madmom")
    parser.add_argument("song", choices=["hysteria", "trooper", "all"], default="all", nargs="?")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent.parent
    test_songs = repo_root / "test songs"
    stems_root = repo_root / "backend" / "stems" / "test_songs"
    reports_dir = repo_root / "docs" / "reports"

    songs = {
        "hysteria": {
            "song_name": "Muse - Hysteria",
            "bass_wav": stems_root / "Muse__Hysteria" / "bass.wav",
            "drums_wav": stems_root / "Muse__Hysteria" / "drums.wav",
            "gp5_path": test_songs / "Muse - Hysteria.gp5",
            "bpm_hint": 94.0,
            "gp5_encoding": None,
        },
        "trooper": {
            "song_name": "Iron Maiden - The Trooper",
            "bass_wav": stems_root / "Iron_Maiden__The_Trooper" / "bass.wav",
            "drums_wav": stems_root / "Iron_Maiden__The_Trooper" / "drums.wav",
            "gp5_path": test_songs / "Iron Maiden - The Trooper.gp5",
            "bpm_hint": 162.0,
            "gp5_encoding": "latin1",
        },
    }

    selected = songs.values() if args.song == "all" else [songs[args.song]]

    for spec in selected:
        print("=" * 64)
        print(f"Evaluating {spec['song_name']}")
        print("=" * 64)
        comparison, _fingered, metrics = evaluate_song(**spec, reports_dir=reports_dir)
        print(f"F1: {comparison.f1_score:.2%}")
        print(f"Precision: {comparison.precision:.2%}")
        print(f"Recall: {comparison.recall:.2%}")
        print(f"Pitch accuracy: {comparison.pitch_accuracy:.2%}")
        print(f"Fingering accuracy: {comparison.fingering_accuracy:.2%}")
        print(f"Tempo used: {metrics['tempo_used']:.1f}")
        print(f"Pipeline time: {metrics['pipeline_time_sec']:.1f}s")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
