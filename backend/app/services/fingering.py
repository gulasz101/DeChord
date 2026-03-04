from __future__ import annotations

from dataclasses import dataclass

from app.services.quantization import QuantizedNote

STANDARD_BASS_TUNING: dict[int, int] = {
    4: 40,  # E1
    3: 45,  # A1
    2: 50,  # D2
    1: 55,  # G2
}


@dataclass(frozen=True)
class FingeredNote:
    bar_index: int
    beat_position: float
    duration_beats: float
    pitch_midi: int
    start_sec: float
    end_sec: float
    string: int
    fret: int


def _candidates_for_pitch(pitch_midi: int, *, max_fret: int) -> list[tuple[int, int]]:
    candidates: list[tuple[int, int]] = []
    for string, open_note in STANDARD_BASS_TUNING.items():
        fret = pitch_midi - open_note
        if 0 <= fret <= max_fret:
            candidates.append((string, fret))
    candidates.sort(key=lambda item: (item[1], item[0]))
    return candidates


def _transition_cost(prev: tuple[int, int], current: tuple[int, int]) -> float:
    prev_string, prev_fret = prev
    string, fret = current

    fret_jump = abs(fret - prev_fret)
    string_change = abs(string - prev_string) * 1.25
    hand_shift = abs((fret // 4) - (prev_fret // 4)) * 0.5
    open_string_bonus = -0.1 if fret == 0 else 0.0
    return fret_jump + string_change + hand_shift + open_string_bonus


def optimize_fingering(notes: list[QuantizedNote], *, max_fret: int = 24) -> list[FingeredNote]:
    if not notes:
        return []

    note_candidates = [_candidates_for_pitch(note.pitch_midi, max_fret=max_fret) for note in notes]
    if any(not candidates for candidates in note_candidates):
        return []

    dp: list[dict[tuple[int, int], tuple[float, tuple[int, int] | None]]] = []
    first_layer: dict[tuple[int, int], tuple[float, tuple[int, int] | None]] = {}
    for candidate in note_candidates[0]:
        first_layer[candidate] = (candidate[1] * 0.1, None)
    dp.append(first_layer)

    for idx in range(1, len(notes)):
        layer: dict[tuple[int, int], tuple[float, tuple[int, int] | None]] = {}
        for candidate in note_candidates[idx]:
            best_cost = float("inf")
            best_prev: tuple[int, int] | None = None
            for prev_candidate, (prev_cost, _) in dp[idx - 1].items():
                cost = prev_cost + _transition_cost(prev_candidate, candidate)
                if cost < best_cost:
                    best_cost = cost
                    best_prev = prev_candidate
            layer[candidate] = (best_cost, best_prev)
        dp.append(layer)

    last_candidate = min(dp[-1].items(), key=lambda item: item[1][0])[0]

    sequence: list[tuple[int, int]] = [last_candidate]
    for idx in range(len(notes) - 1, 0, -1):
        _, prev = dp[idx][sequence[-1]]
        if prev is None:
            break
        sequence.append(prev)
    sequence.reverse()

    return [
        FingeredNote(
            bar_index=note.bar_index,
            beat_position=note.beat_position,
            duration_beats=note.duration_beats,
            pitch_midi=note.pitch_midi,
            start_sec=note.start_sec,
            end_sec=note.end_sec,
            string=position[0],
            fret=position[1],
        )
        for note, position in zip(notes, sequence)
    ]
