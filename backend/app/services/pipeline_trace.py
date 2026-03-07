from __future__ import annotations

from collections import Counter
from statistics import median
from typing import Any

DEFAULT_SHORT_NOTE_THRESHOLD_MS = 80


def build_stage_metrics(
    notes: list[object],
    *,
    previous_notes: list[object] | None = None,
    short_note_threshold_ms: int = DEFAULT_SHORT_NOTE_THRESHOLD_MS,
    merged_count: int = 0,
    added_override: int | None = None,
    removed_override: int | None = None,
    altered_override: int | None = None,
    candidate_flow: dict[str, Any] | None = None,
) -> dict[str, Any]:
    durations_ms = [_duration_ms(note) for note in notes]
    confidence_values = [value for value in (_confidence(note) for note in notes) if value is not None]

    added_count = 0
    removed_count = 0
    altered_count = 0
    if previous_notes is not None:
        previous_counter = Counter(_note_key(note) for note in previous_notes)
        current_counter = Counter(_note_key(note) for note in notes)
        common_count = sum((previous_counter & current_counter).values())
        added_count = max(0, len(notes) - common_count)
        removed_count = max(0, len(previous_notes) - common_count)
        altered_count = _altered_count(previous_notes, notes)

    if added_override is not None:
        added_count = max(0, int(added_override))
    if removed_override is not None:
        removed_count = max(0, int(removed_override))
    if altered_override is not None:
        altered_count = max(0, int(altered_override))

    if confidence_values:
        confidence_stats: dict[str, float | None] = {
            "mean": float(sum(confidence_values) / len(confidence_values)),
            "min": float(min(confidence_values)),
            "max": float(max(confidence_values)),
        }
    else:
        confidence_stats = {"mean": None, "min": None, "max": None}

    metrics = {
        "note_count": len(notes),
        "average_duration_ms": float(sum(durations_ms) / len(durations_ms)) if durations_ms else 0.0,
        "median_duration_ms": float(median(durations_ms)) if durations_ms else 0.0,
        "short_note_threshold_ms": int(short_note_threshold_ms),
        "short_note_count": sum(1 for duration_ms in durations_ms if duration_ms < float(short_note_threshold_ms)),
        "octave_jump_count": _octave_jump_count(notes),
        "pitch_range": _pitch_range(notes),
        "confidence_stats": confidence_stats,
        "notes_added_by_stage": int(added_count),
        "notes_removed_by_stage": int(removed_count),
        "notes_merged_by_stage": int(max(0, merged_count)),
        "notes_altered_by_stage": int(altered_count),
    }
    if candidate_flow is not None:
        metrics["candidate_flow"] = candidate_flow
    return metrics


def build_pipeline_trace_report(
    *,
    song_name: str,
    pipeline_stats: dict[str, dict[str, Any]],
    resource_monitor: dict[str, Any] | None = None,
) -> dict[str, Any]:
    report = {
        "song": song_name,
        "pipeline_stats": pipeline_stats,
    }
    if resource_monitor is not None:
        report["resource_monitor"] = resource_monitor
    return report


def _duration_ms(note: object) -> float:
    start_sec = float(getattr(note, "start_sec", 0.0))
    end_sec = float(getattr(note, "end_sec", start_sec))
    return max(0.0, end_sec - start_sec) * 1000.0


def _confidence(note: object) -> float | None:
    value = getattr(note, "confidence", None)
    if value is None:
        return None
    return float(value)


def _note_key(note: object) -> tuple[int, float, float]:
    return (
        int(getattr(note, "pitch_midi")),
        round(float(getattr(note, "start_sec")), 6),
        round(float(getattr(note, "end_sec")), 6),
    )


def _timing_key(note: object) -> tuple[float, float]:
    return (
        round(float(getattr(note, "start_sec")), 6),
        round(float(getattr(note, "end_sec")), 6),
    )


def _altered_count(previous_notes: list[object], notes: list[object]) -> int:
    previous_by_time = Counter(_timing_key(note) for note in previous_notes)
    current_by_time = Counter(_timing_key(note) for note in notes)
    shared_timings = previous_by_time & current_by_time
    if not shared_timings:
        return 0

    previous_pitch_by_time = Counter((_timing_key(note), int(getattr(note, "pitch_midi"))) for note in previous_notes)
    current_pitch_by_time = Counter((_timing_key(note), int(getattr(note, "pitch_midi"))) for note in notes)
    unchanged = previous_pitch_by_time & current_pitch_by_time
    return max(0, sum(shared_timings.values()) - sum(unchanged.values()))


def _octave_jump_count(notes: list[object]) -> int:
    ordered = sorted(
        notes,
        key=lambda note: (
            float(getattr(note, "start_sec", 0.0)),
            float(getattr(note, "end_sec", 0.0)),
            int(getattr(note, "pitch_midi", 0)),
        ),
    )
    octave_jumps = 0
    previous_pitch: int | None = None
    for note in ordered:
        pitch = int(getattr(note, "pitch_midi"))
        if previous_pitch is not None:
            delta = abs(pitch - previous_pitch)
            if delta >= 12 and delta % 12 == 0:
                octave_jumps += 1
        previous_pitch = pitch
    return octave_jumps


def _pitch_range(notes: list[object]) -> dict[str, int | None]:
    if not notes:
        return {"min": None, "max": None}
    pitches = [int(getattr(note, "pitch_midi")) for note in notes]
    return {"min": int(min(pitches)), "max": int(max(pitches))}
