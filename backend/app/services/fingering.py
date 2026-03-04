from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from app.services.quantization import QuantizedNote

STANDARD_BASS_TUNING_MIDI: dict[int, int] = {
    4: 28,  # E1
    3: 33,  # A1
    2: 38,  # D2
    1: 43,  # G2
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


@dataclass(frozen=True)
class FingeringDebugInfo:
    dropped_reasons: dict[str, int]
    dropped_note_count: int
    playable_note_count: int
    input_note_count: int
    octave_salvage_enabled: bool
    octave_salvaged_notes: int
    tuning_midi: dict[int, int]
    max_fret: int


def _candidates_for_pitch(pitch_midi: int, *, max_fret: int) -> list[tuple[int, int]]:
    candidates: list[tuple[int, int]] = []
    for string, open_note in STANDARD_BASS_TUNING_MIDI.items():
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


def _solve_candidates(note_candidates: list[list[tuple[int, int]]]) -> list[tuple[int, int]]:
    if not note_candidates:
        return []

    dp: list[dict[tuple[int, int], tuple[float, tuple[int, int] | None]]] = []
    first_layer: dict[tuple[int, int], tuple[float, tuple[int, int] | None]] = {}
    for candidate in sorted(note_candidates[0], key=lambda item: (item[1], item[0])):
        first_layer[candidate] = (candidate[1] * 0.1, None)
    dp.append(first_layer)

    for idx in range(1, len(note_candidates)):
        layer: dict[tuple[int, int], tuple[float, tuple[int, int] | None]] = {}
        for candidate in sorted(note_candidates[idx], key=lambda item: (item[1], item[0])):
            best_cost = float("inf")
            best_prev: tuple[int, int] | None = None
            for prev_candidate in sorted(dp[idx - 1]):
                prev_cost, _ = dp[idx - 1][prev_candidate]
                cost = prev_cost + _transition_cost(prev_candidate, candidate)
                if cost < best_cost:
                    best_cost = cost
                    best_prev = prev_candidate
            layer[candidate] = (best_cost, best_prev)
        dp.append(layer)

    last_candidate = min(dp[-1], key=lambda candidate: (dp[-1][candidate][0], candidate[1], candidate[0]))

    sequence: list[tuple[int, int]] = [last_candidate]
    for idx in range(len(note_candidates) - 1, 0, -1):
        _, prev = dp[idx][sequence[-1]]
        if prev is None:
            break
        sequence.append(prev)
    sequence.reverse()
    return sequence


def optimize_fingering_with_debug(notes: list[QuantizedNote], *, max_fret: int = 24) -> tuple[list[FingeredNote], dict[str, object]]:
    if not notes:
        debug_info = FingeringDebugInfo(
            dropped_reasons={},
            dropped_note_count=0,
            playable_note_count=0,
            input_note_count=0,
            octave_salvage_enabled=False,
            octave_salvaged_notes=0,
            tuning_midi=dict(STANDARD_BASS_TUNING_MIDI),
            max_fret=max_fret,
        )
        return [], debug_info.__dict__.copy()

    dropped_reasons: Counter[str] = Counter()
    playable_notes: list[QuantizedNote] = []
    playable_candidates: list[list[tuple[int, int]]] = []

    for note in notes:
        candidates = _candidates_for_pitch(note.pitch_midi, max_fret=max_fret)
        if not candidates:
            dropped_reasons["no_fingering_candidate"] += 1
            continue
        playable_notes.append(note)
        playable_candidates.append(candidates)

    sequence = _solve_candidates(playable_candidates)
    fingered_notes = [
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
        for note, position in zip(playable_notes, sequence)
    ]
    debug_info = FingeringDebugInfo(
        dropped_reasons=dict(dropped_reasons),
        dropped_note_count=len(notes) - len(playable_notes),
        playable_note_count=len(playable_notes),
        input_note_count=len(notes),
        octave_salvage_enabled=False,
        octave_salvaged_notes=0,
        tuning_midi=dict(STANDARD_BASS_TUNING_MIDI),
        max_fret=max_fret,
    )
    return fingered_notes, debug_info.__dict__.copy()


def optimize_fingering(notes: list[QuantizedNote], *, max_fret: int = 24) -> list[FingeredNote]:
    fingered_notes, _ = optimize_fingering_with_debug(notes, max_fret=max_fret)
    return fingered_notes
