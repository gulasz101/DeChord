from __future__ import annotations

from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
from typing import Callable, Protocol
import statistics

import mido

from app.midi import MidiTranscriptionResult
from app.midi import PitchStabilityConfig, _get_pitch_stability_config
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
        intrusion_suppressions = 0
        merged_fragments = 0
        if engine == "basic_pitch" and raw_notes:
            pitch_config = _get_pitch_stability_config()
            raw_notes, stability_stats = _stabilize_basicpitch_notes(raw_notes, pitch_config)
            corrections = int(stability_stats["octave_corrections_applied"])
            intrusion_suppressions = int(stability_stats["suppressed_short_intrusions"])
            merged_fragments = int(stability_stats["merged_fragments"])
        debug_info["basicpitch_octave_corrections_applied"] = int(corrections)
        debug_info["basicpitch_short_intrusions_suppressed"] = int(intrusion_suppressions)
        debug_info["basicpitch_fragments_merged"] = int(merged_fragments)
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


def _merge_same_pitch_gaps(
    notes: list[RawNoteEvent],
    *,
    merge_gap_sec: float,
) -> tuple[list[RawNoteEvent], int]:
    if not notes:
        return [], 0
    merged = [notes[0]]
    merge_count = 0
    for note in notes[1:]:
        last = merged[-1]
        if note.pitch_midi == last.pitch_midi and 0.0 <= (note.start_sec - last.end_sec) <= merge_gap_sec:
            merged[-1] = RawNoteEvent(
                pitch_midi=last.pitch_midi,
                start_sec=last.start_sec,
                end_sec=max(last.end_sec, note.end_sec),
                confidence=max(last.confidence, note.confidence),
            )
            merge_count += 1
            continue
        merged.append(note)
    return merged, merge_count


def _stabilize_basicpitch_notes(
    notes: list[RawNoteEvent],
    config: PitchStabilityConfig,
) -> tuple[list[RawNoteEvent], dict[str, int]]:
    ordered = sorted(notes, key=lambda event: (event.start_sec, event.end_sec, event.pitch_midi))
    if not config.pitch_stability_enable or len(ordered) < 2:
        corrected, corrections = _conservative_basicpitch_octave_stabilization(ordered)
        return corrected, {
            "octave_corrections_applied": int(corrections),
            "suppressed_short_intrusions": 0,
            "merged_fragments": 0,
        }

    min_duration_sec = max(config.pitch_min_note_duration_ms / 1000.0, 0.04)
    merge_gap_sec = max(config.pitch_merge_gap_ms / 1000.0, 0.0)
    corrected, octave_corrections = _conservative_basicpitch_octave_stabilization(ordered)

    working = list(corrected)
    suppressed_short_intrusions = 0
    idx = 1
    while idx < len(working) - 1:
        prev_note = working[idx - 1]
        cur_note = working[idx]
        next_note = working[idx + 1]
        cur_duration = cur_note.end_sec - cur_note.start_sec
        if (
            cur_duration <= min_duration_sec
            and prev_note.pitch_midi == next_note.pitch_midi
            and prev_note.pitch_midi != cur_note.pitch_midi
            and abs(cur_note.pitch_midi - prev_note.pitch_midi) <= 12
            and (cur_note.start_sec - prev_note.end_sec) <= merge_gap_sec
            and (next_note.start_sec - cur_note.end_sec) <= merge_gap_sec
        ):
            working[idx - 1] = RawNoteEvent(
                pitch_midi=prev_note.pitch_midi,
                start_sec=prev_note.start_sec,
                end_sec=next_note.end_sec,
                confidence=max(prev_note.confidence, cur_note.confidence, next_note.confidence),
            )
            del working[idx:idx + 2]
            suppressed_short_intrusions += 1
            idx = max(1, idx - 1)
            continue
        idx += 1

    merged, merged_fragments = _merge_same_pitch_gaps(working, merge_gap_sec=merge_gap_sec)
    return merged, {
        "octave_corrections_applied": int(octave_corrections),
        "suppressed_short_intrusions": int(suppressed_short_intrusions),
        "merged_fragments": int(merged_fragments),
    }
