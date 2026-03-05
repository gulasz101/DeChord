from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import guitarpro


@dataclass(frozen=True)
class ReferenceNote:
    bar_index: int
    beat_position: float
    duration_beats: float
    pitch_midi: int
    string: int
    fret: int


@dataclass(frozen=True)
class ReferenceTab:
    tempo: int
    time_signature: tuple[int, int]
    bars: list[int]
    notes: list[ReferenceNote]
    track_name: str


def _duration_value_to_beats(value: int, *, dotted: bool) -> float:
    """Convert pyguitarpro duration.value to beats (quarter = 1.0)."""
    base = 4.0 / value
    if dotted:
        base *= 1.5
    return base


def _find_bass_track(song: guitarpro.Song) -> guitarpro.Track | None:
    for track in song.tracks:
        if len(track.strings) == 4:
            values = sorted(s.value for s in track.strings)
            if values == [28, 33, 38, 43]:
                return track
    for track in song.tracks:
        if "bass" in track.name.lower():
            return track
    return None


def parse_gp5_bass_track(
    gp5_path: Path,
    *,
    encoding: str | None = None,
) -> ReferenceTab:
    kwargs = {"encoding": encoding} if encoding else {}
    song = guitarpro.parse(str(gp5_path), **kwargs)

    bass_track = _find_bass_track(song)
    if bass_track is None:
        raise ValueError(f"No bass track found in {gp5_path.name}")

    string_midi: dict[int, int] = {}
    for s in bass_track.strings:
        string_midi[s.number] = s.value

    notes: list[ReferenceNote] = []
    bar_indices: list[int] = []

    for m_idx, measure in enumerate(bass_track.measures):
        bar_indices.append(m_idx)

        beat_position = 0.0
        for beat in measure.voices[0].beats:
            dur_beats = _duration_value_to_beats(
                beat.duration.value,
                dotted=beat.duration.isDotted,
            )
            for note in beat.notes:
                open_midi = string_midi.get(note.string, 0)
                pitch_midi = open_midi + note.value
                notes.append(
                    ReferenceNote(
                        bar_index=m_idx,
                        beat_position=round(beat_position, 6),
                        duration_beats=round(dur_beats, 6),
                        pitch_midi=pitch_midi,
                        string=note.string,
                        fret=note.value,
                    )
                )
            beat_position += dur_beats

    ts = song.measureHeaders[0].timeSignature
    return ReferenceTab(
        tempo=song.tempo,
        time_signature=(ts.numerator, ts.denominator.value),
        bars=bar_indices,
        notes=notes,
        track_name=bass_track.name,
    )
