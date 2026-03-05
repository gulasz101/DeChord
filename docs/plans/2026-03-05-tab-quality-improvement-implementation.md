# Tab Quality Improvement Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Systematically improve bass tab generation quality so output matches professional GP5 transcriptions of The Trooper and Hysteria in pitch, rhythm, note density, and fingering.

**Architecture:** Build a GP5 reference parser and comparison harness first, establish baseline metrics, then iteratively improve transcription, cleanup, quantization, export, and fingering stages — measuring quality gains at each step.

**Tech Stack:** Python (pyguitarpro, basic_pitch, librosa, mido), pytest, Markdown reporting.

---

### Task 1: GP5 Reference Parser

**Files:**
- Create: `backend/app/services/gp5_reference.py`
- Test: `backend/tests/test_gp5_reference.py`

**Step 1: Write failing test for GP5 bass track extraction**

```python
# backend/tests/test_gp5_reference.py
from __future__ import annotations

from pathlib import Path

import pytest

from app.services.gp5_reference import ReferenceNote, parse_gp5_bass_track

TEST_SONGS = Path(__file__).resolve().parent.parent.parent / "test songs"
HYSTERIA_GP5 = TEST_SONGS / "Muse - Hysteria.gp5"
TROOPER_GP5 = TEST_SONGS / "Iron Maiden - The Trooper.gp5"


@pytest.mark.skipif(not HYSTERIA_GP5.exists(), reason="test song not available")
def test_parse_hysteria_bass_track() -> None:
    result = parse_gp5_bass_track(HYSTERIA_GP5)
    assert result.tempo > 0
    assert result.time_signature == (4, 4)
    assert len(result.notes) > 0
    assert len(result.bars) > 0
    # Hysteria bar 0 has 16 sixteenth notes on string 3
    bar0_notes = [n for n in result.notes if n.bar_index == 0]
    assert len(bar0_notes) == 16
    assert all(n.duration_beats == 0.25 for n in bar0_notes)  # 16th notes


@pytest.mark.skipif(not TROOPER_GP5.exists(), reason="test song not available")
def test_parse_trooper_bass_track() -> None:
    result = parse_gp5_bass_track(TROOPER_GP5, encoding="latin1")
    assert result.tempo == 162
    assert len(result.notes) > 0
    # Trooper bar 0: 10 notes (mix of 8ths and 16ths)
    bar0_notes = [n for n in result.notes if n.bar_index == 0]
    assert len(bar0_notes) == 10


def test_reference_note_has_required_fields() -> None:
    note = ReferenceNote(
        bar_index=0,
        beat_position=0.0,
        duration_beats=0.25,
        pitch_midi=33,
        string=3,
        fret=0,
    )
    assert note.pitch_midi == 33
    assert note.string == 3
    assert note.fret == 0
```

**Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_gp5_reference.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.gp5_reference'`

**Step 3: Write minimal implementation**

```python
# backend/app/services/gp5_reference.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import guitarpro


@dataclass(frozen=True)
class ReferenceNote:
    bar_index: int
    beat_position: float
    duration_beats: float
    pitch_midi: int
    string: int
    fret: int


@dataclass(frozen=True)
class ReferenceTab:
    tempo: int
    time_signature: tuple[int, int]
    bars: list[int]  # bar indices
    notes: list[ReferenceNote]
    track_name: str


def _duration_value_to_beats(value: int, *, dotted: bool) -> float:
    """Convert pyguitarpro duration.value to beats (quarter = 1.0)."""
    base = 4.0 / value  # whole=4.0, half=2.0, quarter=1.0, 8th=0.5, 16th=0.25
    if dotted:
        base *= 1.5
    return base


def _find_bass_track(song: guitarpro.Song) -> guitarpro.Track | None:
    """Find the bass track by tuning (4-string E1/A1/D2/G2) or name."""
    for track in song.tracks:
        if len(track.strings) == 4:
            values = sorted(s.value for s in track.strings)
            if values == [28, 33, 38, 43]:
                return track
    # Fallback: search by name
    for track in song.tracks:
        if "bass" in track.name.lower():
            return track
    return None


def parse_gp5_bass_track(
    gp5_path: Path,
    *,
    encoding: str | None = None,
) -> ReferenceTab:
    """Parse a GP5 file and extract the bass track as ReferenceNote list."""
    kwargs = {"encoding": encoding} if encoding else {}
    song = guitarpro.parse(str(gp5_path), **kwargs)

    bass_track = _find_bass_track(song)
    if bass_track is None:
        raise ValueError(f"No bass track found in {gp5_path.name}")

    # Build string-to-midi mapping from tuning
    string_midi: dict[int, int] = {}
    for s in bass_track.strings:
        string_midi[s.number] = s.value

    notes: list[ReferenceNote] = []
    bar_indices: list[int] = []

    for m_idx, measure in enumerate(bass_track.measures):
        bar_indices.append(m_idx)
        header = song.measureHeaders[m_idx]
        ts_num = header.timeSignature.numerator
        ts_den = header.timeSignature.denominator.value
        beats_per_bar = ts_num * (4.0 / ts_den)

        # Process voice 0 (primary voice)
        beat_position = 0.0
        for beat in measure.voices[0].beats:
            dur_beats = _duration_value_to_beats(
                beat.duration.value,
                dotted=beat.duration.isDotted,
            )
            for note in beat.notes:
                open_midi = string_midi.get(note.string, 0)
                pitch_midi = open_midi + note.value
                notes.append(
                    ReferenceNote(
                        bar_index=m_idx,
                        beat_position=round(beat_position, 6),
                        duration_beats=round(dur_beats, 6),
                        pitch_midi=pitch_midi,
                        string=note.string,
                        fret=note.value,
                    )
                )
            beat_position += dur_beats

    ts = song.measureHeaders[0].timeSignature
    return ReferenceTab(
        tempo=song.tempo,
        time_signature=(ts.numerator, ts.denominator.value),
        bars=bar_indices,
        notes=notes,
        track_name=bass_track.name,
    )
```

**Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_gp5_reference.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/services/gp5_reference.py backend/tests/test_gp5_reference.py
git commit -m "feat(pipeline): add GP5 reference bass track parser (docs/plans/2026-03-05-tab-quality-improvement-implementation.md)"
```

---

### Task 2: Tab Comparator Module

**Files:**
- Create: `backend/app/services/tab_comparator.py`
- Test: `backend/tests/test_tab_comparator.py`

**Step 1: Write failing test for note comparison**

```python
# backend/tests/test_tab_comparator.py
from __future__ import annotations

from app.services.fingering import FingeredNote
from app.services.gp5_reference import ReferenceNote
from app.services.tab_comparator import ComparisonResult, compare_tabs


def _ref(bar: int, beat: float, dur: float, pitch: int, string: int, fret: int) -> ReferenceNote:
    return ReferenceNote(bar_index=bar, beat_position=beat, duration_beats=dur, pitch_midi=pitch, string=string, fret=fret)


def _gen(bar: int, beat: float, dur: float, pitch: int, string: int, fret: int) -> FingeredNote:
    return FingeredNote(bar_index=bar, beat_position=beat, duration_beats=dur, pitch_midi=pitch, start_sec=0.0, end_sec=0.0, string=string, fret=fret)


def test_perfect_match_returns_100_percent() -> None:
    ref = [_ref(0, 0.0, 0.25, 33, 3, 0), _ref(0, 0.25, 0.25, 40, 2, 2)]
    gen = [_gen(0, 0.0, 0.25, 33, 3, 0), _gen(0, 0.25, 0.25, 40, 2, 2)]
    result = compare_tabs(ref, gen)
    assert result.pitch_accuracy == 1.0
    assert result.note_density_correlation >= 0.99
    assert result.f1_score == 1.0
    assert result.fingering_accuracy == 1.0


def test_missing_notes_lowers_recall() -> None:
    ref = [_ref(0, 0.0, 0.25, 33, 3, 0), _ref(0, 0.25, 0.25, 40, 2, 2)]
    gen = [_gen(0, 0.0, 0.25, 33, 3, 0)]
    result = compare_tabs(ref, gen)
    assert result.f1_score < 1.0
    assert result.recall < 1.0
    assert result.precision == 1.0


def test_extra_notes_lowers_precision() -> None:
    ref = [_ref(0, 0.0, 0.25, 33, 3, 0)]
    gen = [_gen(0, 0.0, 0.25, 33, 3, 0), _gen(0, 0.25, 0.25, 40, 2, 2)]
    result = compare_tabs(ref, gen)
    assert result.precision < 1.0
    assert result.recall == 1.0


def test_wrong_pitch_lowers_pitch_accuracy() -> None:
    ref = [_ref(0, 0.0, 0.25, 33, 3, 0)]
    gen = [_gen(0, 0.0, 0.25, 35, 3, 2)]  # wrong pitch
    result = compare_tabs(ref, gen)
    assert result.pitch_accuracy == 0.0


def test_empty_inputs() -> None:
    result = compare_tabs([], [])
    assert result.f1_score == 0.0
    assert result.precision == 0.0
    assert result.recall == 0.0


def test_per_bar_breakdown() -> None:
    ref = [_ref(0, 0.0, 0.25, 33, 3, 0), _ref(1, 0.0, 0.25, 40, 2, 2)]
    gen = [_gen(0, 0.0, 0.25, 33, 3, 0)]
    result = compare_tabs(ref, gen)
    assert 0 in result.per_bar
    assert 1 in result.per_bar
    assert result.per_bar[0].f1_score == 1.0
    assert result.per_bar[1].f1_score == 0.0
```

**Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_tab_comparator.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Write minimal implementation**

```python
# backend/app/services/tab_comparator.py
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from app.services.fingering import FingeredNote
from app.services.gp5_reference import ReferenceNote


@dataclass(frozen=True)
class BarMetrics:
    bar_index: int
    ref_count: int
    gen_count: int
    matched: int
    pitch_matches: int
    fingering_matches: int
    precision: float
    recall: float
    f1_score: float
    pitch_accuracy: float
    fingering_accuracy: float


@dataclass(frozen=True)
class ComparisonResult:
    precision: float
    recall: float
    f1_score: float
    pitch_accuracy: float
    fingering_accuracy: float
    note_density_correlation: float
    mean_timing_offset: float
    total_ref_notes: int
    total_gen_notes: int
    total_matched: int
    per_bar: dict[int, BarMetrics] = field(default_factory=dict)


def _match_notes_in_bar(
    ref_notes: list[ReferenceNote],
    gen_notes: list[FingeredNote],
    *,
    timing_tolerance: float = 0.3,
) -> list[tuple[ReferenceNote, FingeredNote]]:
    """Match generated notes to reference notes by beat position (greedy nearest)."""
    matches: list[tuple[ReferenceNote, FingeredNote]] = []
    used_gen: set[int] = set()

    for ref in sorted(ref_notes, key=lambda n: n.beat_position):
        best_idx: int | None = None
        best_dist = float("inf")
        for idx, gen in enumerate(gen_notes):
            if idx in used_gen:
                continue
            dist = abs(ref.beat_position - gen.beat_position)
            if dist < best_dist and dist <= timing_tolerance:
                best_dist = dist
                best_idx = idx
        if best_idx is not None:
            matches.append((ref, gen_notes[best_idx]))
            used_gen.add(best_idx)

    return matches


def _compute_bar_metrics(
    bar_index: int,
    ref_notes: list[ReferenceNote],
    gen_notes: list[FingeredNote],
) -> BarMetrics:
    matches = _match_notes_in_bar(ref_notes, gen_notes)
    matched = len(matches)
    pitch_matches = sum(1 for r, g in matches if r.pitch_midi == g.pitch_midi)
    fingering_matches = sum(
        1 for r, g in matches if r.string == g.string and r.fret == g.fret
    )

    precision = matched / len(gen_notes) if gen_notes else 0.0
    recall = matched / len(ref_notes) if ref_notes else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
    pitch_acc = pitch_matches / matched if matched else 0.0
    fing_acc = fingering_matches / matched if matched else 0.0

    return BarMetrics(
        bar_index=bar_index,
        ref_count=len(ref_notes),
        gen_count=len(gen_notes),
        matched=matched,
        pitch_matches=pitch_matches,
        fingering_matches=fingering_matches,
        precision=precision,
        recall=recall,
        f1_score=f1,
        pitch_accuracy=pitch_acc,
        fingering_accuracy=fing_acc,
    )


def compare_tabs(
    reference: list[ReferenceNote],
    generated: list[FingeredNote],
) -> ComparisonResult:
    if not reference and not generated:
        return ComparisonResult(
            precision=0.0,
            recall=0.0,
            f1_score=0.0,
            pitch_accuracy=0.0,
            fingering_accuracy=0.0,
            note_density_correlation=0.0,
            mean_timing_offset=0.0,
            total_ref_notes=0,
            total_gen_notes=0,
            total_matched=0,
        )

    # Group by bar
    ref_by_bar: dict[int, list[ReferenceNote]] = defaultdict(list)
    gen_by_bar: dict[int, list[FingeredNote]] = defaultdict(list)
    for n in reference:
        ref_by_bar[n.bar_index].append(n)
    for n in generated:
        gen_by_bar[n.bar_index].append(n)

    all_bars = sorted(set(ref_by_bar.keys()) | set(gen_by_bar.keys()))
    per_bar: dict[int, BarMetrics] = {}
    total_matched = 0
    total_pitch = 0
    total_fing = 0
    timing_offsets: list[float] = []

    for bar_idx in all_bars:
        ref_notes = ref_by_bar.get(bar_idx, [])
        gen_notes = gen_by_bar.get(bar_idx, [])
        bm = _compute_bar_metrics(bar_idx, ref_notes, gen_notes)
        per_bar[bar_idx] = bm
        total_matched += bm.matched
        total_pitch += bm.pitch_matches
        total_fing += bm.fingering_matches

        # Collect timing offsets for matched notes
        matches = _match_notes_in_bar(ref_notes, gen_notes)
        for r, g in matches:
            timing_offsets.append(abs(r.beat_position - g.beat_position))

    total_ref = len(reference)
    total_gen = len(generated)
    precision = total_matched / total_gen if total_gen else 0.0
    recall = total_matched / total_ref if total_ref else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
    pitch_acc = total_pitch / total_matched if total_matched else 0.0
    fing_acc = total_fing / total_matched if total_matched else 0.0
    mean_timing = sum(timing_offsets) / len(timing_offsets) if timing_offsets else 0.0

    # Note density correlation (Pearson R)
    ref_counts = [len(ref_by_bar.get(b, [])) for b in all_bars]
    gen_counts = [len(gen_by_bar.get(b, [])) for b in all_bars]
    density_corr = _pearson_r(ref_counts, gen_counts)

    return ComparisonResult(
        precision=precision,
        recall=recall,
        f1_score=f1,
        pitch_accuracy=pitch_acc,
        fingering_accuracy=fing_acc,
        note_density_correlation=density_corr,
        mean_timing_offset=mean_timing,
        total_ref_notes=total_ref,
        total_gen_notes=total_gen,
        total_matched=total_matched,
        per_bar=per_bar,
    )


def _pearson_r(x: list[int | float], y: list[int | float]) -> float:
    n = len(x)
    if n < 2:
        return 0.0
    mx = sum(x) / n
    my = sum(y) / n
    cov = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
    sx = sum((xi - mx) ** 2 for xi in x) ** 0.5
    sy = sum((yi - my) ** 2 for yi in y) ** 0.5
    if sx == 0 or sy == 0:
        return 0.0
    return cov / (sx * sy)
```

**Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_tab_comparator.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/services/tab_comparator.py backend/tests/test_tab_comparator.py
git commit -m "feat(pipeline): add tab comparison metrics module (docs/plans/2026-03-05-tab-quality-improvement-implementation.md)"
```

---

### Task 3: Visual Diff Report Generator

**Files:**
- Create: `backend/app/services/tab_report.py`
- Test: `backend/tests/test_tab_report.py`

**Step 1: Write failing test**

```python
# backend/tests/test_tab_report.py
from __future__ import annotations

from app.services.fingering import FingeredNote
from app.services.gp5_reference import ReferenceNote
from app.services.tab_report import generate_comparison_report


def _ref(bar: int, beat: float, dur: float, pitch: int, string: int, fret: int) -> ReferenceNote:
    return ReferenceNote(bar_index=bar, beat_position=beat, duration_beats=dur, pitch_midi=pitch, string=string, fret=fret)


def _gen(bar: int, beat: float, dur: float, pitch: int, string: int, fret: int) -> FingeredNote:
    return FingeredNote(bar_index=bar, beat_position=beat, duration_beats=dur, pitch_midi=pitch, start_sec=0.0, end_sec=0.0, string=string, fret=fret)


def test_report_contains_summary_and_per_bar_table() -> None:
    ref = [_ref(0, 0.0, 0.25, 33, 3, 0), _ref(0, 0.25, 0.25, 40, 2, 2)]
    gen = [_gen(0, 0.0, 0.25, 33, 3, 0)]
    report = generate_comparison_report(ref, gen, song_name="Test Song")
    assert "# Test Song" in report
    assert "F1" in report
    assert "| 0 |" in report  # per-bar row


def test_report_marks_missing_notes() -> None:
    ref = [_ref(0, 0.0, 0.25, 33, 3, 0)]
    gen = []  # no generated notes
    report = generate_comparison_report(ref, gen, song_name="Test")
    assert "MISS" in report or "0.00" in report
```

**Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_tab_report.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# backend/app/services/tab_report.py
from __future__ import annotations

from app.services.fingering import FingeredNote
from app.services.gp5_reference import ReferenceNote
from app.services.tab_comparator import compare_tabs


def generate_comparison_report(
    reference: list[ReferenceNote],
    generated: list[FingeredNote],
    *,
    song_name: str = "Unknown",
) -> str:
    result = compare_tabs(reference, generated)
    lines: list[str] = []
    lines.append(f"# {song_name} — Tab Quality Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Reference notes | {result.total_ref_notes} |")
    lines.append(f"| Generated notes | {result.total_gen_notes} |")
    lines.append(f"| Matched notes | {result.total_matched} |")
    lines.append(f"| Precision | {result.precision:.2%} |")
    lines.append(f"| Recall | {result.recall:.2%} |")
    lines.append(f"| F1 Score | {result.f1_score:.2%} |")
    lines.append(f"| Pitch Accuracy | {result.pitch_accuracy:.2%} |")
    lines.append(f"| Fingering Accuracy | {result.fingering_accuracy:.2%} |")
    lines.append(f"| Density Correlation | {result.note_density_correlation:.3f} |")
    lines.append(f"| Mean Timing Offset | {result.mean_timing_offset:.3f} beats |")
    lines.append("")
    lines.append("## Per-Bar Breakdown")
    lines.append("")
    lines.append("| Bar | Ref | Gen | Match | Pitch | Fing | F1 | Status |")
    lines.append("|-----|-----|-----|-------|-------|------|-----|--------|")

    for bar_idx in sorted(result.per_bar):
        bm = result.per_bar[bar_idx]
        if bm.ref_count == 0 and bm.gen_count == 0:
            status = "EMPTY"
        elif bm.gen_count == 0:
            status = "MISS"
        elif bm.ref_count == 0:
            status = "EXTRA"
        elif bm.f1_score >= 0.9:
            status = "OK"
        elif bm.f1_score >= 0.5:
            status = "PARTIAL"
        else:
            status = "POOR"
        lines.append(
            f"| {bar_idx} | {bm.ref_count} | {bm.gen_count} | {bm.matched} "
            f"| {bm.pitch_accuracy:.2f} | {bm.fingering_accuracy:.2f} "
            f"| {bm.f1_score:.2f} | {status} |"
        )

    lines.append("")
    return "\n".join(lines)
```

**Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_tab_report.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/services/tab_report.py backend/tests/test_tab_report.py
git commit -m "feat(pipeline): add visual diff tab quality report generator (docs/plans/2026-03-05-tab-quality-improvement-implementation.md)"
```

---

### Task 4: Evaluation Script — Stem Separation + Pipeline Run + Comparison

**Files:**
- Create: `backend/scripts/evaluate_tab_quality.py`
- Test: run manually against test songs

**Step 1: Write the evaluation script**

```python
#!/usr/bin/env python
# backend/scripts/evaluate_tab_quality.py
"""
End-to-end tab quality evaluation.

Usage:
    cd backend && uv run python scripts/evaluate_tab_quality.py

Runs Demucs stem separation (cached), full TabPipeline, and compares
against GP5 reference tabs. Writes quality reports to docs/reports/.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

# Ensure backend is on the path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

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
    print(f"  Running Demucs on {mp3_path.name}...")
    # Use demucs to separate, then extract bass and drums
    cmd = [
        sys.executable, "-m", "demucs",
        "--two-stems", "bass",
        "-o", str(output_dir / "demucs_out"),
        str(mp3_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  Demucs failed: {result.stderr[:500]}")
        raise RuntimeError(f"Demucs failed for {mp3_path.name}")

    # Find the output files
    stem_name = mp3_path.stem
    demucs_dir = output_dir / "demucs_out" / "htdemucs" / stem_name
    if not demucs_dir.exists():
        # Try mdx_extra model name
        for model_dir in (output_dir / "demucs_out").iterdir():
            candidate = model_dir / stem_name
            if candidate.exists():
                demucs_dir = candidate
                break

    src_bass = demucs_dir / "bass.wav"
    src_no_bass = demucs_dir / "no_bass.wav"

    if src_bass.exists():
        import shutil
        shutil.copy2(src_bass, bass_wav)
    else:
        raise RuntimeError(f"bass.wav not found in {demucs_dir}")

    # For drums, run a second separation
    cmd_drums = [
        sys.executable, "-m", "demucs",
        "--two-stems", "drums",
        "-o", str(output_dir / "demucs_drums_out"),
        str(mp3_path),
    ]
    result_drums = subprocess.run(cmd_drums, capture_output=True, text=True)
    if result_drums.returncode != 0:
        print(f"  Demucs drums failed, using librosa fallback for rhythm")
        # Create empty drums wav as fallback
        import wave
        with wave.open(str(drums_wav), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(44100)
            w.writeframes(b"\x00" * 44100 * 2)
    else:
        drums_demucs_dir = output_dir / "demucs_drums_out" / "htdemucs" / stem_name
        if not drums_demucs_dir.exists():
            for model_dir in (output_dir / "demucs_drums_out").iterdir():
                candidate = model_dir / stem_name
                if candidate.exists():
                    drums_demucs_dir = candidate
                    break
        src_drums = drums_demucs_dir / "drums.wav"
        if src_drums.exists():
            import shutil
            shutil.copy2(src_drums, drums_wav)

    return bass_wav, drums_wav


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


def pipeline_result_to_fingered_notes(result) -> list:
    """Extract FingeredNote-like objects from alphatex for comparison.

    Actually, the pipeline returns FingeredNote objects indirectly through alphatex.
    We need to re-run the pipeline stages up to fingering to get them.
    Instead, we parse the alphatex back, or better: modify pipeline to expose them.
    """
    # For now, run pipeline stages individually to get fingered notes
    from app.services.tab_pipeline import TabPipeline
    # The result object has debug_info but not the actual fingered notes list.
    # We'll need to either modify the pipeline or re-derive from alphatex.
    # For the initial version, we'll parse the alphatex output.
    return _parse_alphatex_to_notes(result.alphatex, result.tempo_used)


def _parse_alphatex_to_notes(alphatex: str, tempo: float):
    """Parse alphatex back into FingeredNote-like objects for comparison."""
    from app.services.fingering import FingeredNote, STANDARD_BASS_TUNING_MIDI

    lines = alphatex.strip().split("\n")
    body_line = ""
    for line in lines:
        if not line.startswith("\\"):
            body_line = line
            break
        if not any(line.startswith(f"\\{kw}") for kw in ["tempo", "ts", "tuning", "sync"]):
            body_line = line
            break

    # Find the body (measures separated by |)
    for line in lines:
        if "|" in line:
            body_line = line
            break

    if not body_line:
        return []

    measures = body_line.split("|")
    notes = []
    dur_map = {"1": 4.0, "2": 2.0, "4": 1.0, "8": 0.5, "16": 0.25}

    for bar_idx, measure in enumerate(measures):
        measure = measure.strip()
        if not measure or measure.startswith("r"):
            continue
        tokens = measure.split()
        beat_pos = 0.0
        for token in tokens:
            if token.startswith("r"):
                # Rest
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
            continue

        print(f"  Pipeline: tempo={result.tempo_used}, bars={len(result.bars)}")
        print(f"  Debug: {json.dumps({k: v for k, v in result.debug_info.items() if k in ['raw_note_count', 'cleaned_note_count', 'quantized_note_count', 'fingered_note_count']}, indent=2)}")

        # 4. Parse generated notes from alphatex
        gen_notes = _parse_alphatex_to_notes(result.alphatex, result.tempo_used)
        print(f"  Generated: {len(gen_notes)} notes from alphatex")

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

        # Also save raw comparison data as JSON
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
```

**Step 2: Run the script to establish baseline metrics**

Run: `cd backend && uv run python scripts/evaluate_tab_quality.py`
Expected: Reports written, baseline metrics established.

**Step 3: Commit**

```bash
git add backend/scripts/evaluate_tab_quality.py
git commit -m "feat(pipeline): add end-to-end tab quality evaluation script (docs/plans/2026-03-05-tab-quality-improvement-implementation.md)"
```

---

### Task 5: Expose FingeredNotes from Pipeline for Direct Comparison

**Files:**
- Modify: `backend/app/services/tab_pipeline.py`
- Test: `backend/tests/test_tab_pipeline.py`

**Step 1: Write failing test**

```python
# Add to backend/tests/test_tab_pipeline.py

def test_pipeline_result_exposes_fingered_notes() -> None:
    """TabPipelineResult must include fingered_notes for direct comparison."""
    # ... (same setup as existing compose test)
    # Assert:
    assert hasattr(result, "fingered_notes")
    assert len(result.fingered_notes) > 0
```

**Step 2: Run to verify failure**

Run: `cd backend && uv run pytest tests/test_tab_pipeline.py::test_pipeline_result_exposes_fingered_notes -v`
Expected: FAIL — `AttributeError: 'TabPipelineResult' has no attribute 'fingered_notes'`

**Step 3: Add `fingered_notes` field to `TabPipelineResult` and populate it**

In `tab_pipeline.py`, add `fingered_notes: list[FingeredNote]` to the dataclass and set it in `run()`.

**Step 4: Run tests**

Run: `cd backend && uv run pytest tests/test_tab_pipeline.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/services/tab_pipeline.py backend/tests/test_tab_pipeline.py
git commit -m "feat(pipeline): expose fingered_notes in TabPipelineResult (docs/plans/2026-03-05-tab-quality-improvement-implementation.md)"
```

---

### Task 6: BasicPitch Transcription Parameter Tuning

**Files:**
- Modify: `backend/app/midi.py`
- Modify: `backend/app/services/bass_transcriber.py`
- Test: `backend/tests/test_bass_transcriber.py`

**Step 1: Write failing test for configurable BasicPitch parameters**

```python
# Add to test_bass_transcriber.py

def test_transcriber_accepts_sensitivity_kwargs() -> None:
    """BasicPitchTranscriber.transcribe should accept onset_threshold, frame_threshold."""
    transcriber = BasicPitchTranscriber(
        midi_transcribe_fn=lambda path, **kw: b"MThd...",
        parse_notes_fn=lambda midi_bytes: [],
    )
    # Should not raise TypeError
    result = transcriber.transcribe(Path("bass.wav"), onset_threshold=0.3, frame_threshold=0.1)
    assert result.engine == "basic_pitch"
```

**Step 2: Run to verify failure**

Run: `cd backend && uv run pytest tests/test_bass_transcriber.py::test_transcriber_accepts_sensitivity_kwargs -v`

**Step 3: Implement — pass BasicPitch parameters through**

Modify `_transcribe_with_basic_pitch` in `midi.py` to accept and forward `onset_threshold`, `frame_threshold`, `minimum_note_length`, `minimum_frequency` parameters.

Modify `BasicPitchTranscriber.transcribe()` to forward kwargs to the transcription function.

Default values tuned for bass:
- `onset_threshold=0.3` (lower than default 0.5 to catch more onsets)
- `frame_threshold=0.15` (lower than default 0.3 for better recall)
- `minimum_note_length=50` (50ms minimum)
- `minimum_frequency=30` (bass range starts at ~31 Hz for B0)

**Step 4: Run tests**

Run: `cd backend && uv run pytest tests/test_bass_transcriber.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/midi.py backend/app/services/bass_transcriber.py backend/tests/test_bass_transcriber.py
git commit -m "feat(pipeline): add configurable BasicPitch transcription parameters (docs/plans/2026-03-05-tab-quality-improvement-implementation.md)"
```

---

### Task 7: Onset Detection Enhancement for Repeated Notes

**Files:**
- Create: `backend/app/services/onset_recovery.py`
- Test: `backend/tests/test_onset_recovery.py`

**Step 1: Write failing test**

```python
# backend/tests/test_onset_recovery.py
from __future__ import annotations

from app.services.bass_transcriber import RawNoteEvent
from app.services.onset_recovery import recover_missing_onsets


def test_splits_long_note_at_detected_onset() -> None:
    """A long note that spans multiple onset times should be split."""
    notes = [RawNoteEvent(pitch_midi=33, start_sec=0.0, end_sec=2.0, confidence=0.9)]
    onset_times = [0.0, 0.5, 1.0, 1.5]  # 4 onsets during the note
    result = recover_missing_onsets(notes, onset_times)
    assert len(result) == 4  # split into 4 notes


def test_no_split_when_note_is_short() -> None:
    """Short notes shouldn't be split even if onsets exist."""
    notes = [RawNoteEvent(pitch_midi=33, start_sec=0.0, end_sec=0.3, confidence=0.9)]
    onset_times = [0.0, 0.15]
    result = recover_missing_onsets(notes, onset_times, min_split_duration=0.25)
    assert len(result) == 1  # not split because resulting notes would be too short


def test_preserves_notes_without_extra_onsets() -> None:
    notes = [RawNoteEvent(pitch_midi=33, start_sec=0.0, end_sec=0.5, confidence=0.9)]
    onset_times = [0.0]  # only one onset at start
    result = recover_missing_onsets(notes, onset_times)
    assert len(result) == 1
```

**Step 2: Run to verify failure**

Run: `cd backend && uv run pytest tests/test_onset_recovery.py -v`

**Step 3: Implement onset recovery**

```python
# backend/app/services/onset_recovery.py
from __future__ import annotations

from app.services.bass_transcriber import RawNoteEvent


def recover_missing_onsets(
    notes: list[RawNoteEvent],
    onset_times: list[float],
    *,
    min_split_duration: float = 0.08,
    onset_tolerance: float = 0.05,
) -> list[RawNoteEvent]:
    """Split long notes at detected onset times to recover repeated notes."""
    if not notes or not onset_times:
        return list(notes)

    sorted_onsets = sorted(onset_times)
    result: list[RawNoteEvent] = []

    for note in notes:
        # Find onsets that fall within this note (excluding the start)
        interior_onsets = [
            t for t in sorted_onsets
            if note.start_sec + onset_tolerance < t < note.end_sec - min_split_duration
        ]

        if not interior_onsets:
            result.append(note)
            continue

        # Split the note at each interior onset
        boundaries = [note.start_sec] + interior_onsets + [note.end_sec]
        for i in range(len(boundaries) - 1):
            seg_start = boundaries[i]
            seg_end = boundaries[i + 1]
            if seg_end - seg_start >= min_split_duration:
                result.append(RawNoteEvent(
                    pitch_midi=note.pitch_midi,
                    start_sec=seg_start,
                    end_sec=seg_end,
                    confidence=note.confidence,
                ))

    result.sort(key=lambda n: (n.start_sec, n.pitch_midi))
    return result
```

**Step 4: Run tests**

Run: `cd backend && uv run pytest tests/test_onset_recovery.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/services/onset_recovery.py backend/tests/test_onset_recovery.py
git commit -m "feat(pipeline): add onset-based repeated note recovery (docs/plans/2026-03-05-tab-quality-improvement-implementation.md)"
```

---

### Task 8: Integrate Onset Recovery into Pipeline

**Files:**
- Modify: `backend/app/services/tab_pipeline.py`
- Test: `backend/tests/test_tab_pipeline.py`

**Step 1: Write failing test**

```python
# Add to test_tab_pipeline.py

def test_pipeline_applies_onset_recovery_when_enabled() -> None:
    """With onset_recovery enabled, pipeline should split long notes at onset times."""
    # Create a long note that should be split
    long_note = RawNoteEvent(pitch_midi=33, start_sec=0.0, end_sec=2.0, confidence=0.9)

    class FakeTranscriber:
        def transcribe(self, _bass_wav, **kw):
            return BassTranscriptionResult(engine="fake", midi_bytes=b"MThd", raw_notes=[long_note])

    bars = [Bar(index=0, start_sec=0.0, end_sec=2.0, beats_sec=[0.0, 0.5, 1.0, 1.5])]

    pipeline = TabPipeline(
        transcriber=FakeTranscriber(),
        rhythm_extract_fn=lambda _d, **kw: ([0.0, 0.5, 1.0, 1.5], [0.0], "fake"),
        bar_builder_fn=lambda _b, _d, **kw: bars,
    )

    result = pipeline.run(
        Path("bass.wav"), Path("drums.wav"),
        bpm_hint=120.0,
        onset_recovery=True,
    )

    # Should have more than 1 note after onset recovery splits the long note
    assert result.debug_info.get("onset_recovery_applied") is True
```

**Step 2: Run to verify failure**

**Step 3: Integrate onset recovery into `TabPipeline.run()`**

Add `onset_recovery: bool = False` parameter. When enabled:
1. After transcription, detect onsets on bass stem using `librosa.onset.onset_detect()`
2. Run `recover_missing_onsets()` on the raw notes before cleanup
3. Record diagnostics

**Step 4: Run tests**

Run: `cd backend && uv run pytest tests/test_tab_pipeline.py -v`

**Step 5: Commit**

```bash
git add backend/app/services/tab_pipeline.py backend/tests/test_tab_pipeline.py
git commit -m "feat(pipeline): integrate onset recovery into tab pipeline (docs/plans/2026-03-05-tab-quality-improvement-implementation.md)"
```

---

### Task 9: Note Cleanup Parameter Calibration

**Files:**
- Modify: `backend/app/services/note_cleanup.py`
- Modify: `backend/app/services/tab_pipeline.py`
- Test: `backend/tests/test_note_cleanup.py`

**Step 1: Write failing test for BPM-adaptive thresholds**

```python
# Add to test_note_cleanup.py

def test_adaptive_cleanup_at_high_bpm_keeps_short_notes() -> None:
    """At 160 BPM, 16th notes are ~94ms. Cleanup should not filter them."""
    fast_notes = [
        RawNoteEvent(pitch_midi=33, start_sec=0.0, end_sec=0.094, confidence=0.5),
        RawNoteEvent(pitch_midi=33, start_sec=0.094, end_sec=0.188, confidence=0.5),
    ]
    result = cleanup_note_events(fast_notes, min_duration_sec=0.05, min_confidence=0.2)
    assert len(result) == 2  # both kept at BPM-appropriate threshold


def test_octave_correction_enabled_fixes_jump() -> None:
    """Octave jumps should be corrected when enabled."""
    notes = [
        RawNoteEvent(pitch_midi=33, start_sec=0.0, end_sec=0.5, confidence=0.9),
        RawNoteEvent(pitch_midi=45, start_sec=0.5, end_sec=1.0, confidence=0.9),  # +12 octave jump
        RawNoteEvent(pitch_midi=35, start_sec=1.0, end_sec=1.5, confidence=0.9),
    ]
    result = cleanup_note_events(notes, apply_octave_correction=True)
    assert result[1].pitch_midi == 33  # corrected down one octave
```

**Step 2: Run to verify — some may already pass, calibrate thresholds**

**Step 3: Adjust cleanup defaults and add BPM-aware `cleanup_for_bpm()` helper**

Add a helper function:
```python
def cleanup_params_for_bpm(bpm: float) -> dict:
    """Return cleanup parameters tuned for the given BPM."""
    sixteenth_duration = 60.0 / bpm / 4.0
    return {
        "min_duration_sec": max(0.03, sixteenth_duration * 0.6),
        "min_confidence": 0.15,
        "merge_gap_sec": max(0.02, sixteenth_duration * 0.3),
        "apply_octave_correction": True,
    }
```

**Step 4: Run tests**

Run: `cd backend && uv run pytest tests/test_note_cleanup.py -v`

**Step 5: Commit**

```bash
git add backend/app/services/note_cleanup.py backend/app/services/tab_pipeline.py backend/tests/test_note_cleanup.py
git commit -m "feat(pipeline): add BPM-adaptive cleanup thresholds and enable octave correction (docs/plans/2026-03-05-tab-quality-improvement-implementation.md)"
```

---

### Task 10: AlphaTeX Dotted Notes and Better Rest Handling

**Files:**
- Modify: `backend/app/services/alphatex_exporter.py`
- Test: `backend/tests/test_alphatex_exporter.py`

**Step 1: Write failing tests**

```python
# Add to test_alphatex_exporter.py

def test_dotted_quarter_note_exported() -> None:
    note = FingeredNote(
        bar_index=0, beat_position=0.0, duration_beats=1.5,
        pitch_midi=33, start_sec=0.0, end_sec=0.0, string=3, fret=0,
    )
    bars = [Bar(index=0, start_sec=0.0, end_sec=2.0, beats_sec=[0.0, 0.5, 1.0, 1.5])]
    alphatex, _ = export_alphatex([note], bars, tempo_used=120)
    assert "4d" in alphatex  # dotted quarter


def test_rest_fills_gap_between_notes() -> None:
    notes = [
        FingeredNote(bar_index=0, beat_position=0.0, duration_beats=1.0,
                     pitch_midi=33, start_sec=0.0, end_sec=0.0, string=3, fret=0),
        FingeredNote(bar_index=0, beat_position=3.0, duration_beats=1.0,
                     pitch_midi=33, start_sec=0.0, end_sec=0.0, string=3, fret=0),
    ]
    bars = [Bar(index=0, start_sec=0.0, end_sec=2.0, beats_sec=[0.0, 0.5, 1.0, 1.5])]
    alphatex, _ = export_alphatex(notes, bars, tempo_used=120)
    # Should have a rest between the two notes (beats 1-3)
    assert "r." in alphatex
```

**Step 2: Run to verify failure**

**Step 3: Implement dotted note tokens and gap-filling rests**

Update `_duration_to_token`:
```python
def _duration_to_token(duration_beats: float) -> str:
    # Check dotted durations first (within tolerance)
    if abs(duration_beats - 3.0) < 0.1:
        return "2d"  # dotted half
    if abs(duration_beats - 1.5) < 0.05:
        return "4d"  # dotted quarter
    if abs(duration_beats - 0.75) < 0.03:
        return "8d"  # dotted eighth
    if abs(duration_beats - 0.375) < 0.02:
        return "16d"  # dotted sixteenth
    # Standard durations
    if duration_beats >= 4.0:
        return "1"
    if duration_beats >= 2.0:
        return "2"
    if duration_beats >= 1.0:
        return "4"
    if duration_beats >= 0.5:
        return "8"
    return "16"
```

Add rest-filling logic in `export_alphatex` to insert rests between non-adjacent notes within a bar.

**Step 4: Run tests**

Run: `cd backend && uv run pytest tests/test_alphatex_exporter.py -v`

**Step 5: Commit**

```bash
git add backend/app/services/alphatex_exporter.py backend/tests/test_alphatex_exporter.py
git commit -m "feat(pipeline): add dotted notes and gap-filling rests to alphatex export (docs/plans/2026-03-05-tab-quality-improvement-implementation.md)"
```

---

### Task 11: Run Evaluation and Measure Quality Improvement

**Files:**
- Run: `backend/scripts/evaluate_tab_quality.py`
- Create: `docs/reports/baseline_quality.md`

**Step 1: Run full evaluation with all improvements**

Run: `cd backend && uv run python scripts/evaluate_tab_quality.py`

**Step 2: Analyze results and identify remaining gaps**

Review the per-bar comparison reports. Identify:
- Bars with worst F1 scores
- Systematic patterns (always missing notes in certain positions, consistent pitch errors)
- Whether density gaps are due to transcription misses or cleanup over-filtering

**Step 3: Document baseline + improved metrics**

Write a summary comparing baseline vs improved metrics to `docs/reports/`.

**Step 4: Commit reports**

```bash
git add docs/reports/
git commit -m "docs: add initial quality evaluation reports (docs/plans/2026-03-05-tab-quality-improvement-implementation.md)"
```

---

### Task 12: Iterative Refinement Based on Evaluation Results

**Files:** Depends on Task 11 findings.

This task is data-driven. Based on the evaluation results from Task 11:

1. **If pitch accuracy is low**: Focus on BasicPitch parameter tuning, try lower thresholds, add onset detection.
2. **If note density is low**: Focus on cleanup thresholds (too aggressive filtering), onset recovery (repeated notes merged).
3. **If timing is off**: Focus on quantization grid alignment, bar boundary detection.
4. **If fingering doesn't match**: Tune DP solver transition costs, verify tuning mapping.

For each improvement:
- Adjust parameters in the relevant module.
- Re-run evaluation script.
- Compare metrics before/after.
- Commit when metrics improve.

**Step 1: Run evaluation, identify worst area**

**Step 2: Adjust parameters for that area**

**Step 3: Re-run evaluation, verify improvement**

**Step 4: Repeat for next worst area**

**Step 5: Commit all improvements with metrics summary**

---

### Task 13: Final Reset and Verification

**Files:**
- Run: `make reset`
- Update: this plan file with completion checkboxes

**Step 1: Run full reset**

Run: `make reset`

**Step 2: Run evaluation one final time from clean state**

Run: `cd backend && uv run python scripts/evaluate_tab_quality.py`

**Step 3: Verify all tests pass**

Run: `cd backend && uv run pytest -v`

**Step 4: Update plan with final metrics and mark complete**

**Step 5: Final commit**

```bash
git add -A
git commit -m "chore: final verification and quality metrics (docs/plans/2026-03-05-tab-quality-improvement-implementation.md)"
```

---

## Task Checklist

- [ ] Task 1: GP5 Reference Parser
- [x] Task 2: Tab Comparator Module
- [ ] Task 3: Visual Diff Report Generator
- [ ] Task 4: Evaluation Script
- [ ] Task 5: Expose FingeredNotes from Pipeline
- [ ] Task 6: BasicPitch Transcription Parameter Tuning
- [ ] Task 7: Onset Detection Enhancement
- [ ] Task 8: Integrate Onset Recovery into Pipeline
- [ ] Task 9: Note Cleanup Parameter Calibration
- [ ] Task 10: AlphaTeX Dotted Notes and Better Rests
- [ ] Task 11: Run Evaluation and Measure Quality
- [ ] Task 12: Iterative Refinement
- [ ] Task 13: Final Reset and Verification
