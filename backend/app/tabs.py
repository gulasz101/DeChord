from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Callable

import mido

ParseMidiFn = Callable[[bytes], list["MidiNoteEvent"]]

EADG_OPEN_NOTES: dict[int, int] = {
    4: 40,  # E1
    3: 45,  # A1
    2: 50,  # D2
    1: 55,  # G2
}
MAX_FRET = 24
MEASURE_BEATS = 4.0
TICKS_PER_QUARTER = 960


@dataclass(frozen=True)
class MidiNoteEvent:
    note: int
    start: float
    end: float


@dataclass(frozen=True)
class TabNote:
    string: int
    fret: int
    start: float
    end: float
    midi_note: int


def _parse_midi_events(midi_bytes: bytes) -> list[MidiNoteEvent]:
    midi = mido.MidiFile(file=BytesIO(midi_bytes))
    ticks_per_beat = midi.ticks_per_beat
    tempo = 500000
    abs_ticks = 0
    abs_seconds = 0.0
    active: dict[int, float] = {}
    events: list[MidiNoteEvent] = []

    for msg in mido.merge_tracks(midi.tracks):
        abs_ticks += msg.time
        abs_seconds += mido.tick2second(msg.time, ticks_per_beat, tempo)

        if msg.type == "set_tempo":
            tempo = msg.tempo
            continue

        if msg.type == "note_on" and msg.velocity > 0:
            active[msg.note] = abs_seconds
            continue

        if msg.type in ("note_off", "note_on"):
            if msg.type == "note_on" and msg.velocity > 0:
                continue
            start = active.pop(msg.note, None)
            if start is None:
                continue
            end = max(abs_seconds, start + 0.05)
            events.append(MidiNoteEvent(note=msg.note, start=start, end=end))

    events.sort(key=lambda event: (event.start, event.note))
    return events


def _pick_best_position(note: int, previous: TabNote | None) -> tuple[int, int] | None:
    candidates: list[tuple[int, int]] = []
    for string, open_note in EADG_OPEN_NOTES.items():
        fret = note - open_note
        if 0 <= fret <= MAX_FRET:
            candidates.append((string, fret))

    if not candidates:
        return None

    if previous is None:
        return min(candidates, key=lambda item: (item[1], item[0]))

    def score(candidate: tuple[int, int]) -> tuple[float, int, int]:
        string, fret = candidate
        movement = abs(fret - previous.fret) + (abs(string - previous.string) * 0.5)
        return (movement, fret, string)

    return min(candidates, key=score)


def map_midi_to_eadg_positions(
    midi_bytes: bytes,
    *,
    parse_midi_fn: ParseMidiFn | None = None,
) -> list[TabNote]:
    events = (parse_midi_fn or _parse_midi_events)(midi_bytes)
    tab_notes: list[TabNote] = []
    previous: TabNote | None = None

    for event in events:
        selected = _pick_best_position(event.note, previous)
        if selected is None:
            continue
        string, fret = selected
        tab_note = TabNote(
            string=string,
            fret=fret,
            start=event.start,
            end=event.end,
            midi_note=event.note,
        )
        tab_notes.append(tab_note)
        previous = tab_note

    return tab_notes


def _duration_value(note: TabNote) -> int:
    length = max(note.end - note.start, 0.05)
    if length >= 0.9:
        return 4
    if length >= 0.45:
        return 8
    return 16


def _duration_in_quarter_beats(duration_value: int) -> float:
    if duration_value == 1:
        return 4.0
    if duration_value == 2:
        return 2.0
    if duration_value == 4:
        return 1.0
    if duration_value == 8:
        return 0.5
    return 0.25


def build_gp5_from_tab_positions(tab_notes: list[TabNote]) -> bytes:
    import guitarpro
    from guitarpro import models

    song = models.Song()
    track = song.tracks[0]
    track.name = "Bass"
    track.fretCount = MAX_FRET
    track.strings = [
        models.GuitarString(1, EADG_OPEN_NOTES[1]),
        models.GuitarString(2, EADG_OPEN_NOTES[2]),
        models.GuitarString(3, EADG_OPEN_NOTES[3]),
        models.GuitarString(4, EADG_OPEN_NOTES[4]),
    ]
    current_measure = track.measures[0]
    current_voice = current_measure.voices[0]
    used_beats = 0.0
    measure_number = 1
    header_start = song.measureHeaders[0].start

    for tab_note in tab_notes:
        duration_value = _duration_value(tab_note)
        duration_beats = _duration_in_quarter_beats(duration_value)

        if used_beats + duration_beats > MEASURE_BEATS:
            measure_number += 1
            header_start += int(TICKS_PER_QUARTER * MEASURE_BEATS)
            header = models.MeasureHeader(
                number=measure_number,
                start=header_start,
            )
            song.measureHeaders.append(header)
            current_measure = models.Measure(track=track, header=header)
            track.measures.append(current_measure)
            current_voice = current_measure.voices[0]
            used_beats = 0.0

        beat = models.Beat(
            voice=current_voice,
            duration=models.Duration(value=duration_value),
            status=models.BeatStatus.normal,
        )
        current_voice.beats.append(beat)
        note = models.Note(
            beat=beat,
            value=tab_note.fret,
            string=tab_note.string,
            type=models.NoteType.normal,
        )
        beat.notes.append(note)
        used_beats += duration_beats

    with TemporaryDirectory(prefix="dechord-gp5-") as tmp_dir:
        output = Path(tmp_dir) / "tab.gp5"
        guitarpro.write(song, output)
        return output.read_bytes()
