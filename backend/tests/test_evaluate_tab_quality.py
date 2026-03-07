from __future__ import annotations

import pytest

from scripts.evaluate_tab_quality import parse_cli_args


def test_parse_cli_args_accepts_resource_monitor_flags() -> None:
    args = parse_cli_args(
        [
            "--song-dir",
            "../test songs",
            "--song",
            "Muse - Hysteria",
            "--resource-monitor",
            "--max-memory-mb",
            "8192",
            "--max-child-procs",
            "3",
        ]
    )

    assert args.resource_monitor is True
    assert args.max_memory_mb == 8192
    assert args.max_child_procs == 3
