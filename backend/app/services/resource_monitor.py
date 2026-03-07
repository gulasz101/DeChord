from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass
import _thread
import os
import subprocess
from threading import Event
from threading import Lock
from threading import Thread
from typing import Callable


DEFAULT_MAX_MEMORY_MB = 12_288
DEFAULT_MAX_CHILD_PROCESSES = 4
DEFAULT_POLL_INTERVAL_SEC = 2.0


@dataclass(frozen=True)
class ResourceMonitorConfig:
    enabled: bool = False
    max_memory_mb: int = DEFAULT_MAX_MEMORY_MB
    max_child_processes: int = DEFAULT_MAX_CHILD_PROCESSES
    poll_interval_sec: float = DEFAULT_POLL_INTERVAL_SEC


@dataclass(frozen=True)
class ResourceMonitorSnapshot:
    pid: int
    rss_mb: float
    child_process_count: int
    descendant_process_count: int
    sampled_process_count: int


@dataclass(frozen=True)
class ResourceMonitorSummary:
    enabled: bool
    max_memory_mb: int
    max_child_processes: int
    poll_interval_sec: float
    serial_execution: bool
    thresholds_exceeded: bool
    aborted_for_safety: bool
    exceeded_reason: str | None
    sample_count: int
    peak_rss_mb: float | None
    peak_child_process_count: int
    peak_descendant_process_count: int
    limit_snapshot: ResourceMonitorSnapshot | None

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


class ResourceLimitExceeded(RuntimeError):
    def __init__(self, summary: ResourceMonitorSummary) -> None:
        self.summary = summary
        detail = summary.exceeded_reason or "resource_limit"
        super().__init__(f"Resource safety threshold exceeded: {detail}")


ProcessSnapshotProvider = Callable[[], list[dict[str, int]]]
ResourceSampleFn = Callable[[int], ResourceMonitorSnapshot]


def sample_process_tree_usage(
    *,
    pid: int | None = None,
    process_snapshot_provider: ProcessSnapshotProvider | None = None,
) -> ResourceMonitorSnapshot:
    root_pid = int(os.getpid() if pid is None else pid)
    rows = (process_snapshot_provider or _read_process_snapshot)()
    by_parent: dict[int, list[dict[str, int]]] = {}
    by_pid: dict[int, dict[str, int]] = {}
    for row in rows:
        proc_pid = int(row["pid"])
        by_pid[proc_pid] = row
        by_parent.setdefault(int(row["ppid"]), []).append(row)

    if root_pid not in by_pid:
        return ResourceMonitorSnapshot(
            pid=root_pid,
            rss_mb=0.0,
            child_process_count=0,
            descendant_process_count=0,
            sampled_process_count=0,
        )

    stack = [root_pid]
    descendant_pids: list[int] = []
    rss_kb = 0
    while stack:
        current_pid = stack.pop()
        row = by_pid.get(current_pid)
        if row is None:
            continue
        descendant_pids.append(current_pid)
        rss_kb += int(row["rss_kb"])
        stack.extend(int(child["pid"]) for child in by_parent.get(current_pid, []))

    descendant_process_count = len(descendant_pids)
    return ResourceMonitorSnapshot(
        pid=root_pid,
        rss_mb=float(rss_kb) / 1024.0,
        child_process_count=len(by_parent.get(root_pid, [])),
        descendant_process_count=descendant_process_count,
        sampled_process_count=descendant_process_count,
    )


def run_with_resource_monitor(
    work_fn: Callable[[], object],
    *,
    config: ResourceMonitorConfig,
    sample_fn: ResourceSampleFn | None = None,
) -> tuple[object, ResourceMonitorSummary]:
    if not config.enabled:
        result = work_fn()
        return result, ResourceMonitorSummary(
            enabled=False,
            max_memory_mb=int(config.max_memory_mb),
            max_child_processes=int(config.max_child_processes),
            poll_interval_sec=float(config.poll_interval_sec),
            serial_execution=True,
            thresholds_exceeded=False,
            aborted_for_safety=False,
            exceeded_reason=None,
            sample_count=0,
            peak_rss_mb=None,
            peak_child_process_count=0,
            peak_descendant_process_count=0,
            limit_snapshot=None,
        )

    pid = os.getpid()
    sampler = sample_fn or (lambda process_pid: sample_process_tree_usage(pid=process_pid))
    stop_event = Event()
    threshold_event = Event()
    state_lock = Lock()
    state: dict[str, object] = {
        "sample_count": 0,
        "peak_rss_mb": 0.0,
        "peak_child_process_count": 0,
        "peak_descendant_process_count": 0,
        "limit_snapshot": None,
        "exceeded_reason": None,
    }

    def monitor() -> None:
        while not stop_event.is_set():
            snapshot = sampler(pid)
            exceeded_reason: str | None = None
            if snapshot.rss_mb > float(config.max_memory_mb):
                exceeded_reason = "memory_limit_mb"
            elif snapshot.child_process_count > int(config.max_child_processes):
                exceeded_reason = "child_process_limit"

            with state_lock:
                state["sample_count"] = int(state["sample_count"]) + 1
                state["peak_rss_mb"] = max(float(state["peak_rss_mb"]), float(snapshot.rss_mb))
                state["peak_child_process_count"] = max(
                    int(state["peak_child_process_count"]),
                    int(snapshot.child_process_count),
                )
                state["peak_descendant_process_count"] = max(
                    int(state["peak_descendant_process_count"]),
                    int(snapshot.descendant_process_count),
                )
                if exceeded_reason is not None and state["limit_snapshot"] is None:
                    state["limit_snapshot"] = snapshot
                    state["exceeded_reason"] = exceeded_reason

            if exceeded_reason is not None:
                threshold_event.set()
                stop_event.set()
                _thread.interrupt_main()
                return

            stop_event.wait(max(0.01, float(config.poll_interval_sec)))

    monitor_thread = Thread(target=monitor, name="dechord-resource-monitor", daemon=True)
    monitor_thread.start()
    try:
        result = work_fn()
    except KeyboardInterrupt as exc:
        if not threshold_event.is_set():
            raise
        raise ResourceLimitExceeded(
            _build_summary(config=config, state=state, thresholds_exceeded=True, aborted_for_safety=True)
        ) from exc
    finally:
        stop_event.set()
        monitor_thread.join(timeout=max(0.1, float(config.poll_interval_sec) * 2.0))

    summary = _build_summary(
        config=config,
        state=state,
        thresholds_exceeded=threshold_event.is_set(),
        aborted_for_safety=False,
    )
    return result, summary


def _build_summary(
    *,
    config: ResourceMonitorConfig,
    state: dict[str, object],
    thresholds_exceeded: bool,
    aborted_for_safety: bool,
) -> ResourceMonitorSummary:
    sample_count = int(state["sample_count"])
    peak_rss_mb = float(state["peak_rss_mb"]) if sample_count > 0 else None
    limit_snapshot = state["limit_snapshot"] if isinstance(state["limit_snapshot"], ResourceMonitorSnapshot) else None
    exceeded_reason = state["exceeded_reason"] if isinstance(state["exceeded_reason"], str) else None
    return ResourceMonitorSummary(
        enabled=True,
        max_memory_mb=int(config.max_memory_mb),
        max_child_processes=int(config.max_child_processes),
        poll_interval_sec=float(config.poll_interval_sec),
        serial_execution=True,
        thresholds_exceeded=bool(thresholds_exceeded),
        aborted_for_safety=bool(aborted_for_safety),
        exceeded_reason=exceeded_reason,
        sample_count=sample_count,
        peak_rss_mb=peak_rss_mb,
        peak_child_process_count=int(state["peak_child_process_count"]),
        peak_descendant_process_count=int(state["peak_descendant_process_count"]),
        limit_snapshot=limit_snapshot,
    )


def _read_process_snapshot() -> list[dict[str, int]]:
    result = subprocess.run(
        ["ps", "-axo", "pid=,ppid=,rss="],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        error = result.stderr.strip() or result.stdout.strip() or "ps failed"
        raise RuntimeError(f"Unable to sample process tree: {error}")

    rows: list[dict[str, int]] = []
    for line in result.stdout.splitlines():
        parts = line.strip().split()
        if len(parts) != 3:
            continue
        try:
            pid_value = int(parts[0])
            ppid_value = int(parts[1])
            rss_value = int(parts[2])
        except ValueError:
            continue
        rows.append({"pid": pid_value, "ppid": ppid_value, "rss_kb": rss_value})
    return rows
