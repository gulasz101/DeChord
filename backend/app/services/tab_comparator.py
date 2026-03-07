from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from math import ceil

from app.services.gp5_reference import ReferenceNote


@dataclass
class BarMetrics:
    ref_count: int = 0
    gen_count: int = 0
    matched: int = 0
    pitch_matches: int = 0
    fingering_matches: int = 0

    @property
    def precision(self) -> float:
        return self.matched / self.gen_count if self.gen_count > 0 else 0.0

    @property
    def recall(self) -> float:
        return self.matched / self.ref_count if self.ref_count > 0 else 0.0

    @property
    def f1_score(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) > 0 else 0.0

    @property
    def pitch_accuracy(self) -> float:
        return self.pitch_matches / self.matched if self.matched > 0 else 0.0

    @property
    def fingering_accuracy(self) -> float:
        return self.fingering_matches / self.matched if self.matched > 0 else 0.0


@dataclass
class ComparisonResult:
    total_ref_notes: int = 0
    total_gen_notes: int = 0
    total_matched: int = 0
    total_pitch_matches: int = 0
    total_fingering_matches: int = 0
    per_bar: dict[int, BarMetrics] = field(default_factory=dict)
    timing_offsets: list[float] = field(default_factory=list)
    onset_precision_ms: float = 0.0
    onset_recall_ms: float = 0.0
    onset_f1_ms: float = 0.0
    onset_precision_grid: float = 0.0
    onset_recall_grid: float = 0.0
    onset_f1_grid: float = 0.0
    octave_confusion: dict[str, int] = field(
        default_factory=lambda: {
            "exact": 0,
            "octave_plus_12": 0,
            "octave_minus_12": 0,
            "other": 0,
        }
    )

    @property
    def precision(self) -> float:
        return self.total_matched / self.total_gen_notes if self.total_gen_notes > 0 else 0.0

    @property
    def recall(self) -> float:
        return self.total_matched / self.total_ref_notes if self.total_ref_notes > 0 else 0.0

    @property
    def f1_score(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) > 0 else 0.0

    @property
    def pitch_accuracy(self) -> float:
        return self.total_pitch_matches / self.total_matched if self.total_matched > 0 else 0.0

    @property
    def fingering_accuracy(self) -> float:
        return self.total_fingering_matches / self.total_matched if self.total_matched > 0 else 0.0

    @property
    def note_density_correlation(self) -> float:
        if not self.per_bar:
            return 0.0
        bars = sorted(self.per_bar.keys())
        ref_counts = [self.per_bar[b].ref_count for b in bars]
        gen_counts = [self.per_bar[b].gen_count for b in bars]
        if len(bars) < 2:
            return 1.0 if ref_counts == gen_counts else 0.0
        mean_r = sum(ref_counts) / len(ref_counts)
        mean_g = sum(gen_counts) / len(gen_counts)
        numerator = sum((r - mean_r) * (g - mean_g) for r, g in zip(ref_counts, gen_counts))
        den_r = sum((r - mean_r) ** 2 for r in ref_counts) ** 0.5
        den_g = sum((g - mean_g) ** 2 for g in gen_counts) ** 0.5
        if den_r == 0 or den_g == 0:
            return 1.0 if ref_counts == gen_counts else 0.0
        return numerator / (den_r * den_g)

    @property
    def mean_timing_offset(self) -> float:
        if not self.timing_offsets:
            return 0.0
        return sum(abs(offset) for offset in self.timing_offsets) / len(self.timing_offsets)


def _f1(precision: float, recall: float) -> float:
    if precision + recall <= 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def _match_onsets(
    reference: list[ReferenceNote],
    generated: list[ReferenceNote],
    *,
    tolerance_beats: float,
) -> tuple[int, int, int]:
    ref_by_bar: dict[int, list[ReferenceNote]] = defaultdict(list)
    gen_by_bar: dict[int, list[ReferenceNote]] = defaultdict(list)
    for note in reference:
        ref_by_bar[note.bar_index].append(note)
    for note in generated:
        gen_by_bar[note.bar_index].append(note)

    matched = 0
    for bar_idx in sorted(set(ref_by_bar) | set(gen_by_bar)):
        ref_notes = ref_by_bar.get(bar_idx, [])
        gen_notes = gen_by_bar.get(bar_idx, [])
        used_gen: set[int] = set()
        for ref_note in ref_notes:
            best_idx = None
            best_delta = float("inf")
            for idx, gen_note in enumerate(gen_notes):
                if idx in used_gen:
                    continue
                delta = abs(ref_note.beat_position - gen_note.beat_position)
                if delta <= tolerance_beats and delta < best_delta:
                    best_delta = delta
                    best_idx = idx
            if best_idx is not None:
                matched += 1
                used_gen.add(best_idx)

    return matched, len(reference), len(generated)


def compare_tabs(
    reference: list[ReferenceNote],
    generated: list[ReferenceNote],
    *,
    beat_tolerance: float = 0.05,
    bpm: float = 120.0,
    subdivision: int = 16,
    onset_tolerance_ms: float = 30.0,
) -> ComparisonResult:
    result = ComparisonResult(total_ref_notes=len(reference), total_gen_notes=len(generated))

    ref_by_bar: dict[int, list[ReferenceNote]] = defaultdict(list)
    gen_by_bar: dict[int, list[ReferenceNote]] = defaultdict(list)

    for note in reference:
        ref_by_bar[note.bar_index].append(note)
    for note in generated:
        gen_by_bar[note.bar_index].append(note)

    all_bars = sorted(set(ref_by_bar.keys()) | set(gen_by_bar.keys()))
    for bar_idx in all_bars:
        bar_ref = ref_by_bar.get(bar_idx, [])
        bar_gen = list(gen_by_bar.get(bar_idx, []))
        metrics = BarMetrics(ref_count=len(bar_ref), gen_count=len(bar_gen))

        used_gen: set[int] = set()
        for ref_note in bar_ref:
            best_idx = None
            best_delta = float("inf")
            for idx, gen_note in enumerate(bar_gen):
                if idx in used_gen:
                    continue
                delta = abs(ref_note.beat_position - gen_note.beat_position)
                if delta <= beat_tolerance and delta < best_delta:
                    best_delta = delta
                    best_idx = idx
            if best_idx is None:
                continue

            gen_note = bar_gen[best_idx]
            used_gen.add(best_idx)
            metrics.matched += 1
            result.total_matched += 1
            result.timing_offsets.append(gen_note.beat_position - ref_note.beat_position)

            pitch_delta = gen_note.pitch_midi - ref_note.pitch_midi
            if pitch_delta == 0:
                metrics.pitch_matches += 1
                result.total_pitch_matches += 1
                result.octave_confusion["exact"] += 1
            elif pitch_delta == 12:
                result.octave_confusion["octave_plus_12"] += 1
            elif pitch_delta == -12:
                result.octave_confusion["octave_minus_12"] += 1
            else:
                result.octave_confusion["other"] += 1

            if ref_note.string == gen_note.string and ref_note.fret == gen_note.fret:
                metrics.fingering_matches += 1
                result.total_fingering_matches += 1

        result.per_bar[bar_idx] = metrics

    ms_tolerance_beats = abs((bpm * (onset_tolerance_ms / 1000.0)) / 60.0)
    onset_match_ms, ref_count, gen_count = _match_onsets(
        reference,
        generated,
        tolerance_beats=ms_tolerance_beats,
    )
    result.onset_precision_ms = onset_match_ms / gen_count if gen_count else 0.0
    result.onset_recall_ms = onset_match_ms / ref_count if ref_count else 0.0
    result.onset_f1_ms = _f1(result.onset_precision_ms, result.onset_recall_ms)

    steps_per_beat = max(int(ceil(subdivision / 4)), 1)
    grid_tolerance_beats = 1.0 / steps_per_beat
    onset_match_grid, ref_count, gen_count = _match_onsets(
        reference,
        generated,
        tolerance_beats=grid_tolerance_beats,
    )
    result.onset_precision_grid = onset_match_grid / gen_count if gen_count else 0.0
    result.onset_recall_grid = onset_match_grid / ref_count if ref_count else 0.0
    result.onset_f1_grid = _f1(result.onset_precision_grid, result.onset_recall_grid)

    return result
