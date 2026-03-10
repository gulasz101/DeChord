from __future__ import annotations

from app.services.bass_transcriber import RawNoteEvent


def _init_stats(stats: dict[str, int] | None) -> dict[str, int]:
    target = stats if stats is not None else {}
    for key in (
        "removed_short",
        "removed_low_conf",
        "removed_overlap",
        "merged_same_pitch",
        "octave_corrected",
        "merges_blocked_by_onset",
        "merges_blocked_by_tag",
    ):
        target.setdefault(key, 0)
    return target


def _filter_noise(
    events: list[RawNoteEvent],
    *,
    min_duration_sec: float,
    min_confidence: float,
    stats: dict[str, int],
) -> list[RawNoteEvent]:
    filtered: list[RawNoteEvent] = []
    for event in events:
        duration = event.end_sec - event.start_sec
        if duration < min_duration_sec:
            stats["removed_short"] += 1
            continue
        if event.confidence < min_confidence:
            stats["removed_low_conf"] += 1
            continue
        filtered.append(event)
    return filtered


def _enforce_monophony(events: list[RawNoteEvent], *, stats: dict[str, int]) -> list[RawNoteEvent]:
    if not events:
        return []

    ordered = sorted(events, key=lambda event: (event.start_sec, event.end_sec, event.pitch_midi))
    result: list[RawNoteEvent] = [ordered[0]]

    for current in ordered[1:]:
        previous = result[-1]
        if current.start_sec >= previous.end_sec:
            result.append(current)
            continue

        if current.confidence > previous.confidence:
            trimmed_previous = RawNoteEvent(
                pitch_midi=previous.pitch_midi,
                start_sec=previous.start_sec,
                end_sec=current.start_sec,
                confidence=previous.confidence,
            )
            result[-1] = trimmed_previous
            result.append(current)
            stats["removed_overlap"] += 1
            continue

        if current.end_sec > previous.end_sec:
            shifted_current = RawNoteEvent(
                pitch_midi=current.pitch_midi,
                start_sec=previous.end_sec,
                end_sec=current.end_sec,
                confidence=current.confidence,
            )
            if shifted_current.end_sec - shifted_current.start_sec > 0:
                result.append(shifted_current)
                stats["removed_overlap"] += 1

    return [event for event in result if event.end_sec - event.start_sec > 0]


def _has_onset_between(onset_times: list[float], *, start: float, end: float) -> bool:
    for onset in onset_times:
        if start <= onset <= end:
            return True
    return False


def _merge_repeated_notes(
    events: list[RawNoteEvent],
    *,
    merge_gap_sec: float,
    onset_times: list[float],
    onset_split_starts: set[float],
    stats: dict[str, int],
) -> list[RawNoteEvent]:
    if not events:
        return []

    merged: list[RawNoteEvent] = [events[0]]
    for event in events[1:]:
        last = merged[-1]
        gap = event.start_sec - last.end_sec
        if event.pitch_midi == last.pitch_midi and 0 <= gap < merge_gap_sec:
            if _has_onset_between(onset_times, start=last.end_sec, end=event.start_sec):
                stats["merges_blocked_by_onset"] += 1
                merged.append(event)
                continue

            last_tagged = round(last.start_sec, 6) in onset_split_starts
            current_tagged = round(event.start_sec, 6) in onset_split_starts
            if last_tagged or current_tagged:
                stats["merges_blocked_by_tag"] += 1
                merged.append(event)
                continue

            merged[-1] = RawNoteEvent(
                pitch_midi=last.pitch_midi,
                start_sec=last.start_sec,
                end_sec=max(last.end_sec, event.end_sec),
                confidence=max(last.confidence, event.confidence),
            )
            stats["merged_same_pitch"] += 1
            continue
        merged.append(event)
    return merged


def _correct_octave_jumps(events: list[RawNoteEvent], *, stats: dict[str, int]) -> list[RawNoteEvent]:
    if len(events) < 3:
        return events

    corrected = list(events)
    for idx in range(1, len(corrected) - 1):
        prev_note = corrected[idx - 1].pitch_midi
        current = corrected[idx]
        next_note = corrected[idx + 1].pitch_midi

        if abs(current.pitch_midi - prev_note) < 11:
            continue
        if abs(next_note - prev_note) > 4:
            continue

        for shift in (-12, 12):
            shifted = current.pitch_midi + shift
            if abs(shifted - prev_note) <= 4 and abs(shifted - next_note) <= 4:
                corrected[idx] = RawNoteEvent(
                    pitch_midi=shifted,
                    start_sec=current.start_sec,
                    end_sec=current.end_sec,
                    confidence=current.confidence,
                )
                stats["octave_corrected"] += 1
                break

    return corrected


def cleanup_params_for_bpm(bpm: float) -> dict[str, float | bool]:
    bpm = max(float(bpm), 1.0)
    sixteenth_duration = 60.0 / bpm / 4.0
    return {
        # Keep thresholds high enough to suppress spurious micro-notes at fast tempos.
        "min_duration_sec": max(0.07, sixteenth_duration * 0.6),
        "min_confidence": 0.15,
        "merge_gap_sec": max(0.04, sixteenth_duration * 0.3),
        "apply_octave_correction": True,
    }


def cleanup_note_events(
    events: list[RawNoteEvent],
    *,
    min_duration_sec: float = 0.06,
    min_confidence: float = 0.2,
    merge_gap_sec: float = 0.04,
    apply_octave_correction: bool = False,
    onset_times: list[float] | None = None,
    onset_split_starts: set[float] | None = None,
    stats: dict[str, int] | None = None,
) -> list[RawNoteEvent]:
    if not events:
        if stats is not None:
            _init_stats(stats)
        return []

    internal_stats = _init_stats(stats)
    onset_times = sorted(onset_times or [])
    onset_split_starts = onset_split_starts or set()

    cleaned = _filter_noise(
        events,
        min_duration_sec=min_duration_sec,
        min_confidence=min_confidence,
        stats=internal_stats,
    )
    cleaned = _enforce_monophony(cleaned, stats=internal_stats)
    cleaned = _merge_repeated_notes(
        cleaned,
        merge_gap_sec=merge_gap_sec,
        onset_times=onset_times,
        onset_split_starts=onset_split_starts,
        stats=internal_stats,
    )
    if apply_octave_correction:
        cleaned = _correct_octave_jumps(cleaned, stats=internal_stats)
    return cleaned
