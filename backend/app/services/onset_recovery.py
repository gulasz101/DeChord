from __future__ import annotations

from app.services.bass_transcriber import RawNoteEvent


def recover_missing_onsets(
    notes: list[RawNoteEvent],
    onset_times: list[float],
    *,
    min_split_duration: float = 0.08,
    onset_tolerance: float = 0.05,
) -> list[RawNoteEvent]:
    """Split long notes at detected onset times to recover repeated notes."""
    if not notes or not onset_times:
        return list(notes)

    sorted_onsets = sorted(onset_times)
    result: list[RawNoteEvent] = []

    for note in notes:
        interior_onsets = [
            t for t in sorted_onsets
            if note.start_sec + onset_tolerance < t < note.end_sec - min_split_duration
        ]

        if not interior_onsets:
            result.append(note)
            continue

        boundaries = [note.start_sec] + interior_onsets + [note.end_sec]
        for i in range(len(boundaries) - 1):
            seg_start = boundaries[i]
            seg_end = boundaries[i + 1]
            if seg_end - seg_start >= min_split_duration:
                result.append(RawNoteEvent(
                    pitch_midi=note.pitch_midi,
                    start_sec=seg_start,
                    end_sec=seg_end,
                    confidence=note.confidence,
                ))

    result.sort(key=lambda n: (n.start_sec, n.pitch_midi))
    return result
