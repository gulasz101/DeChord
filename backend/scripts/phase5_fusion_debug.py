#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.evaluate_tab_quality import REPORTS_DIR
from scripts.evaluate_tab_quality import ResolvedInputs
from scripts.evaluate_tab_quality import evaluate_inputs

CANONICAL_INPUTS = [
    ResolvedInputs(
        song_name="Muse - Hysteria",
        mp3_path=(Path(__file__).resolve().parent.parent.parent / "test songs" / "Muse - Hysteria.mp3").resolve(),
        gp5_path=(Path(__file__).resolve().parent.parent.parent / "test songs" / "Muse - Hysteria.gp5").resolve(),
    ),
    ResolvedInputs(
        song_name="Iron Maiden - The Trooper",
        mp3_path=(Path(__file__).resolve().parent.parent.parent / "test songs" / "Iron Maiden - The Trooper.mp3").resolve(),
        gp5_path=(Path(__file__).resolve().parent.parent.parent / "test songs" / "Iron Maiden - The Trooper.gp5").resolve(),
    ),
]


def _song_key(song_name: str) -> str:
    lowered = song_name.lower()
    if "hysteria" in lowered:
        return "hysteria"
    if "trooper" in lowered:
        return "trooper"
    return lowered.replace(" ", "_")


def summarize_fusion_candidates(candidates: list[dict[str, object]]) -> dict[str, object]:
    accepted = [row for row in candidates if row.get("accepted") is True]
    rejected = [row for row in candidates if row.get("accepted") is False]
    rejection_reasons = Counter(str(row.get("rejection_reason")) for row in rejected if row.get("rejection_reason"))

    def avg_anchor_distance(rows: list[dict[str, object]]) -> float:
        distances: list[float] = []
        for row in rows:
            confidence = row.get("confidence_components")
            if not isinstance(confidence, dict):
                continue
            value = confidence.get("anchor_distance_semitones")
            if isinstance(value, int | float):
                distances.append(float(value))
        if not distances:
            return 0.0
        return sum(distances) / float(len(distances))

    return {
        "accepted_dense_pass_notes": len(accepted),
        "rejected_dense_pass_notes": len(rejected),
        "rejection_reasons": dict(sorted(rejection_reasons.items())),
        "avg_pitch_distance_from_anchor_accepted": avg_anchor_distance(accepted),
        "avg_pitch_distance_from_anchor_rejected": avg_anchor_distance(rejected),
    }


def render_phase5_summary_markdown(song_summaries: dict[str, dict[str, object]]) -> str:
    ordered = ["hysteria", "trooper"]
    lines = ["# Phase 5 Fusion Summary", ""]
    for key in ordered:
        summary = song_summaries.get(key)
        if summary is None:
            continue
        title = "Hysteria" if key == "hysteria" else "Trooper"
        lines.extend(
            [
                f"## {title}",
                f"- Accepted dense-pass notes: `{summary['accepted_dense_pass_notes']}`",
                f"- Rejected dense-pass notes: `{summary['rejected_dense_pass_notes']}`",
                "- Rejection histogram:",
            ]
        )
        reasons = summary.get("rejection_reasons", {})
        if isinstance(reasons, dict) and reasons:
            for reason, count in sorted(reasons.items()):
                lines.append(f"  - `{reason}`: `{count}`")
        else:
            lines.append("  - `(none)`")
        lines.extend(
            [
                (
                    "- Average pitch distance from anchor "
                    f"(accepted vs rejected): `{summary['avg_pitch_distance_from_anchor_accepted']:.3f}` / "
                    f"`{summary['avg_pitch_distance_from_anchor_rejected']:.3f}`"
                ),
                "",
            ]
        )
    return "\n".join(lines).strip() + "\n"


def _load_pipeline_debug(debug_path: str) -> dict[str, object]:
    payload = json.loads(Path(debug_path).read_text())
    pipeline_debug = payload.get("pipeline_debug")
    if not isinstance(pipeline_debug, dict):
        return {}
    return pipeline_debug


def _run_for_input(resolved: ResolvedInputs, *, quality: str) -> dict[str, object]:
    song_key = _song_key(resolved.song_name)
    output = evaluate_inputs(resolved, quality=quality, phase=f"phase5_{song_key}_fusion_debug")
    pipeline_debug = _load_pipeline_debug(str(output["debug_path"]))
    candidates = pipeline_debug.get("dense_bar_fusion_candidates")
    candidate_rows = candidates if isinstance(candidates, list) else []
    summary = summarize_fusion_candidates(candidate_rows)

    report_payload = {
        "song": resolved.song_name,
        "quality": quality,
        "resolved_mp3_path": str(resolved.mp3_path),
        "resolved_gp5_path": str(resolved.gp5_path),
        "accepted_dense_pass_notes": summary["accepted_dense_pass_notes"],
        "rejected_dense_pass_notes": summary["rejected_dense_pass_notes"],
        "rejection_reasons": summary["rejection_reasons"],
        "avg_pitch_distance_from_anchor_accepted": summary["avg_pitch_distance_from_anchor_accepted"],
        "avg_pitch_distance_from_anchor_rejected": summary["avg_pitch_distance_from_anchor_rejected"],
        "dense_bar_fusion_candidates": candidate_rows,
    }

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / f"{song_key}_phase5_fusion_debug.json").write_text(json.dumps(report_payload, indent=2, sort_keys=True))
    return summary


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Phase 5 dense-bar fusion diagnostics artifacts")
    parser.add_argument("--mp3")
    parser.add_argument("--gp5")
    parser.add_argument("--quality", default="high_accuracy_aggressive")
    args = parser.parse_args(argv)
    has_mp3 = bool(args.mp3)
    has_gp5 = bool(args.gp5)
    if has_mp3 ^ has_gp5:
        parser.error("--mp3 and --gp5 must be provided together")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.mp3 and args.gp5:
        selected_inputs = [
            ResolvedInputs(
                song_name=Path(args.mp3).stem,
                mp3_path=Path(args.mp3).expanduser().resolve(),
                gp5_path=Path(args.gp5).expanduser().resolve(),
            )
        ]
    else:
        selected_inputs = CANONICAL_INPUTS

    summaries: dict[str, dict[str, object]] = {}
    for resolved in selected_inputs:
        summaries[_song_key(resolved.song_name)] = _run_for_input(resolved, quality=args.quality)

    summary_markdown = render_phase5_summary_markdown(summaries)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / "phase5_fusion_summary.md").write_text(summary_markdown)
    print(json.dumps({"generated": sorted(summaries.keys())}, indent=2))
    print(f"summary: {REPORTS_DIR / 'phase5_fusion_summary.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
