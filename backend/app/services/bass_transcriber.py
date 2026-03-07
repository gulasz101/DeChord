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
from app.services.pipeline_trace import build_stage_metrics

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


@dataclass(frozen=True)
class BasicPitchStageTrace:
    pitch_stabilized_notes: list[RawNoteEvent]
    admission_filtered_notes: list[RawNoteEvent]
    stats: dict[str, int]


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

        parsed_notes = self._parse_notes_fn(midi_bytes)
        corrections = 0
        intrusion_suppressions = 0
        merged_fragments = 0
        rejected_notes = 0
        pitch_stabilized_notes = list(parsed_notes)
        admission_filtered_notes = list(parsed_notes)
        if engine == "basic_pitch" and parsed_notes:
            pitch_config = _get_pitch_stability_config()
            stage_trace = _trace_basicpitch_stages(parsed_notes, pitch_config)
            pitch_stabilized_notes = list(stage_trace.pitch_stabilized_notes)
            admission_filtered_notes = list(stage_trace.admission_filtered_notes)
            stability_stats = stage_trace.stats
            corrections = int(stability_stats["octave_corrections_applied"])
            intrusion_suppressions = int(stability_stats["suppressed_short_intrusions"])
            merged_fragments = int(stability_stats["merged_fragments"])
            rejected_notes = int(stability_stats["rejected_notes"])
        else:
            pitch_config = _get_pitch_stability_config()
        debug_info["basicpitch_octave_corrections_applied"] = int(corrections)
        debug_info["basicpitch_short_intrusions_suppressed"] = int(intrusion_suppressions)
        debug_info["basicpitch_fragments_merged"] = int(merged_fragments)
        debug_info["basicpitch_rejected_notes"] = int(rejected_notes)
        debug_info["pipeline_trace"] = {
            "pipeline_stats": {
                "basic_pitch_raw": build_stage_metrics(
                    parsed_notes,
                    short_note_threshold_ms=pitch_config.note_min_duration_ms,
                ),
                "pitch_stabilized": build_stage_metrics(
                    pitch_stabilized_notes,
                    previous_notes=parsed_notes,
                    short_note_threshold_ms=pitch_config.note_min_duration_ms,
                ),
                "admission_filtered": build_stage_metrics(
                    admission_filtered_notes,
                    previous_notes=pitch_stabilized_notes,
                    short_note_threshold_ms=pitch_config.note_min_duration_ms,
                    merged_count=merged_fragments,
                ),
            }
        }
        return BassTranscriptionResult(
            engine=engine,
            midi_bytes=midi_bytes,
            raw_notes=admission_filtered_notes,
            debug_info=debug_info,
        )


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


def _note_duration_sec(note: RawNoteEvent) -> float:
    return max(0.0, float(note.end_sec) - float(note.start_sec))


def _is_octave_related(pitch_a: int, pitch_b: int) -> bool:
    return abs(int(pitch_a) - int(pitch_b)) == 12


def _has_continuity_support(
    prev_note: RawNoteEvent | None,
    note: RawNoteEvent,
    next_note: RawNoteEvent | None,
    *,
    merge_gap_sec: float,
) -> bool:
    for neighbor in (prev_note, next_note):
        if neighbor is None:
            continue
        gap = min(
            abs(float(note.start_sec) - float(neighbor.end_sec)),
            abs(float(neighbor.start_sec) - float(note.end_sec)),
        )
        if gap <= merge_gap_sec and abs(int(neighbor.pitch_midi) - int(note.pitch_midi)) <= 2:
            return True
    return False


def _looks_like_repeated_pluck(
    left_note: RawNoteEvent,
    right_note: RawNoteEvent,
    *,
    gap_sec: float,
    merge_gap_sec: float,
) -> bool:
    if left_note.pitch_midi != right_note.pitch_midi:
        return False
    left_duration = _note_duration_sec(left_note)
    right_duration = _note_duration_sec(right_note)
    return (
        gap_sec >= min(0.03, merge_gap_sec)
        and left_duration <= 0.18
        and right_duration <= 0.18
        and min(left_note.confidence, right_note.confidence) >= 0.9
    )


def _should_suppress_intrusion(
    prev_note: RawNoteEvent,
    note: RawNoteEvent,
    next_note: RawNoteEvent,
    *,
    min_duration_sec: float,
    octave_intrusion_max_sec: float,
    merge_gap_sec: float,
    low_conf_threshold: float,
) -> bool:
    note_duration = _note_duration_sec(note)
    if note_duration > max(min_duration_sec, octave_intrusion_max_sec):
        return False
    if (float(note.start_sec) - float(prev_note.end_sec)) > merge_gap_sec:
        return False
    if (float(next_note.start_sec) - float(note.end_sec)) > merge_gap_sec:
        return False
    same_pitch_neighbors = prev_note.pitch_midi == next_note.pitch_midi
    near_same_neighbors = abs(prev_note.pitch_midi - next_note.pitch_midi) <= 1
    if not (same_pitch_neighbors or near_same_neighbors):
        return False
    if note.pitch_midi == prev_note.pitch_midi:
        return False
    octave_intrusion = _is_octave_related(note.pitch_midi, prev_note.pitch_midi) or _is_octave_related(
        note.pitch_midi,
        next_note.pitch_midi,
    )
    weaker_than_neighbors = note.confidence <= (min(prev_note.confidence, next_note.confidence) - 0.08)
    weak_intrusion = note.confidence <= max(low_conf_threshold, min(prev_note.confidence, next_note.confidence) - 0.2)
    return octave_intrusion or weak_intrusion or (same_pitch_neighbors and weaker_than_neighbors)


def _should_reject_note(
    prev_note: RawNoteEvent | None,
    note: RawNoteEvent,
    next_note: RawNoteEvent | None,
    *,
    min_duration_sec: float,
    merge_gap_sec: float,
    low_conf_threshold: float,
) -> bool:
    duration_sec = _note_duration_sec(note)
    if duration_sec > min_duration_sec:
        return False
    if note.confidence > low_conf_threshold:
        return False
    return not _has_continuity_support(prev_note, note, next_note, merge_gap_sec=merge_gap_sec)


def _merge_fragmented_same_pitch_notes(
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
        gap_sec = max(0.0, float(note.start_sec) - float(last.end_sec))
        if (
            note.pitch_midi == last.pitch_midi
            and gap_sec <= merge_gap_sec
            and not _looks_like_repeated_pluck(last, note, gap_sec=gap_sec, merge_gap_sec=merge_gap_sec)
        ):
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


def _trace_basicpitch_stages(
    notes: list[RawNoteEvent],
    config: PitchStabilityConfig,
) -> BasicPitchStageTrace:
    ordered = sorted(notes, key=lambda event: (event.start_sec, event.end_sec, event.pitch_midi))
    if not config.pitch_stability_enable:
        corrected, corrections = _conservative_basicpitch_octave_stabilization(ordered)
        return BasicPitchStageTrace(
            pitch_stabilized_notes=corrected,
            admission_filtered_notes=corrected,
            stats={
                "octave_corrections_applied": int(corrections),
                "suppressed_short_intrusions": 0,
                "merged_fragments": 0,
                "rejected_notes": 0,
            },
        )

    min_duration_sec = max(config.note_min_duration_ms / 1000.0, 0.04)
    merge_gap_sec = max(config.note_merge_gap_ms / 1000.0, 0.0)
    octave_intrusion_max_sec = max(config.note_octave_intrusion_max_duration_ms / 1000.0, min_duration_sec)
    working = list(ordered)
    suppressed_short_intrusions = 0
    idx = 1
    while idx < len(working) - 1:
        prev_note = working[idx - 1]
        cur_note = working[idx]
        next_note = working[idx + 1]
        if _should_suppress_intrusion(
            prev_note,
            cur_note,
            next_note,
            min_duration_sec=min_duration_sec,
            octave_intrusion_max_sec=octave_intrusion_max_sec,
            merge_gap_sec=merge_gap_sec,
            low_conf_threshold=config.note_low_confidence_threshold,
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

    corrected, octave_corrections = _conservative_basicpitch_octave_stabilization(working)
    if len(corrected) < 2:
        rejected_notes = 0
        admission_filtered_notes = corrected
        if config.note_admission_enable and corrected:
            note = corrected[0]
            if _note_duration_sec(note) <= min_duration_sec and note.confidence <= config.note_low_confidence_threshold:
                admission_filtered_notes = []
                rejected_notes = 1
        return BasicPitchStageTrace(
            pitch_stabilized_notes=corrected,
            admission_filtered_notes=admission_filtered_notes,
            stats={
                "octave_corrections_applied": int(octave_corrections),
                "suppressed_short_intrusions": int(suppressed_short_intrusions),
                "merged_fragments": 0,
                "rejected_notes": int(rejected_notes),
            },
        )

    if config.note_admission_enable:
        filtered: list[RawNoteEvent] = []
        rejected_notes = 0
        for idx, note in enumerate(corrected):
            prev_note = corrected[idx - 1] if idx > 0 else None
            next_note = corrected[idx + 1] if idx + 1 < len(corrected) else None
            if _should_reject_note(
                prev_note,
                note,
                next_note,
                min_duration_sec=min_duration_sec,
                merge_gap_sec=merge_gap_sec,
                low_conf_threshold=config.note_low_confidence_threshold,
            ):
                rejected_notes += 1
                continue
            filtered.append(note)
    else:
        filtered = corrected
        rejected_notes = 0

    merged, merged_fragments = _merge_fragmented_same_pitch_notes(filtered, merge_gap_sec=merge_gap_sec)
    return BasicPitchStageTrace(
        pitch_stabilized_notes=corrected,
        admission_filtered_notes=merged,
        stats={
            "octave_corrections_applied": int(octave_corrections),
            "suppressed_short_intrusions": int(suppressed_short_intrusions),
            "merged_fragments": int(merged_fragments),
            "rejected_notes": int(rejected_notes),
        },
    )
