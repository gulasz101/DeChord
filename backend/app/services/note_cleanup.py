from __future__ import annotations

from app.services.bass_transcriber import RawNoteEvent


def _filter_noise(
    events: list[RawNoteEvent],
    *,
    min_duration_sec: float,
    min_confidence: float,
) -> list[RawNoteEvent]:
    filtered: list[RawNoteEvent] = []
    for event in events:
        duration = event.end_sec - event.start_sec
        if duration < min_duration_sec:
            continue
        if event.confidence < min_confidence:
            continue
        filtered.append(event)
    return filtered


def _enforce_monophony(events: list[RawNoteEvent]) -> list[RawNoteEvent]:
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

    return [event for event in result if event.end_sec - event.start_sec > 0]


def _merge_repeated_notes(events: list[RawNoteEvent], *, merge_gap_sec: float) -> list[RawNoteEvent]:
    if not events:
        return []

    merged: list[RawNoteEvent] = [events[0]]
    for event in events[1:]:
        last = merged[-1]
        gap = event.start_sec - last.end_sec
        if event.pitch_midi == last.pitch_midi and 0 <= gap < merge_gap_sec:
            merged[-1] = RawNoteEvent(
                pitch_midi=last.pitch_midi,
                start_sec=last.start_sec,
                end_sec=max(last.end_sec, event.end_sec),
                confidence=max(last.confidence, event.confidence),
            )
            continue
        merged.append(event)
    return merged


def _correct_octave_jumps(events: list[RawNoteEvent]) -> list[RawNoteEvent]:
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
                break

    return corrected


def cleanup_params_for_bpm(bpm: float) -> dict:
    """Return cleanup parameters tuned for the given BPM.

    At high BPMs, 16th notes are shorter and we need to lower thresholds
    to avoid filtering them out. At 160 BPM, a 16th note is ~94ms.
    """
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
) -> list[RawNoteEvent]:
    if not events:
        return []

    cleaned = _filter_noise(events, min_duration_sec=min_duration_sec, min_confidence=min_confidence)
    cleaned = _enforce_monophony(cleaned)
    cleaned = _merge_repeated_notes(cleaned, merge_gap_sec=merge_gap_sec)
    if apply_octave_correction:
        cleaned = _correct_octave_jumps(cleaned)
    return cleaned
