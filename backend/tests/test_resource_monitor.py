from __future__ import annotations

import time

import pytest

from app.services.resource_monitor import ResourceLimitExceeded
from app.services.resource_monitor import ResourceMonitorConfig
from app.services.resource_monitor import ResourceMonitorSnapshot
from app.services.resource_monitor import ResourceMonitorSummary
from app.services.resource_monitor import run_with_resource_monitor
from app.services.resource_monitor import sample_process_tree_usage


def test_sample_process_tree_usage_returns_stable_structure() -> None:
    snapshot = sample_process_tree_usage(
        pid=100,
        process_snapshot_provider=lambda: [
            {"pid": 100, "ppid": 1, "rss_kb": 256_000},
            {"pid": 101, "ppid": 100, "rss_kb": 128_000},
            {"pid": 102, "ppid": 100, "rss_kb": 64_000},
            {"pid": 103, "ppid": 2, "rss_kb": 512_000},
        ],
    )

    assert isinstance(snapshot, ResourceMonitorSnapshot)
    assert snapshot.pid == 100
    assert snapshot.rss_mb == pytest.approx((256_000 + 128_000 + 64_000) / 1024.0, rel=1e-4)
    assert snapshot.child_process_count == 2
    assert snapshot.descendant_process_count == 3
    assert snapshot.sampled_process_count == 3


def test_sample_process_tree_usage_counts_grandchildren() -> None:
    snapshot = sample_process_tree_usage(
        pid=200,
        process_snapshot_provider=lambda: [
            {"pid": 200, "ppid": 1, "rss_kb": 100_000},
            {"pid": 201, "ppid": 200, "rss_kb": 90_000},
            {"pid": 202, "ppid": 201, "rss_kb": 80_000},
        ],
    )

    assert snapshot.child_process_count == 1
    assert snapshot.descendant_process_count == 3
    assert snapshot.rss_mb == pytest.approx((100_000 + 90_000 + 80_000) / 1024.0, rel=1e-4)


def test_run_with_resource_monitor_aborts_when_memory_threshold_is_exceeded() -> None:
    samples = iter(
        [
            ResourceMonitorSnapshot(
                pid=321,
                rss_mb=128.0,
                child_process_count=1,
                descendant_process_count=2,
                sampled_process_count=2,
            ),
            ResourceMonitorSnapshot(
                pid=321,
                rss_mb=2048.0,
                child_process_count=1,
                descendant_process_count=2,
                sampled_process_count=2,
            ),
        ]
    )

    def long_running_work() -> str:
        time.sleep(0.2)
        return "finished"

    with pytest.raises(ResourceLimitExceeded) as exc_info:
        run_with_resource_monitor(
            long_running_work,
            config=ResourceMonitorConfig(
                enabled=True,
                max_memory_mb=512,
                max_child_processes=4,
                poll_interval_sec=0.01,
            ),
            sample_fn=lambda _pid: next(samples),
        )

    assert exc_info.value.summary.aborted_for_safety is True
    assert exc_info.value.summary.thresholds_exceeded is True
    assert exc_info.value.summary.exceeded_reason == "memory_limit_mb"
    assert exc_info.value.summary.limit_snapshot is not None
    assert exc_info.value.summary.limit_snapshot.rss_mb == pytest.approx(2048.0)


def test_run_with_resource_monitor_aborts_when_child_process_threshold_is_exceeded() -> None:
    samples = iter(
        [
            ResourceMonitorSnapshot(
                pid=654,
                rss_mb=256.0,
                child_process_count=1,
                descendant_process_count=2,
                sampled_process_count=2,
            ),
            ResourceMonitorSnapshot(
                pid=654,
                rss_mb=384.0,
                child_process_count=7,
                descendant_process_count=8,
                sampled_process_count=8,
            ),
        ]
    )

    with pytest.raises(ResourceLimitExceeded) as exc_info:
        run_with_resource_monitor(
            lambda: time.sleep(0.2),
            config=ResourceMonitorConfig(
                enabled=True,
                max_memory_mb=4096,
                max_child_processes=4,
                poll_interval_sec=0.01,
            ),
            sample_fn=lambda _pid: next(samples),
        )

    assert exc_info.value.summary.thresholds_exceeded is True
    assert exc_info.value.summary.exceeded_reason == "child_process_limit"
    assert exc_info.value.summary.limit_snapshot is not None
    assert exc_info.value.summary.limit_snapshot.child_process_count == 7


def test_run_with_resource_monitor_returns_summary_when_disabled() -> None:
    result, summary = run_with_resource_monitor(
        lambda: "ok",
        config=ResourceMonitorConfig(enabled=False, max_memory_mb=512, max_child_processes=2),
        sample_fn=lambda _pid: ResourceMonitorSnapshot(
            pid=999,
            rss_mb=12.0,
            child_process_count=0,
            descendant_process_count=1,
            sampled_process_count=1,
        ),
    )

    assert result == "ok"
    assert isinstance(summary, ResourceMonitorSummary)
    assert summary.enabled is False
    assert summary.thresholds_exceeded is False
    assert summary.aborted_for_safety is False
    assert summary.limit_snapshot is None
