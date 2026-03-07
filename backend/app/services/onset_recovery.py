from __future__ import annotations

from app.services.bass_transcriber import RawNoteEvent


def recovery_params_for_bpm(bpm: float) -> dict[str, float]:
    bpm = max(float(bpm), 1.0)
    sixteenth = 60.0 / bpm / 4.0
    return {
        "min_split_duration": max(0.05, sixteenth * 0.35),
        "onset_tolerance": max(0.02, sixteenth * 0.15),
    }


def recover_missing_onsets(
    notes: list[RawNoteEvent],
    onset_times: list[float],
    *,
    min_split_duration: float,
    onset_tolerance: float,
) -> tuple[list[RawNoteEvent], set[float], int]:
    if not notes or not onset_times:
        return list(notes), set(), 0

    sorted_onsets = sorted(onset_times)
    result: list[RawNoteEvent] = []
    split_starts: set[float] = set()
    split_count = 0

    for note in notes:
        interior_onsets = [
            t for t in sorted_onsets if note.start_sec + onset_tolerance < t < note.end_sec - min_split_duration
        ]

        if not interior_onsets:
            result.append(note)
            continue

        boundaries = [note.start_sec] + interior_onsets + [note.end_sec]
        for index in range(len(boundaries) - 1):
            seg_start = boundaries[index]
            seg_end = boundaries[index + 1]
            if seg_end - seg_start < min_split_duration:
                continue
            if index > 0:
                split_starts.add(round(seg_start, 6))
            result.append(
                RawNoteEvent(
                    pitch_midi=note.pitch_midi,
                    start_sec=seg_start,
                    end_sec=seg_end,
                    confidence=note.confidence,
                )
            )
        split_count += len(interior_onsets)

    result.sort(key=lambda event: (event.start_sec, event.pitch_midi))
    return result, split_starts, split_count
