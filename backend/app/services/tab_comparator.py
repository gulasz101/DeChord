from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from app.services.fingering import FingeredNote
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
        num = sum((r - mean_r) * (g - mean_g) for r, g in zip(ref_counts, gen_counts))
        den_r = sum((r - mean_r) ** 2 for r in ref_counts) ** 0.5
        den_g = sum((g - mean_g) ** 2 for g in gen_counts) ** 0.5
        if den_r == 0 or den_g == 0:
            return 1.0 if ref_counts == gen_counts else 0.0
        return num / (den_r * den_g)

    @property
    def mean_timing_offset(self) -> float:
        return sum(abs(t) for t in self.timing_offsets) / len(self.timing_offsets) if self.timing_offsets else 0.0


BEAT_TOLERANCE = 0.125


def compare_tabs(
    reference: list[ReferenceNote],
    generated: list[FingeredNote],
    *,
    beat_tolerance: float = BEAT_TOLERANCE,
) -> ComparisonResult:
    result = ComparisonResult(
        total_ref_notes=len(reference),
        total_gen_notes=len(generated),
    )

    ref_by_bar: dict[int, list[ReferenceNote]] = defaultdict(list)
    gen_by_bar: dict[int, list[FingeredNote]] = defaultdict(list)

    for note in reference:
        ref_by_bar[note.bar_index].append(note)
    for note in generated:
        gen_by_bar[note.bar_index].append(note)

    all_bars = sorted(set(ref_by_bar.keys()) | set(gen_by_bar.keys()))

    for bar_idx in all_bars:
        bar_ref = ref_by_bar.get(bar_idx, [])
        bar_gen = list(gen_by_bar.get(bar_idx, []))
        bm = BarMetrics(ref_count=len(bar_ref), gen_count=len(bar_gen))

        used_gen: set[int] = set()
        for ref_note in bar_ref:
            for gi, gen_note in enumerate(bar_gen):
                if gi in used_gen:
                    continue
                if abs(ref_note.beat_position - gen_note.beat_position) <= beat_tolerance:
                    bm.matched += 1
                    result.total_matched += 1
                    result.timing_offsets.append(gen_note.beat_position - ref_note.beat_position)
                    if ref_note.pitch_midi == gen_note.pitch_midi:
                        bm.pitch_matches += 1
                        result.total_pitch_matches += 1
                    if ref_note.string == gen_note.string and ref_note.fret == gen_note.fret:
                        bm.fingering_matches += 1
                        result.total_fingering_matches += 1
                    used_gen.add(gi)
                    break

        result.per_bar[bar_idx] = bm

    return result
