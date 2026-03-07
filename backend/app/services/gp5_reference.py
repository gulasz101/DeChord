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
class ReferenceBar:
    index: int


@dataclass(frozen=True)
class ReferenceTab:
    tempo: float
    time_signature: tuple[int, int]
    bars: list[ReferenceBar]
    notes: list[ReferenceNote]


def _duration_to_beats(duration) -> float:
    base_beats = 4.0 / float(duration.value)
    if duration.isDotted:
        base_beats *= 1.5
    if getattr(duration, "isDoubleDotted", False):
        base_beats *= 1.75

    tuplet = duration.tuplet
    if tuplet and tuplet.enters:
        base_beats *= float(tuplet.times) / float(tuplet.enters)
    return base_beats


def _select_bass_track(song) -> object:
    for track in song.tracks:
        if track.isPercussionTrack:
            continue
        if "bass" in track.name.lower() and len(track.strings) >= 4:
            return track

    # Fallback: select lowest 4-string track by tuning
    candidates = [track for track in song.tracks if not track.isPercussionTrack and len(track.strings) >= 4]
    if not candidates:
        raise RuntimeError("No suitable non-percussion track found in GP5 file")

    candidates.sort(key=lambda track: min(s.value for s in track.strings))
    return candidates[0]


def parse_gp5_bass_track(path: Path, encoding: str | None = None) -> ReferenceTab:
    gp_song = guitarpro.parse(str(path), encoding=encoding or "cp1252")
    bass_track = _select_bass_track(gp_song)

    tempo = float(gp_song.tempo)
    first_measure = bass_track.measures[0]
    numerator = int(first_measure.timeSignature.numerator)
    denominator = int(first_measure.timeSignature.denominator.value)

    ticks_per_quarter = 960.0
    bars = [ReferenceBar(index=i) for i, _ in enumerate(bass_track.measures)]
    notes: list[ReferenceNote] = []

    for bar_index, measure in enumerate(bass_track.measures):
        measure_start = float(measure.start)
        for voice in measure.voices:
            for beat in voice.beats:
                beat_position = (float(beat.start) - measure_start) / ticks_per_quarter
                duration_beats = _duration_to_beats(beat.duration)
                for note in beat.notes:
                    if note.type.name.lower() == "rest":
                        continue
                    string_idx = int(note.string)
                    open_midi = bass_track.strings[string_idx - 1].value
                    fret = int(note.value)
                    pitch_midi = int(open_midi + fret)
                    notes.append(
                        ReferenceNote(
                            bar_index=bar_index,
                            beat_position=max(0.0, beat_position),
                            duration_beats=duration_beats,
                            pitch_midi=pitch_midi,
                            string=string_idx,
                            fret=fret,
                        )
                    )

    notes.sort(key=lambda item: (item.bar_index, item.beat_position, item.pitch_midi, item.string, item.fret))

    return ReferenceTab(
        tempo=tempo,
        time_signature=(numerator, denominator),
        bars=bars,
        notes=notes,
    )
