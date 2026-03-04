from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Callable, Protocol

import mido

from app.midi import transcribe_bass_stem_to_midi

MidiTranscribeFn = Callable[[Path], bytes]
ParseNotesFn = Callable[[bytes], list["RawNoteEvent"]]


@dataclass(frozen=True)
class RawNoteEvent:
    pitch_midi: int
    start_sec: float
    end_sec: float
    confidence: float


@dataclass(frozen=True)
class BassTranscriptionResult:
    engine: str
    midi_bytes: bytes
    raw_notes: list[RawNoteEvent]


class BassTranscriber(Protocol):
    def transcribe(self, bass_wav: Path) -> BassTranscriptionResult: ...


def parse_midi_to_raw_notes(midi_bytes: bytes) -> list[RawNoteEvent]:
    midi = mido.MidiFile(file=BytesIO(midi_bytes))
    tempo = 500000
    abs_seconds = 0.0
    active: dict[int, float] = {}
    events: list[RawNoteEvent] = []

    for msg in mido.merge_tracks(midi.tracks):
        abs_seconds += mido.tick2second(msg.time, midi.ticks_per_beat, tempo)
        if msg.type == "set_tempo":
            tempo = msg.tempo
            continue
        if msg.type == "note_on" and msg.velocity > 0:
            active[msg.note] = abs_seconds
            continue
        if msg.type not in ("note_off", "note_on"):
            continue

        start = active.pop(msg.note, None)
        if start is None:
            continue
        end = max(abs_seconds, start + 0.05)
        events.append(
            RawNoteEvent(
                pitch_midi=int(msg.note),
                start_sec=float(start),
                end_sec=float(end),
                confidence=1.0,
            )
        )

    events.sort(key=lambda event: (event.start_sec, event.pitch_midi))
    return events


class BasicPitchTranscriber:
    def __init__(
        self,
        *,
        midi_transcribe_fn: MidiTranscribeFn | None = None,
        parse_notes_fn: ParseNotesFn | None = None,
    ) -> None:
        self._midi_transcribe_fn = midi_transcribe_fn or transcribe_bass_stem_to_midi
        self._parse_notes_fn = parse_notes_fn or parse_midi_to_raw_notes

    def transcribe(self, bass_wav: Path) -> BassTranscriptionResult:
        midi_bytes = self._midi_transcribe_fn(bass_wav)
        if not midi_bytes:
            raise RuntimeError("Bass MIDI transcription failed: generated MIDI is empty")

        raw_notes = self._parse_notes_fn(midi_bytes)
        return BassTranscriptionResult(engine="basic_pitch", midi_bytes=midi_bytes, raw_notes=raw_notes)
