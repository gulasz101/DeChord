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
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
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
