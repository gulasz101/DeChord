from __future__ import annotations

from scripts.phase5_fusion_debug import render_phase5_summary_markdown
from scripts.phase5_fusion_debug import summarize_fusion_candidates


def test_summarize_fusion_candidates_counts_histogram_and_distance_averages() -> None:
    candidates = [
        {
            "accepted": True,
            "rejection_reason": None,
            "confidence_components": {"anchor_distance_semitones": 1},
        },
        {
            "accepted": True,
            "rejection_reason": None,
            "confidence_components": {"anchor_distance_semitones": 3},
        },
        {
            "accepted": False,
            "rejection_reason": "pitch_far_from_anchor",
            "confidence_components": {"anchor_distance_semitones": 11},
        },
        {
            "accepted": False,
            "rejection_reason": "weak_local_support",
            "confidence_components": {"anchor_distance_semitones": 8},
        },
    ]

    summary = summarize_fusion_candidates(candidates)

    assert summary["accepted_dense_pass_notes"] == 2
    assert summary["rejected_dense_pass_notes"] == 2
    assert summary["rejection_reasons"] == {
        "pitch_far_from_anchor": 1,
        "weak_local_support": 1,
    }
    assert summary["avg_pitch_distance_from_anchor_accepted"] == 2.0
    assert summary["avg_pitch_distance_from_anchor_rejected"] == 9.5


def test_render_phase5_summary_markdown_includes_required_sections() -> None:
    markdown = render_phase5_summary_markdown(
        {
            "hysteria": {
                "accepted_dense_pass_notes": 10,
                "rejected_dense_pass_notes": 4,
                "rejection_reasons": {"weak_local_support": 3, "duplicate_existing_note": 1},
                "avg_pitch_distance_from_anchor_accepted": 1.5,
                "avg_pitch_distance_from_anchor_rejected": 7.0,
            },
            "trooper": {
                "accepted_dense_pass_notes": 6,
                "rejected_dense_pass_notes": 2,
                "rejection_reasons": {"pitch_far_from_anchor": 2},
                "avg_pitch_distance_from_anchor_accepted": 2.0,
                "avg_pitch_distance_from_anchor_rejected": 9.0,
            },
        }
    )

    assert "# Phase 5 Fusion Summary" in markdown
    assert "## Hysteria" in markdown
    assert "## Trooper" in markdown
    assert "accepted dense-pass notes" in markdown.lower()
    assert "rejection histogram" in markdown.lower()
