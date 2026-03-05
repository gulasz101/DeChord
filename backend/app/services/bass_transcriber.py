from __future__ import annotations

from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
from typing import Callable, Protocol
import statistics

import mido

from app.midi import MidiTranscriptionResult
from app.midi import transcribe_bass_stem_to_midi

MidiTranscribeFn = Callable[[Path], bytes | MidiTranscriptionResult]
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
    debug_info: dict[str, object] = field(default_factory=dict)


class BassTranscriber(Protocol):
    def transcribe(self, bass_wav: Path, **kwargs) -> BassTranscriptionResult: ...


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

    def transcribe(self, bass_wav: Path, **kwargs) -> BassTranscriptionResult:
        raw_midi_result = self._midi_transcribe_fn(bass_wav)
        if isinstance(raw_midi_result, MidiTranscriptionResult):
            midi_bytes = raw_midi_result.midi_bytes
            engine = raw_midi_result.engine_used
            debug_info = dict(raw_midi_result.diagnostics)
        else:
            midi_bytes = raw_midi_result
            engine = "basic_pitch"
            debug_info = {"transcription_engine_used": "basic_pitch"}

        if not midi_bytes:
            raise RuntimeError("Bass MIDI transcription failed: generated MIDI is empty")

        raw_notes = self._parse_notes_fn(midi_bytes)
        corrections = 0
        if engine == "basic_pitch" and raw_notes:
            raw_notes, corrections = _conservative_basicpitch_octave_stabilization(raw_notes)
        debug_info["basicpitch_octave_corrections_applied"] = int(corrections)
        return BassTranscriptionResult(engine=engine, midi_bytes=midi_bytes, raw_notes=raw_notes, debug_info=debug_info)


def _conservative_basicpitch_octave_stabilization(
    notes: list[RawNoteEvent],
) -> tuple[list[RawNoteEvent], int]:
    if len(notes) < 3:
        return notes, 0

    ordered = sorted(notes, key=lambda event: (event.start_sec, event.end_sec, event.pitch_midi))
    corrected = list(ordered)
    corrections = 0

    for idx in range(1, len(corrected) - 1):
        prev_note = corrected[idx - 1]
        cur_note = corrected[idx]
        next_note = corrected[idx + 1]

        if cur_note.confidence < 0.4:
            continue
        if prev_note.confidence < 0.5 or next_note.confidence < 0.5:
            continue

        neighbor_median = int(round(statistics.median([prev_note.pitch_midi, next_note.pitch_midi])))
        delta = cur_note.pitch_midi - neighbor_median
        if abs(delta) != 12:
            continue

        candidate_pitch = int(cur_note.pitch_midi - 12 if delta > 0 else cur_note.pitch_midi + 12)
        if candidate_pitch < 28 or candidate_pitch > 64:
            continue

        # Guardrail: only touch notes strongly supported by both adjacent notes.
        if abs(candidate_pitch - prev_note.pitch_midi) > 3 or abs(candidate_pitch - next_note.pitch_midi) > 3:
            continue
        # Guardrail: keep true large leaps when neighbors also indicate wide interval.
        if abs(prev_note.pitch_midi - next_note.pitch_midi) > 6:
            continue

        corrected[idx] = RawNoteEvent(
            pitch_midi=candidate_pitch,
            start_sec=cur_note.start_sec,
            end_sec=cur_note.end_sec,
            confidence=cur_note.confidence,
        )
        corrections += 1

    return corrected, corrections
