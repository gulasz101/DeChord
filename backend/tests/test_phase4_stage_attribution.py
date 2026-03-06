from __future__ import annotations

from scripts.phase4_stage_attribution import StageBarCounts
from scripts.phase4_stage_attribution import bar_deficit_top_n


def test_bar_deficit_top_n_orders_by_largest_deficit_then_bar_index() -> None:
    ref_counts = {0: 6, 1: 5, 2: 8, 3: 3}
    final_counts = {0: 4, 1: 1, 2: 8, 3: 0}

    rows = bar_deficit_top_n(ref_counts, final_counts, limit=3)

    assert [row.bar_index for row in rows] == [1, 3, 0]
    assert [row.deficit for row in rows] == [4, 3, 2]


def test_bar_deficit_top_n_includes_stage_counts_with_zero_fill() -> None:
    ref_counts = {0: 4, 1: 4}
    final_counts = {0: 2}
    stage_counts = {
        "raw": {0: 3, 1: 1},
        "cleanup": {0: 2},
    }

    rows = bar_deficit_top_n(ref_counts, final_counts, limit=2, stage_counts=stage_counts)

    assert len(rows) == 2
    assert rows[0].stage_counts == {"raw": 1, "cleanup": 0}
    assert rows[1].stage_counts == {"raw": 3, "cleanup": 2}


def test_stage_bar_counts_to_markdown_row() -> None:
    row = StageBarCounts(
        bar_index=12,
        reference_count=10,
        final_generated_count=3,
        deficit=7,
        stage_counts={"raw": 9, "cleanup": 5, "final": 3},
    )

    rendered = row.to_markdown_row(["raw", "cleanup", "final"])

    assert rendered == "| 12 | 10 | 3 | 7 | 9 | 5 | 3 |"
