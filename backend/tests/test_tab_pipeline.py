from __future__ import annotations

from pathlib import Path

import pytest

from app.services.alphatex_exporter import SyncPoint
from app.services.bass_transcriber import BassTranscriptionResult, RawNoteEvent
from app.services.fingering import FingeredNote
from app.services.quantization import QuantizedNote
from app.services.rhythm_grid import Bar
from app.services.tab_pipeline import FingeringCollapseError, TabPipeline


def test_tab_pipeline_composes_all_stages_and_exposes_debug_info() -> None:
    raw_notes = [RawNoteEvent(pitch_midi=40, start_sec=0.0, end_sec=0.5, confidence=0.9)]

    class FakeTranscriber:
        def transcribe(self, _bass_wav: Path) -> BassTranscriptionResult:
            return BassTranscriptionResult(engine="basic_pitch", midi_bytes=b"MThd", raw_notes=raw_notes)

    bars = [Bar(index=0, start_sec=0.0, end_sec=2.0, beats_sec=[0.0, 0.5, 1.0, 1.5])]

    pipeline = TabPipeline(
        transcriber=FakeTranscriber(),
        rhythm_extract_fn=lambda _drums, **_kwargs: ([0.0, 0.5, 1.0, 1.5], [0.0], "madmom"),
        bar_builder_fn=lambda _beats, _downbeats, **_kwargs: bars,
        cleanup_fn=lambda events, **_kwargs: events,
        quantize_fn=lambda events, _grid, **_kwargs: [
            QuantizedNote(
                bar_index=0,
                beat_position=0.0,
                duration_beats=1.0,
                pitch_midi=40,
                start_sec=0.0,
                end_sec=0.5,
            )
        ],
        fingering_fn=lambda notes, **_kwargs: [
            FingeredNote(
                bar_index=0,
                beat_position=0.0,
                duration_beats=1.0,
                pitch_midi=40,
                start_sec=0.0,
                end_sec=0.5,
                string=4,
                fret=0,
            )
        ],
        export_fn=lambda notes, bars, **_kwargs: ("\\tempo 120", [SyncPoint(bar_index=0, millisecond_offset=0)]),
    )

    result = pipeline.run(Path("bass.wav"), Path("drums.wav"), bpm_hint=120.0)

    assert result.alphatex.startswith("\\tempo")
    assert result.tempo_used == 120.0
    assert result.midi_bytes == b"MThd"
    assert result.debug_info["rhythm_source"] == "madmom"
    assert result.debug_info["raw_note_count"] == 1
    assert result.debug_info["quantized_note_count"] == 1
    assert result.sync_points[0].bar_index == 0


def test_tab_pipeline_drops_only_unplayable_notes_and_surfaces_fingering_debug() -> None:
    raw_notes = [RawNoteEvent(pitch_midi=40, start_sec=0.0, end_sec=0.5, confidence=0.9)]

    class FakeTranscriber:
        def transcribe(self, _bass_wav: Path) -> BassTranscriptionResult:
            return BassTranscriptionResult(engine="basic_pitch", midi_bytes=b"MThd", raw_notes=raw_notes)

    bars = [Bar(index=0, start_sec=0.0, end_sec=2.0, beats_sec=[0.0, 0.5, 1.0, 1.5])]
    exported_notes: list[FingeredNote] = []

    def fake_export(notes, _bars, **_kwargs):
        exported_notes.extend(notes)
        return ("\\tempo 120", [SyncPoint(bar_index=0, millisecond_offset=0)])

    pipeline = TabPipeline(
        transcriber=FakeTranscriber(),
        rhythm_extract_fn=lambda _drums, **_kwargs: ([0.0, 0.5, 1.0, 1.5], [0.0], "madmom"),
        bar_builder_fn=lambda _beats, _downbeats, **_kwargs: bars,
        cleanup_fn=lambda events, **_kwargs: events,
        quantize_fn=lambda events, _grid, **_kwargs: [
            QuantizedNote(
                bar_index=0,
                beat_position=0.0,
                duration_beats=1.0,
                pitch_midi=40,
                start_sec=0.0,
                end_sec=0.5,
            ),
            QuantizedNote(
                bar_index=0,
                beat_position=1.0,
                duration_beats=1.0,
                pitch_midi=20,
                start_sec=0.5,
                end_sec=1.0,
            ),
            QuantizedNote(
                bar_index=0,
                beat_position=2.0,
                duration_beats=1.0,
                pitch_midi=45,
                start_sec=1.0,
                end_sec=1.5,
            ),
        ],
        export_fn=fake_export,
    )

    result = pipeline.run(Path("bass.wav"), Path("drums.wav"), bpm_hint=120.0)

    assert [note.pitch_midi for note in exported_notes] == [40, 45]
    assert result.debug_info["quantized_note_count"] == 3
    assert result.debug_info["fingered_note_count"] == 2
    assert result.debug_info["fingering"]["dropped_reasons"] == {"no_fingering_candidate": 1}
    assert result.debug_info["fingering"]["octave_salvaged_notes"] == 0
    assert result.debug_info["fingering"]["tuning_midi"] == {4: 28, 3: 33, 2: 38, 1: 43}


def test_tab_pipeline_raises_when_all_quantized_notes_drop_in_fingering() -> None:
    raw_notes = [RawNoteEvent(pitch_midi=20, start_sec=0.0, end_sec=0.5, confidence=0.9)]

    class FakeTranscriber:
        def transcribe(self, _bass_wav: Path) -> BassTranscriptionResult:
            return BassTranscriptionResult(engine="basic_pitch", midi_bytes=b"MThd", raw_notes=raw_notes)

    bars = [Bar(index=0, start_sec=0.0, end_sec=2.0, beats_sec=[0.0, 0.5, 1.0, 1.5])]
    export_called = False

    def fake_export(_notes, _bars, **_kwargs):
        nonlocal export_called
        export_called = True
        return ("\\tempo 120", [SyncPoint(bar_index=0, millisecond_offset=0)])

    pipeline = TabPipeline(
        transcriber=FakeTranscriber(),
        rhythm_extract_fn=lambda _drums, **_kwargs: ([0.0, 0.5, 1.0, 1.5], [0.0], "madmom"),
        bar_builder_fn=lambda _beats, _downbeats, **_kwargs: bars,
        cleanup_fn=lambda events, **_kwargs: events,
        quantize_fn=lambda _events, _grid, **_kwargs: [
            QuantizedNote(
                bar_index=0,
                beat_position=0.0,
                duration_beats=1.0,
                pitch_midi=20,
                start_sec=0.0,
                end_sec=0.5,
            )
        ],
        export_fn=fake_export,
    )

    with pytest.raises(FingeringCollapseError, match="fingering dropped all quantized notes"):
        pipeline.run(Path("bass.wav"), Path("drums.wav"), bpm_hint=120.0)

    assert export_called is False
