from __future__ import annotations

import math
import wave
from pathlib import Path

import pytest

from app.services.alphatex_exporter import SyncPoint
from app.services.bass_transcriber import BassTranscriptionResult, RawNoteEvent
from app.services.fingering import FingeredNote
from app.services.note_cleanup import cleanup_params_for_bpm
from app.services.quantization import QuantizedNote
from app.services.rhythm_grid import Bar
from app.services.tab_pipeline import FingeringCollapseError, TabPipeline


def test_pipeline_result_exposes_fingered_notes() -> None:
    """TabPipelineResult must include fingered_notes for direct comparison."""
    raw_notes = [RawNoteEvent(pitch_midi=40, start_sec=0.0, end_sec=0.5, confidence=0.9)]

    class FakeTranscriber:
        def transcribe(self, _bass_wav, **kw):
            return BassTranscriptionResult(engine="fake", midi_bytes=b"MThd", raw_notes=raw_notes)

    bars = [Bar(index=0, start_sec=0.0, end_sec=2.0, beats_sec=[0.0, 0.5, 1.0, 1.5])]

    pipeline = TabPipeline(
        transcriber=FakeTranscriber(),
        rhythm_extract_fn=lambda _drums, **kw: ([0.0, 0.5, 1.0, 1.5], [0.0], "madmom"),
        bar_builder_fn=lambda _beats, _downbeats, **kw: bars,
    )

    result = pipeline.run(Path("bass.wav"), Path("drums.wav"), bpm_hint=120.0)

    assert hasattr(result, "fingered_notes")
    assert len(result.fingered_notes) > 0
    assert result.fingered_notes[0].pitch_midi == 40


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


def test_tab_pipeline_smoke_alphatex_contains_notes_and_sync_with_nonzero_after_fingering() -> None:
    raw_notes = [RawNoteEvent(pitch_midi=34, start_sec=0.0, end_sec=0.5, confidence=0.9)]

    class FakeTranscriber:
        def transcribe(self, _bass_wav: Path) -> BassTranscriptionResult:
            return BassTranscriptionResult(engine="basic_pitch", midi_bytes=b"MThd", raw_notes=raw_notes)

    bars = [Bar(index=0, start_sec=0.0, end_sec=2.0, beats_sec=[0.0, 0.5, 1.0, 1.5])]
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
                pitch_midi=34,
                start_sec=0.0,
                end_sec=0.5,
            ),
            QuantizedNote(
                bar_index=0,
                beat_position=1.0,
                duration_beats=1.0,
                pitch_midi=40,
                start_sec=0.5,
                end_sec=1.0,
            ),
        ],
    )

    result = pipeline.run(Path("bass.wav"), Path("drums.wav"), bpm_hint=120.0)

    assert result.debug_info["after_fingering"] > 0
    assert result.debug_info["after_exporting"] > 0
    assert "\\sync(" in result.alphatex
    assert "r.1" not in result.alphatex
    assert "1.3.4" in result.alphatex or "6.4.4" in result.alphatex


def _write_test_wav(path: Path, *, amplitudes: list[int], sample_rate: int = 8000, seconds_per_bar: float = 2.0) -> None:
    frame_count_per_bar = int(sample_rate * seconds_per_bar)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        frames = bytearray()
        for amplitude in amplitudes:
            for i in range(frame_count_per_bar):
                sample = int(amplitude * math.sin((2.0 * math.pi * 220.0 * i) / sample_rate))
                frames.extend(sample.to_bytes(2, byteorder="little", signed=True))
        wav_file.writeframes(bytes(frames))


def _write_constant_wav(path: Path, *, amplitude: int, duration_sec: float, sample_rate: int = 8000) -> None:
    frame_count = int(sample_rate * duration_sec)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        frames = bytearray()
        for _ in range(frame_count):
            frames.extend(int(amplitude).to_bytes(2, byteorder="little", signed=True))
        wav_file.writeframes(bytes(frames))


def test_high_accuracy_detects_suspect_silence_and_adds_notes(tmp_path: Path) -> None:
    bars = [
        Bar(index=0, start_sec=0.0, end_sec=2.0, beats_sec=[0.0, 0.5, 1.0, 1.5]),
        Bar(index=1, start_sec=2.0, end_sec=4.0, beats_sec=[2.0, 2.5, 3.0, 3.5]),
    ]

    class FakeTranscriber:
        def __init__(self) -> None:
            self.calls = 0

        def transcribe(self, _bass_wav: Path) -> BassTranscriptionResult:
            self.calls += 1
            if self.calls == 1:
                return BassTranscriptionResult(
                    engine="basic_pitch",
                    midi_bytes=b"MThd",
                    raw_notes=[RawNoteEvent(pitch_midi=40, start_sec=2.2, end_sec=2.6, confidence=0.9)],
                )
            return BassTranscriptionResult(
                engine="basic_pitch",
                midi_bytes=b"MThd",
                raw_notes=[RawNoteEvent(pitch_midi=34, start_sec=0.4, end_sec=0.8, confidence=0.9)],
            )

    transcriber = FakeTranscriber()

    def fake_quantize(events, _grid, **_kwargs):
        quantized: list[QuantizedNote] = []
        for event in events:
            bar_index = 0 if event.start_sec < 2.0 else 1
            quantized.append(
                QuantizedNote(
                    bar_index=bar_index,
                    beat_position=0.0,
                    duration_beats=1.0,
                    pitch_midi=event.pitch_midi,
                    start_sec=event.start_sec,
                    end_sec=event.end_sec,
                )
            )
        return quantized

    bass_wav = tmp_path / "bass.wav"
    drums_wav = tmp_path / "drums.wav"
    _write_test_wav(bass_wav, amplitudes=[9000, 7000])
    _write_test_wav(drums_wav, amplitudes=[1000, 1000])

    pipeline = TabPipeline(
        transcriber=transcriber,
        rhythm_extract_fn=lambda _drums, **_kwargs: ([0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5], [0.0, 2.0], "madmom"),
        bar_builder_fn=lambda _beats, _downbeats, **_kwargs: bars,
        cleanup_fn=lambda events, **_kwargs: events,
        quantize_fn=fake_quantize,
        fingering_fn=lambda notes, **_kwargs: [
            FingeredNote(
                bar_index=note.bar_index,
                beat_position=note.beat_position,
                duration_beats=note.duration_beats,
                pitch_midi=note.pitch_midi,
                start_sec=note.start_sec,
                end_sec=note.end_sec,
                string=4,
                fret=0,
            )
            for note in notes
        ],
        export_fn=lambda notes, _bars, **_kwargs: ("\\tempo 120", [SyncPoint(bar_index=0, millisecond_offset=0)]),
    )

    result = pipeline.run(
        bass_wav,
        drums_wav,
        bpm_hint=120.0,
        tab_generation_quality_mode="high_accuracy",
    )

    assert transcriber.calls > 1
    assert result.debug_info["suspect_silence_bars_count"] == 1
    assert result.debug_info["notes_added_second_pass"] > 0
    assert result.debug_info["notes_per_bar_before_high_accuracy"] == [0, 1]
    assert result.debug_info["notes_per_bar_after_high_accuracy"] == [1, 1]


def test_high_accuracy_does_not_trigger_on_low_energy_empty_bars(tmp_path: Path) -> None:
    bars = [
        Bar(index=0, start_sec=0.0, end_sec=2.0, beats_sec=[0.0, 0.5, 1.0, 1.5]),
        Bar(index=1, start_sec=2.0, end_sec=4.0, beats_sec=[2.0, 2.5, 3.0, 3.5]),
    ]

    class FakeTranscriber:
        def __init__(self) -> None:
            self.calls = 0

        def transcribe(self, _bass_wav: Path) -> BassTranscriptionResult:
            self.calls += 1
            return BassTranscriptionResult(
                engine="basic_pitch",
                midi_bytes=b"MThd",
                raw_notes=[RawNoteEvent(pitch_midi=40, start_sec=2.1, end_sec=2.5, confidence=0.9)],
            )

    transcriber = FakeTranscriber()

    def fake_quantize(events, _grid, **_kwargs):
        quantized: list[QuantizedNote] = []
        for event in events:
            bar_index = 0 if event.start_sec < 2.0 else 1
            quantized.append(
                QuantizedNote(
                    bar_index=bar_index,
                    beat_position=0.0,
                    duration_beats=1.0,
                    pitch_midi=event.pitch_midi,
                    start_sec=event.start_sec,
                    end_sec=event.end_sec,
                )
            )
        return quantized

    bass_wav = tmp_path / "bass.wav"
    drums_wav = tmp_path / "drums.wav"
    _write_test_wav(bass_wav, amplitudes=[1000, 12000])
    _write_test_wav(drums_wav, amplitudes=[1000, 1000])

    pipeline = TabPipeline(
        transcriber=transcriber,
        rhythm_extract_fn=lambda _drums, **_kwargs: ([0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5], [0.0, 2.0], "madmom"),
        bar_builder_fn=lambda _beats, _downbeats, **_kwargs: bars,
        cleanup_fn=lambda events, **_kwargs: events,
        quantize_fn=fake_quantize,
        fingering_fn=lambda notes, **_kwargs: [
            FingeredNote(
                bar_index=note.bar_index,
                beat_position=note.beat_position,
                duration_beats=note.duration_beats,
                pitch_midi=note.pitch_midi,
                start_sec=note.start_sec,
                end_sec=note.end_sec,
                string=4,
                fret=0,
            )
            for note in notes
        ],
        export_fn=lambda notes, _bars, **_kwargs: ("\\tempo 120", [SyncPoint(bar_index=0, millisecond_offset=0)]),
    )

    result = pipeline.run(
        bass_wav,
        drums_wav,
        bpm_hint=120.0,
        tab_generation_quality_mode="high_accuracy",
    )

    assert transcriber.calls == 1
    assert result.debug_info["suspect_silence_bars_count"] == 0
    assert result.debug_info["notes_added_second_pass"] == 0


def test_pipeline_corrects_double_time_grid_and_aligns_last_sync_to_audio_duration(tmp_path: Path) -> None:
    class FakeTranscriber:
        def transcribe(self, _bass_wav: Path) -> BassTranscriptionResult:
            return BassTranscriptionResult(
                engine="basic_pitch",
                midi_bytes=b"MThd",
                raw_notes=[RawNoteEvent(pitch_midi=40, start_sec=0.4, end_sec=0.8, confidence=0.9)],
            )

    # Raw beat grid is double-time (240 BPM) for a canonical song BPM of 120.
    beats = [idx * 0.25 for idx in range(30)]  # 0.0..7.25
    downbeats = [idx * 1.0 for idx in range(8)]  # 0.0..7.0
    bass_wav = tmp_path / "bass.wav"
    drums_wav = tmp_path / "drums.wav"
    _write_constant_wav(bass_wav, amplitude=500, duration_sec=8.0)
    _write_constant_wav(drums_wav, amplitude=500, duration_sec=8.0)

    pipeline = TabPipeline(
        transcriber=FakeTranscriber(),
        rhythm_extract_fn=lambda _drums, **_kwargs: (beats, downbeats, "madmom"),
        cleanup_fn=lambda events, **_kwargs: events,
        quantize_fn=lambda events, _grid, **_kwargs: [
            QuantizedNote(
                bar_index=0,
                beat_position=0.0,
                duration_beats=1.0,
                pitch_midi=events[0].pitch_midi,
                start_sec=events[0].start_sec,
                end_sec=events[0].end_sec,
            )
        ],
        fingering_fn=lambda notes, **_kwargs: [
            FingeredNote(
                bar_index=note.bar_index,
                beat_position=note.beat_position,
                duration_beats=note.duration_beats,
                pitch_midi=note.pitch_midi,
                start_sec=note.start_sec,
                end_sec=note.end_sec,
                string=4,
                fret=0,
            )
            for note in notes
        ],
    )

    result = pipeline.run(
        bass_wav,
        drums_wav,
        bpm_hint=120.0,
        tab_generation_quality_mode="standard",
        sync_every_bars=4,
    )

    assert result.debug_info["grid_correction_applied"] == "double_time"
    assert result.debug_info["beat_bpm_estimate_raw"] == pytest.approx(240.0, abs=1.0)
    assert result.debug_info["beat_bpm_estimate_corrected"] == pytest.approx(120.0, abs=1.0)
    assert abs(result.debug_info["audio_duration_sec"] - (result.debug_info["tab_last_sync_ms"] / 1000.0)) < 2.0


def test_high_accuracy_aggressive_uses_onsets_for_low_rms_empty_bar_detection(tmp_path: Path, monkeypatch) -> None:
    bars = [
        Bar(index=0, start_sec=0.0, end_sec=2.0, beats_sec=[0.0, 0.5, 1.0, 1.5]),
        Bar(index=1, start_sec=2.0, end_sec=4.0, beats_sec=[2.0, 2.5, 3.0, 3.5]),
    ]

    class FakeTranscriber:
        def __init__(self) -> None:
            self.calls = 0

        def transcribe(self, _bass_wav: Path, **_kwargs) -> BassTranscriptionResult:
            self.calls += 1
            if self.calls == 1:
                return BassTranscriptionResult(
                    engine="basic_pitch",
                    midi_bytes=b"MThd",
                    raw_notes=[RawNoteEvent(pitch_midi=40, start_sec=2.2, end_sec=2.6, confidence=0.9)],
                )
            return BassTranscriptionResult(
                engine="basic_pitch",
                midi_bytes=b"MThd",
                raw_notes=[RawNoteEvent(pitch_midi=35, start_sec=0.3, end_sec=0.6, confidence=0.9)],
            )

    def fake_quantize(events, _grid, **_kwargs):
        quantized: list[QuantizedNote] = []
        for event in events:
            bar_index = 0 if event.start_sec < 2.0 else 1
            quantized.append(
                QuantizedNote(
                    bar_index=bar_index,
                    beat_position=0.0,
                    duration_beats=1.0,
                    pitch_midi=event.pitch_midi,
                    start_sec=event.start_sec,
                    end_sec=event.end_sec,
                )
            )
        return quantized

    bass_wav = tmp_path / "bass.wav"
    drums_wav = tmp_path / "drums.wav"
    _write_test_wav(bass_wav, amplitudes=[300, 12000])  # keep bar 0 too low for global median RMS trigger.
    _write_test_wav(drums_wav, amplitudes=[1000, 1000])

    monkeypatch.setattr(
        TabPipeline,
        "_bar_onset_peaks",
        staticmethod(lambda _bass, _bars: [2, 0]),
        raising=False,
    )

    standard_ha_pipeline = TabPipeline(
        transcriber=FakeTranscriber(),
        rhythm_extract_fn=lambda _drums, **_kwargs: ([0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5], [0.0, 2.0], "madmom"),
        bar_builder_fn=lambda _beats, _downbeats, **_kwargs: bars,
        cleanup_fn=lambda events, **_kwargs: events,
        quantize_fn=fake_quantize,
        fingering_fn=lambda notes, **_kwargs: [
            FingeredNote(
                bar_index=note.bar_index,
                beat_position=note.beat_position,
                duration_beats=note.duration_beats,
                pitch_midi=note.pitch_midi,
                start_sec=note.start_sec,
                end_sec=note.end_sec,
                string=4,
                fret=0,
            )
            for note in notes
        ],
        export_fn=lambda notes, _bars, **_kwargs: ("\\tempo 120", [SyncPoint(bar_index=0, millisecond_offset=0)]),
    )

    standard_result = standard_ha_pipeline.run(
        bass_wav,
        drums_wav,
        bpm_hint=120.0,
        tab_generation_quality_mode="high_accuracy",
    )

    aggressive_pipeline = TabPipeline(
        transcriber=FakeTranscriber(),
        rhythm_extract_fn=lambda _drums, **_kwargs: ([0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5], [0.0, 2.0], "madmom"),
        bar_builder_fn=lambda _beats, _downbeats, **_kwargs: bars,
        cleanup_fn=lambda events, **_kwargs: events,
        quantize_fn=fake_quantize,
        fingering_fn=lambda notes, **_kwargs: [
            FingeredNote(
                bar_index=note.bar_index,
                beat_position=note.beat_position,
                duration_beats=note.duration_beats,
                pitch_midi=note.pitch_midi,
                start_sec=note.start_sec,
                end_sec=note.end_sec,
                string=4,
                fret=0,
            )
            for note in notes
        ],
        export_fn=lambda notes, _bars, **_kwargs: ("\\tempo 120", [SyncPoint(bar_index=0, millisecond_offset=0)]),
    )

    aggressive_result = aggressive_pipeline.run(
        bass_wav,
        drums_wav,
        bpm_hint=120.0,
        tab_generation_quality_mode="high_accuracy_aggressive",
    )

    assert standard_result.debug_info["suspect_silence_bars_count"] == 0
    assert standard_result.debug_info["notes_added_second_pass"] == 0
    assert aggressive_result.debug_info["suspect_silence_bars_count"] == 1
    assert aggressive_result.debug_info["notes_added_second_pass"] > 0
    assert aggressive_result.debug_info["suspect_bars"][0]["triggered_by_onsets"] is True


def test_pipeline_applies_onset_recovery_before_cleanup() -> None:
    class FakeTranscriber:
        def transcribe(self, _bass_wav: Path) -> BassTranscriptionResult:
            return BassTranscriptionResult(
                engine="basic_pitch",
                midi_bytes=b"MThd",
                raw_notes=[RawNoteEvent(pitch_midi=40, start_sec=0.0, end_sec=1.0, confidence=0.9)],
            )

    bars = [Bar(index=0, start_sec=0.0, end_sec=2.0, beats_sec=[0.0, 0.5, 1.0, 1.5])]
    cleanup_inputs: dict[str, object] = {}

    def fake_cleanup(events, **kwargs):
        cleanup_inputs["events"] = events
        cleanup_inputs["kwargs"] = kwargs
        return events

    pipeline = TabPipeline(
        transcriber=FakeTranscriber(),
        rhythm_extract_fn=lambda _drums, **_kwargs: ([0.0, 0.5, 1.0, 1.5], [0.0], "madmom"),
        bar_builder_fn=lambda _beats, _downbeats, **_kwargs: bars,
        cleanup_fn=fake_cleanup,
        onset_detect_fn=lambda _bass_wav: [0.4],
        quantize_fn=lambda events, _grid, **_kwargs: [
            QuantizedNote(
                bar_index=0,
                beat_position=0.0,
                duration_beats=0.5,
                pitch_midi=event.pitch_midi,
                start_sec=event.start_sec,
                end_sec=event.end_sec,
            )
            for event in events
        ],
        fingering_fn=lambda notes, **_kwargs: [
            FingeredNote(
                bar_index=note.bar_index,
                beat_position=note.beat_position,
                duration_beats=note.duration_beats,
                pitch_midi=note.pitch_midi,
                start_sec=note.start_sec,
                end_sec=note.end_sec,
                string=4,
                fret=0,
            )
            for note in notes
        ],
        export_fn=lambda notes, _bars, **_kwargs: ("\\tempo 120", [SyncPoint(bar_index=0, millisecond_offset=0)]),
    )

    result = pipeline.run(Path("bass.wav"), Path("drums.wav"), bpm_hint=120.0, onset_recovery=True)

    assert result.debug_info["onset_recovery_applied"] is True
    cleanup_events = cleanup_inputs["events"]
    assert isinstance(cleanup_events, list)
    assert len(cleanup_events) == 2
    assert cleanup_events[0].start_sec == 0.0
    assert cleanup_events[0].end_sec == 0.4
    assert cleanup_events[1].start_sec == 0.4
    assert cleanup_events[1].end_sec == 1.0


def test_pipeline_uses_bpm_adaptive_cleanup_parameters() -> None:
    class FakeTranscriber:
        def transcribe(self, _bass_wav: Path) -> BassTranscriptionResult:
            return BassTranscriptionResult(
                engine="basic_pitch",
                midi_bytes=b"MThd",
                raw_notes=[RawNoteEvent(pitch_midi=40, start_sec=0.0, end_sec=0.5, confidence=0.9)],
            )

    bars = [Bar(index=0, start_sec=0.0, end_sec=2.0, beats_sec=[0.0, 0.5, 1.0, 1.5])]
    captured_kwargs: dict[str, object] = {}

    def fake_cleanup(events, **kwargs):
        captured_kwargs.update(kwargs)
        return events

    pipeline = TabPipeline(
        transcriber=FakeTranscriber(),
        rhythm_extract_fn=lambda _drums, **_kwargs: ([0.0, 0.375, 0.75, 1.125], [0.0], "madmom"),
        bar_builder_fn=lambda _beats, _downbeats, **_kwargs: bars,
        cleanup_fn=fake_cleanup,
        quantize_fn=lambda events, _grid, **_kwargs: [
            QuantizedNote(
                bar_index=0,
                beat_position=0.0,
                duration_beats=1.0,
                pitch_midi=event.pitch_midi,
                start_sec=event.start_sec,
                end_sec=event.end_sec,
            )
            for event in events
        ],
        fingering_fn=lambda notes, **_kwargs: [
            FingeredNote(
                bar_index=note.bar_index,
                beat_position=note.beat_position,
                duration_beats=note.duration_beats,
                pitch_midi=note.pitch_midi,
                start_sec=note.start_sec,
                end_sec=note.end_sec,
                string=4,
                fret=0,
            )
            for note in notes
        ],
        export_fn=lambda notes, _bars, **_kwargs: ("\\tempo 120", [SyncPoint(bar_index=0, millisecond_offset=0)]),
    )

    pipeline.run(Path("bass.wav"), Path("drums.wav"), bpm_hint=160.0)

    assert captured_kwargs == cleanup_params_for_bpm(160.0)
