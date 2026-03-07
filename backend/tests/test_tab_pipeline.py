from __future__ import annotations

import math
import wave
from pathlib import Path

import pytest
import app.services.onset_note_generator as onset_note_generator_mod

from app.services.alphatex_exporter import SyncPoint
from app.services.bass_transcriber import BassTranscriptionResult, RawNoteEvent
from app.services.dense_note_generator import DenseNoteCandidate
from app.services.fingering import FingeredNote
from app.services.note_cleanup import cleanup_params_for_bpm
from app.services.onset_note_generator import OnsetNoteCandidate
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


def test_pipeline_reuses_identical_cleanup_kwargs_in_second_pass(tmp_path: Path, monkeypatch) -> None:
    class FakeTranscriber:
        def __init__(self) -> None:
            self.calls = 0

        def transcribe(self, _bass_wav: Path, **_kwargs) -> BassTranscriptionResult:
            self.calls += 1
            if self.calls == 1:
                return BassTranscriptionResult(
                    engine="basic_pitch",
                    midi_bytes=b"MThd",
                    raw_notes=[RawNoteEvent(pitch_midi=40, start_sec=2.1, end_sec=2.4, confidence=0.9)],
                )
            return BassTranscriptionResult(
                engine="basic_pitch",
                midi_bytes=b"MThd",
                raw_notes=[RawNoteEvent(pitch_midi=35, start_sec=0.2, end_sec=0.6, confidence=0.9)],
            )

    bars = [
        Bar(index=0, start_sec=0.0, end_sec=2.0, beats_sec=[0.0, 0.5, 1.0, 1.5]),
        Bar(index=1, start_sec=2.0, end_sec=4.0, beats_sec=[2.0, 2.5, 3.0, 3.5]),
    ]

    cleanup_kwargs_calls: list[dict[str, object]] = []

    def fake_cleanup(events, **kwargs):
        cleanup_kwargs_calls.append(dict(kwargs))
        return events

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

    pipeline = TabPipeline(
        transcriber=FakeTranscriber(),
        rhythm_extract_fn=lambda _drums, **_kwargs: ([0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5], [0.0, 2.0], "madmom"),
        bar_builder_fn=lambda _beats, _downbeats, **_kwargs: bars,
        cleanup_fn=fake_cleanup,
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

    bass_wav = tmp_path / "bass.wav"
    drums_wav = tmp_path / "drums.wav"
    _write_test_wav(bass_wav, amplitudes=[300, 12000])
    _write_test_wav(drums_wav, amplitudes=[1000, 1000])
    monkeypatch.setattr(TabPipeline, "_bar_rms_values", staticmethod(lambda _bass, _bars: [1.0, 1.0]), raising=False)
    monkeypatch.setattr(TabPipeline, "_bar_onset_peaks", staticmethod(lambda _bass, _bars: [0, 0]), raising=False)

    pipeline.run(
        bass_wav,
        drums_wav,
        bpm_hint=160.0,
        tab_generation_quality_mode="high_accuracy",
    )

    assert len(cleanup_kwargs_calls) == 2
    assert cleanup_kwargs_calls[0] == cleanup_kwargs_calls[1]
    expected_cleanup = cleanup_params_for_bpm(160.0)
    for key, value in expected_cleanup.items():
        assert cleanup_kwargs_calls[0][key] == value


def test_pipeline_enables_onset_recovery_for_high_accuracy_by_default(tmp_path: Path, monkeypatch) -> None:
    class FakeTranscriber:
        def transcribe(self, _bass_wav: Path, **_kwargs) -> BassTranscriptionResult:
            return BassTranscriptionResult(
                engine="basic_pitch",
                midi_bytes=b"MThd",
                raw_notes=[RawNoteEvent(pitch_midi=40, start_sec=0.0, end_sec=1.0, confidence=0.9)],
            )

    bars = [Bar(index=0, start_sec=0.0, end_sec=2.0, beats_sec=[0.0, 0.5, 1.0, 1.5])]
    pipeline = TabPipeline(
        transcriber=FakeTranscriber(),
        rhythm_extract_fn=lambda _drums, **_kwargs: ([0.0, 0.5, 1.0, 1.5], [0.0], "madmom"),
        bar_builder_fn=lambda _beats, _downbeats, **_kwargs: bars,
        onset_detect_fn=lambda _bass: [0.4],
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

    bass_wav = tmp_path / "bass.wav"
    drums_wav = tmp_path / "drums.wav"
    _write_test_wav(bass_wav, amplitudes=[8000])
    _write_test_wav(drums_wav, amplitudes=[1000])
    monkeypatch.setattr(TabPipeline, "_bar_rms_values", staticmethod(lambda _bass, _bars: [0.1]), raising=False)
    monkeypatch.setattr(TabPipeline, "_bar_onset_peaks", staticmethod(lambda _bass, _bars: [0]), raising=False)

    result = pipeline.run(
        bass_wav,
        drums_wav,
        bpm_hint=120.0,
        tab_generation_quality_mode="high_accuracy",
    )

    assert result.debug_info["onset_recovery_applied"] is True
    assert result.debug_info["after_onset_recovery_count"] == 2


def test_high_accuracy_aggressive_second_pass_targets_dense_sparse_bars(tmp_path: Path, monkeypatch) -> None:
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
                    raw_notes=[
                        RawNoteEvent(pitch_midi=40, start_sec=0.2, end_sec=1.4, confidence=0.9),
                        RawNoteEvent(pitch_midi=35, start_sec=2.2, end_sec=2.6, confidence=0.9),
                    ],
                )
            return BassTranscriptionResult(
                engine="basic_pitch",
                midi_bytes=b"MThd",
                raw_notes=[RawNoteEvent(pitch_midi=40, start_sec=1.45, end_sec=1.8, confidence=0.9)],
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
    _write_test_wav(bass_wav, amplitudes=[6000, 6000])
    _write_test_wav(drums_wav, amplitudes=[1000, 1000])

    monkeypatch.setattr(TabPipeline, "_bar_rms_values", staticmethod(lambda _bass, _bars: [1.0, 1.0]), raising=False)
    monkeypatch.setattr(
        TabPipeline,
        "_bar_onset_peaks",
        staticmethod(lambda _bass, _bars: [8, 0]),
        raising=False,
    )

    pipeline = TabPipeline(
        transcriber=FakeTranscriber(),
        dense_note_generator=type(
            "FakeDenseGenerator",
            (),
            {
                "generate": lambda self, **_kwargs: [
                    DenseNoteCandidate(
                        pitch_midi=40,
                        start_sec=1.45,
                        end_sec=1.8,
                        confidence=0.76,
                        support={"anchor_pitch": 40, "repeated_note_mode": True, "raw_pitch_midi": 52},
                    )
                ]
            },
        )(),
        rhythm_extract_fn=lambda _drums, **_kwargs: ([0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5], [0.0, 2.0], "madmom"),
        bar_builder_fn=lambda _beats, _downbeats, **_kwargs: bars,
        onset_detect_fn=lambda _bass: [0.2, 1.45, 1.8],
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
        tab_generation_quality_mode="high_accuracy_aggressive",
        onset_recovery=False,
    )

    assert result.debug_info["suspect_silence_bars_count"] == 1
    assert result.debug_info["notes_added_second_pass"] > 0
    assert result.debug_info["suspect_bars"][0]["triggered_by_dense_sparse"] is True
    fusion_summary = result.debug_info["dense_note_fusion_summary"]
    assert fusion_summary["candidates"] >= 1
    assert fusion_summary["accepted"] >= 1
    assert fusion_summary["rejected"] == 0


def test_dense_sparse_second_pass_reuses_local_pitch_track(tmp_path: Path, monkeypatch) -> None:
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
                    raw_notes=[
                        RawNoteEvent(pitch_midi=40, start_sec=0.2, end_sec=1.2, confidence=0.9),
                        RawNoteEvent(pitch_midi=35, start_sec=2.2, end_sec=2.6, confidence=0.9),
                    ],
                )
            return BassTranscriptionResult(
                engine="basic_pitch",
                midi_bytes=b"MThd",
                raw_notes=[RawNoteEvent(pitch_midi=52, start_sec=1.25, end_sec=1.55, confidence=0.9)],
            )

    def fake_quantize(events, _grid, **_kwargs):
        return [
            QuantizedNote(
                bar_index=0 if event.start_sec < 2.0 else 1,
                beat_position=0.0,
                duration_beats=1.0,
                pitch_midi=event.pitch_midi,
                start_sec=event.start_sec,
                end_sec=event.end_sec,
            )
            for event in events
        ]

    exported_pitches: list[int] = []

    def fake_export(notes, _bars, **_kwargs):
        exported_pitches.extend(note.pitch_midi for note in notes)
        return "\\tempo 120", [SyncPoint(bar_index=0, millisecond_offset=0)]

    bass_wav = tmp_path / "bass.wav"
    drums_wav = tmp_path / "drums.wav"
    _write_test_wav(bass_wav, amplitudes=[6000, 6000])
    _write_test_wav(drums_wav, amplitudes=[1000, 1000])

    monkeypatch.setattr(TabPipeline, "_bar_rms_values", staticmethod(lambda _bass, _bars: [1.0, 1.0]), raising=False)
    monkeypatch.setattr(TabPipeline, "_bar_onset_peaks", staticmethod(lambda _bass, _bars: [8, 0]), raising=False)

    pipeline = TabPipeline(
        transcriber=FakeTranscriber(),
        dense_note_generator=type(
            "FakeDenseGenerator",
            (),
            {
                "generate": lambda self, **_kwargs: [
                    DenseNoteCandidate(
                        pitch_midi=62,
                        start_sec=1.45,
                        end_sec=1.8,
                        confidence=0.42,
                        support={"anchor_pitch": 40, "repeated_note_mode": False, "raw_pitch_midi": 62},
                    )
                ]
            },
        )(),
        rhythm_extract_fn=lambda _drums, **_kwargs: ([0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5], [0.0, 2.0], "madmom"),
        bar_builder_fn=lambda _beats, _downbeats, **_kwargs: bars,
        onset_detect_fn=lambda _bass: [0.2, 1.45, 1.8],
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
        export_fn=fake_export,
    )

    pipeline.run(
        bass_wav,
        drums_wav,
        bpm_hint=120.0,
        tab_generation_quality_mode="high_accuracy_aggressive",
        onset_recovery=False,
    )

    assert 40 in exported_pitches
    assert 52 not in exported_pitches


def test_dense_sparse_second_pass_rejects_pitch_outlier_and_logs_reason(tmp_path: Path, monkeypatch) -> None:
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
                    raw_notes=[
                        RawNoteEvent(pitch_midi=40, start_sec=0.2, end_sec=1.0, confidence=0.9),
                        RawNoteEvent(pitch_midi=40, start_sec=1.05, end_sec=1.4, confidence=0.9),
                    ],
                )
            return BassTranscriptionResult(
                engine="basic_pitch",
                midi_bytes=b"MThd",
                raw_notes=[RawNoteEvent(pitch_midi=62, start_sec=1.45, end_sec=1.8, confidence=0.9)],
            )

    def fake_quantize(events, _grid, **_kwargs):
        return [
            QuantizedNote(
                bar_index=0 if event.start_sec < 2.0 else 1,
                beat_position=0.0,
                duration_beats=1.0,
                pitch_midi=event.pitch_midi,
                start_sec=event.start_sec,
                end_sec=event.end_sec,
            )
            for event in events
        ]

    bass_wav = tmp_path / "bass.wav"
    drums_wav = tmp_path / "drums.wav"
    _write_test_wav(bass_wav, amplitudes=[6000, 6000])
    _write_test_wav(drums_wav, amplitudes=[1000, 1000])

    monkeypatch.setattr(TabPipeline, "_bar_rms_values", staticmethod(lambda _bass, _bars: [1.0, 1.0]), raising=False)
    monkeypatch.setattr(TabPipeline, "_bar_onset_peaks", staticmethod(lambda _bass, _bars: [8, 0]), raising=False)

    pipeline = TabPipeline(
        transcriber=FakeTranscriber(),
        dense_note_generator=type(
            "FakeDenseGenerator",
            (),
            {
                "generate": lambda self, **_kwargs: [
                    DenseNoteCandidate(
                        pitch_midi=62,
                        start_sec=1.45,
                        end_sec=1.8,
                        confidence=0.42,
                        support={"anchor_pitch": 40, "repeated_note_mode": False, "raw_pitch_midi": 62},
                    )
                ]
            },
        )(),
        rhythm_extract_fn=lambda _drums, **_kwargs: ([0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5], [0.0, 2.0], "madmom"),
        bar_builder_fn=lambda _beats, _downbeats, **_kwargs: bars,
        onset_detect_fn=lambda _bass: [0.2, 1.45, 1.8],
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
        tab_generation_quality_mode="high_accuracy_aggressive",
        onset_recovery=False,
    )

    summary = result.debug_info["dense_note_fusion_summary"]
    assert summary["candidates"] == 1
    assert summary["accepted"] == 0
    assert summary["rejected"] == 1
    assert summary["rejection_histogram"]["pitch_far_from_anchor"] == 1
    candidate = result.debug_info["dense_note_fusion_candidates"][0]
    assert candidate["accepted"] is False
    assert candidate["rejection_reason"] == "pitch_far_from_anchor"


def test_dense_sparse_second_pass_rejects_octave_neighbor_intrusion(tmp_path: Path, monkeypatch) -> None:
    bars = [
        Bar(index=0, start_sec=0.0, end_sec=2.0, beats_sec=[0.0, 0.5, 1.0, 1.5]),
        Bar(index=1, start_sec=2.0, end_sec=4.0, beats_sec=[2.0, 2.5, 3.0, 3.5]),
    ]

    class FakeTranscriber:
        def transcribe(self, _bass_wav: Path, **_kwargs) -> BassTranscriptionResult:
            return BassTranscriptionResult(
                engine="basic_pitch",
                midi_bytes=b"MThd",
                raw_notes=[
                    RawNoteEvent(pitch_midi=40, start_sec=0.20, end_sec=1.10, confidence=0.94),
                    RawNoteEvent(pitch_midi=40, start_sec=1.12, end_sec=1.40, confidence=0.93),
                ],
            )

    def fake_quantize(events, _grid, **_kwargs):
        return [
            QuantizedNote(
                bar_index=0 if event.start_sec < 2.0 else 1,
                beat_position=0.0,
                duration_beats=1.0,
                pitch_midi=event.pitch_midi,
                start_sec=event.start_sec,
                end_sec=event.end_sec,
            )
            for event in events
        ]

    bass_wav = tmp_path / "bass.wav"
    drums_wav = tmp_path / "drums.wav"
    _write_test_wav(bass_wav, amplitudes=[6000, 6000])
    _write_test_wav(drums_wav, amplitudes=[1000, 1000])

    monkeypatch.setattr(TabPipeline, "_bar_rms_values", staticmethod(lambda _bass, _bars: [1.0, 1.0]), raising=False)
    monkeypatch.setattr(TabPipeline, "_bar_onset_peaks", staticmethod(lambda _bass, _bars: [8, 0]), raising=False)

    pipeline = TabPipeline(
        transcriber=FakeTranscriber(),
        dense_note_generator=type(
            "FakeDenseGenerator",
            (),
            {
                "generate": lambda self, **_kwargs: [
                    DenseNoteCandidate(
                        pitch_midi=52,
                        start_sec=1.45,
                        end_sec=1.50,
                        confidence=0.78,
                        support={"anchor_pitch": 40, "repeated_note_mode": False, "raw_pitch_midi": 52},
                    )
                ]
            },
        )(),
        rhythm_extract_fn=lambda _drums, **_kwargs: ([0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5], [0.0, 2.0], "madmom"),
        bar_builder_fn=lambda _beats, _downbeats, **_kwargs: bars,
        onset_detect_fn=lambda _bass: [0.2, 1.45, 1.8],
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
        tab_generation_quality_mode="high_accuracy_aggressive",
        onset_recovery=False,
    )

    summary = result.debug_info["dense_note_fusion_summary"]
    assert summary["candidates"] == 1
    assert summary["accepted"] == 0
    assert summary["rejected"] == 1
    assert summary["rejection_histogram"]["octave_neighbor_conflict"] == 1


def test_high_accuracy_aggressive_fuses_dense_candidates_before_cleanup(tmp_path: Path, monkeypatch) -> None:
    class FakeTranscriber:
        def transcribe(self, _bass_wav: Path, **_kwargs) -> BassTranscriptionResult:
            return BassTranscriptionResult(
                engine="basic_pitch",
                midi_bytes=b"MThd",
                raw_notes=[
                    RawNoteEvent(pitch_midi=40, start_sec=0.2, end_sec=0.8, confidence=0.9),
                    RawNoteEvent(pitch_midi=35, start_sec=2.2, end_sec=2.6, confidence=0.9),
                ],
            )

    class FakeDenseGenerator:
        def generate(self, **_kwargs):
            return [
                DenseNoteCandidate(
                    pitch_midi=40,
                    start_sec=1.0,
                    end_sec=1.16,
                    confidence=0.74,
                    support={"anchor_pitch": 40, "repeated_note_mode": True},
                )
            ]

    bars = [
        Bar(index=0, start_sec=0.0, end_sec=2.0, beats_sec=[0.0, 0.5, 1.0, 1.5]),
        Bar(index=1, start_sec=2.0, end_sec=4.0, beats_sec=[2.0, 2.5, 3.0, 3.5]),
    ]
    cleanup_inputs: list[list[RawNoteEvent]] = []

    def fake_cleanup(events, **_kwargs):
        cleanup_inputs.append(list(events))
        return events

    pipeline = TabPipeline(
        transcriber=FakeTranscriber(),
        dense_note_generator=FakeDenseGenerator(),
        rhythm_extract_fn=lambda _drums, **_kwargs: ([0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5], [0.0, 2.0], "madmom"),
        bar_builder_fn=lambda _beats, _downbeats, **_kwargs: bars,
        onset_detect_fn=lambda _bass: [0.2, 1.0, 1.5],
        cleanup_fn=fake_cleanup,
        quantize_fn=lambda events, _grid, **_kwargs: [
            QuantizedNote(
                bar_index=0 if event.start_sec < 2.0 else 1,
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
                fret=max(0, note.pitch_midi - 28),
            )
            for note in notes
        ],
        export_fn=lambda notes, _bars, **_kwargs: ("\\tempo 120", [SyncPoint(bar_index=0, millisecond_offset=0)]),
    )

    monkeypatch.setattr(TabPipeline, "_bar_rms_values", staticmethod(lambda _bass, _bars: [1.0, 1.0]), raising=False)
    monkeypatch.setattr(TabPipeline, "_bar_onset_peaks", staticmethod(lambda _bass, _bars: [8, 0]), raising=False)

    result = pipeline.run(
        tmp_path / "bass.wav",
        tmp_path / "drums.wav",
        bpm_hint=120.0,
        tab_generation_quality_mode="high_accuracy_aggressive",
        onset_recovery=False,
    )

    assert len(cleanup_inputs) == 2
    assert [(round(note.start_sec, 2), note.pitch_midi) for note in cleanup_inputs[-1]] == [(0.2, 40), (1.0, 40), (2.2, 35)]
    source_summary = result.debug_info["raw_note_source_summary"]
    assert source_summary["basic_pitch"] == 2
    assert source_summary["dense_note_generator"] == 1
    assert result.debug_info["dense_note_fusion_summary"]["accepted"] == 1


def test_high_accuracy_aggressive_can_disable_dense_note_generator_with_config(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DECHORD_DENSE_NOTE_GENERATOR_ENABLE", "0")

    class FakeTranscriber:
        def transcribe(self, _bass_wav: Path, **_kwargs) -> BassTranscriptionResult:
            return BassTranscriptionResult(
                engine="basic_pitch",
                midi_bytes=b"MThd",
                raw_notes=[
                    RawNoteEvent(pitch_midi=40, start_sec=0.2, end_sec=0.8, confidence=0.9),
                    RawNoteEvent(pitch_midi=35, start_sec=2.2, end_sec=2.6, confidence=0.9),
                ],
            )

    dense_generator_calls: list[dict[str, object]] = []

    class FakeDenseGenerator:
        def generate(self, **kwargs):
            dense_generator_calls.append(dict(kwargs))
            return [
                DenseNoteCandidate(
                    pitch_midi=40,
                    start_sec=1.0,
                    end_sec=1.16,
                    confidence=0.74,
                    support={"anchor_pitch": 40, "repeated_note_mode": True},
                )
            ]

    bars = [
        Bar(index=0, start_sec=0.0, end_sec=2.0, beats_sec=[0.0, 0.5, 1.0, 1.5]),
        Bar(index=1, start_sec=2.0, end_sec=4.0, beats_sec=[2.0, 2.5, 3.0, 3.5]),
    ]
    cleanup_inputs: list[list[RawNoteEvent]] = []

    def fake_cleanup(events, **_kwargs):
        cleanup_inputs.append(list(events))
        return events

    pipeline = TabPipeline(
        transcriber=FakeTranscriber(),
        dense_note_generator=FakeDenseGenerator(),
        rhythm_extract_fn=lambda _drums, **_kwargs: ([0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5], [0.0, 2.0], "madmom"),
        bar_builder_fn=lambda _beats, _downbeats, **_kwargs: bars,
        onset_detect_fn=lambda _bass: [0.2, 1.0, 1.5],
        cleanup_fn=fake_cleanup,
        quantize_fn=lambda events, _grid, **_kwargs: [
            QuantizedNote(
                bar_index=0 if event.start_sec < 2.0 else 1,
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
                fret=max(0, note.pitch_midi - 28),
            )
            for note in notes
        ],
        export_fn=lambda notes, _bars, **_kwargs: ("\\tempo 120", [SyncPoint(bar_index=0, millisecond_offset=0)]),
    )

    monkeypatch.setattr(TabPipeline, "_bar_rms_values", staticmethod(lambda _bass, _bars: [1.0, 1.0]), raising=False)
    monkeypatch.setattr(TabPipeline, "_bar_onset_peaks", staticmethod(lambda _bass, _bars: [8, 0]), raising=False)
    monkeypatch.setattr(
        TabPipeline,
        "_transcribe_window_with_offset",
        lambda self, _bass_wav, *, window_start, window_end: [
            RawNoteEvent(
                pitch_midi=41,
                start_sec=window_start + 0.2,
                end_sec=min(window_end, window_start + 0.36),
                confidence=0.88,
            )
        ],
        raising=False,
    )

    result = pipeline.run(
        tmp_path / "bass.wav",
        tmp_path / "drums.wav",
        bpm_hint=120.0,
        tab_generation_quality_mode="high_accuracy_aggressive",
        onset_recovery=False,
    )

    assert dense_generator_calls == []
    assert len(cleanup_inputs) == 1
    assert result.debug_info["dense_note_fusion_summary"]["accepted"] == 0
    assert result.debug_info["raw_note_source_summary"] == {"basic_pitch": 2}


def test_pipeline_records_raw_note_source_attribution_and_cleanup_survival(tmp_path: Path, monkeypatch) -> None:
    class FakeTranscriber:
        def transcribe(self, _bass_wav: Path, **_kwargs) -> BassTranscriptionResult:
            return BassTranscriptionResult(
                engine="basic_pitch",
                midi_bytes=b"MThd",
                raw_notes=[RawNoteEvent(pitch_midi=40, start_sec=0.2, end_sec=0.8, confidence=0.9)],
            )

    class FakeDenseGenerator:
        def generate(self, **_kwargs):
            return [
                DenseNoteCandidate(
                    pitch_midi=40,
                    start_sec=1.0,
                    end_sec=1.16,
                    confidence=0.74,
                    support={"anchor_pitch": 40, "repeated_note_mode": True, "raw_pitch_midi": 52},
                )
            ]

    bars = [Bar(index=0, start_sec=0.0, end_sec=2.0, beats_sec=[0.0, 0.5, 1.0, 1.5])]

    def fake_cleanup(events, **_kwargs):
        return [event for event in events if event.start_sec < 0.5]

    pipeline = TabPipeline(
        transcriber=FakeTranscriber(),
        dense_note_generator=FakeDenseGenerator(),
        rhythm_extract_fn=lambda _drums, **_kwargs: ([0.0, 0.5, 1.0, 1.5], [0.0], "madmom"),
        bar_builder_fn=lambda _beats, _downbeats, **_kwargs: bars,
        onset_detect_fn=lambda _bass: [0.2, 1.0, 1.4],
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
                fret=max(0, note.pitch_midi - 28),
            )
            for note in notes
        ],
        export_fn=lambda notes, _bars, **_kwargs: ("\\tempo 120", [SyncPoint(bar_index=0, millisecond_offset=0)]),
    )

    monkeypatch.setattr(TabPipeline, "_bar_rms_values", staticmethod(lambda _bass, _bars: [1.0]), raising=False)
    monkeypatch.setattr(TabPipeline, "_bar_onset_peaks", staticmethod(lambda _bass, _bars: [8]), raising=False)

    result = pipeline.run(
        tmp_path / "bass.wav",
        tmp_path / "drums.wav",
        bpm_hint=120.0,
        tab_generation_quality_mode="high_accuracy_aggressive",
        onset_recovery=False,
    )

    rows = result.debug_info["raw_note_source_rows"]
    assert len(rows) == 2
    assert rows[0]["source"] == "basic_pitch"
    assert rows[0]["survived_cleanup"] is True
    assert rows[1]["source"] == "hybrid_merged"
    assert rows[1]["survived_cleanup"] is False
    assert rows[1]["confidence_summary"]["raw_pitch_midi"] == 52


def test_standard_mode_activates_dense_recovery_for_sparse_regions_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DECHORD_RAW_NOTE_RECALL_ENABLE", "1")
    monkeypatch.setenv("DECHORD_RAW_NOTE_SPARSE_REGION_BOOST_ENABLE", "1")
    monkeypatch.setenv("DECHORD_DENSE_CANDIDATE_SPARSE_REGION_THRESHOLD_MS", "180")

    class FakeTranscriber:
        def transcribe(self, _bass_wav: Path) -> BassTranscriptionResult:
            return BassTranscriptionResult(
                engine="basic_pitch",
                midi_bytes=b"MThd",
                raw_notes=[
                    RawNoteEvent(pitch_midi=40, start_sec=0.00, end_sec=0.08, confidence=0.92),
                    RawNoteEvent(pitch_midi=40, start_sec=0.42, end_sec=0.50, confidence=0.93),
                ],
                debug_info={
                    "pipeline_trace": {
                        "pipeline_stats": {
                            "basic_pitch_raw": {
                                "note_count": 2,
                                "average_duration_ms": 80.0,
                                "median_duration_ms": 80.0,
                                "short_note_threshold_ms": 60,
                                "short_note_count": 0,
                                "octave_jump_count": 0,
                                "confidence_stats": {"mean": 0.925, "min": 0.92, "max": 0.93},
                                "notes_added_by_stage": 0,
                                "notes_removed_by_stage": 0,
                                "notes_merged_by_stage": 0,
                                "notes_altered_by_stage": 0,
                                "candidate_flow": {
                                    "pre_filter_note_count": 2,
                                    "post_filter_note_count": 2,
                                    "filtered_out_note_count": 0,
                                    "filter_rejection_histogram": {},
                                },
                            },
                            "pitch_stabilized": {
                                "note_count": 2,
                                "average_duration_ms": 80.0,
                                "median_duration_ms": 80.0,
                                "short_note_threshold_ms": 60,
                                "short_note_count": 0,
                                "octave_jump_count": 0,
                                "confidence_stats": {"mean": 0.925, "min": 0.92, "max": 0.93},
                                "notes_added_by_stage": 0,
                                "notes_removed_by_stage": 0,
                                "notes_merged_by_stage": 0,
                                "notes_altered_by_stage": 0,
                            },
                            "admission_filtered": {
                                "note_count": 2,
                                "average_duration_ms": 80.0,
                                "median_duration_ms": 80.0,
                                "short_note_threshold_ms": 60,
                                "short_note_count": 0,
                                "octave_jump_count": 0,
                                "confidence_stats": {"mean": 0.925, "min": 0.92, "max": 0.93},
                                "notes_added_by_stage": 0,
                                "notes_removed_by_stage": 0,
                                "notes_merged_by_stage": 0,
                                "notes_altered_by_stage": 0,
                            },
                        }
                    }
                },
            )

    bars = [Bar(index=0, start_sec=0.0, end_sec=1.0, beats_sec=[0.0, 0.25, 0.5, 0.75])]
    quantize_inputs: list[RawNoteEvent] = []

    def fake_quantize(events, _grid, **_kwargs):
        quantize_inputs[:] = list(events)
        return [
            QuantizedNote(
                bar_index=0,
                beat_position=float(index) * 0.5,
                duration_beats=0.5,
                pitch_midi=note.pitch_midi,
                start_sec=note.start_sec,
                end_sec=note.end_sec,
            )
            for index, note in enumerate(events)
        ]

    pipeline = TabPipeline(
        transcriber=FakeTranscriber(),
        rhythm_extract_fn=lambda _drums, **_kwargs: ([0.0, 0.25, 0.5, 0.75], [0.0], "madmom"),
        bar_builder_fn=lambda _beats, _downbeats, **_kwargs: bars,
        onset_detect_fn=lambda _bass: [0.02, 0.20, 0.44],
        cleanup_fn=lambda events, **_kwargs: list(events),
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
                fret=max(0, note.pitch_midi - 28),
            )
            for note in notes
        ],
        export_fn=lambda _notes, _bars, **_kwargs: ("\\tempo 120", [SyncPoint(bar_index=0, millisecond_offset=0)]),
        dense_note_generator=type(
            "FakeDenseGenerator",
            (),
            {
                "generate": lambda self, **_kwargs: [
                    DenseNoteCandidate(
                        pitch_midi=40,
                        start_sec=0.20,
                        end_sec=0.28,
                        confidence=0.74,
                        support={"raw_pitch_midi": 40, "anchor_pitch": 40},
                    )
                ],
            },
        )(),
    )

    result = pipeline.run(
        Path("bass.wav"),
        Path("drums.wav"),
        bpm_hint=120.0,
        tab_generation_quality_mode="standard",
        onset_recovery=False,
    )

    assert len(quantize_inputs) == 3
    assert [round(note.start_sec, 2) for note in quantize_inputs] == [0.0, 0.2, 0.42]
    assert result.debug_info["pipeline_trace"]["pipeline_stats"]["dense_candidates"]["note_count"] == 1
    assert result.debug_info["pipeline_trace"]["pipeline_stats"]["dense_accepted"]["note_count"] == 1


def test_tab_pipeline_uses_onset_candidates_when_basic_pitch_is_sparse(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DECHORD_ONSET_NOTE_GENERATOR_ENABLE", "1")
    monkeypatch.setenv("DECHORD_ONSET_NOTE_GENERATOR_MODE", "fallback")
    monkeypatch.setenv("DECHORD_ONSET_DENSITY_NOTES_PER_SEC_THRESHOLD", "3.0")

    class FakeTranscriber:
        def transcribe(self, _bass_wav: Path) -> BassTranscriptionResult:
            return BassTranscriptionResult(
                engine="basic_pitch",
                midi_bytes=b"MThd",
                raw_notes=[],
                debug_info={
                    "pipeline_trace": {
                        "pipeline_stats": {
                            "basic_pitch_raw": {
                                "note_count": 0,
                                "average_duration_ms": 0.0,
                                "median_duration_ms": 0.0,
                                "short_note_threshold_ms": 60,
                                "short_note_count": 0,
                                "octave_jump_count": 0,
                                "pitch_range": {"min": None, "max": None},
                                "confidence_stats": {"mean": None, "min": None, "max": None},
                                "notes_added_by_stage": 0,
                                "notes_removed_by_stage": 0,
                                "notes_merged_by_stage": 0,
                                "notes_altered_by_stage": 0,
                            },
                            "pitch_stabilized": {
                                "note_count": 0,
                                "average_duration_ms": 0.0,
                                "median_duration_ms": 0.0,
                                "short_note_threshold_ms": 60,
                                "short_note_count": 0,
                                "octave_jump_count": 0,
                                "pitch_range": {"min": None, "max": None},
                                "confidence_stats": {"mean": None, "min": None, "max": None},
                                "notes_added_by_stage": 0,
                                "notes_removed_by_stage": 0,
                                "notes_merged_by_stage": 0,
                                "notes_altered_by_stage": 0,
                            },
                            "admission_filtered": {
                                "note_count": 0,
                                "average_duration_ms": 0.0,
                                "median_duration_ms": 0.0,
                                "short_note_threshold_ms": 60,
                                "short_note_count": 0,
                                "octave_jump_count": 0,
                                "pitch_range": {"min": None, "max": None},
                                "confidence_stats": {"mean": None, "min": None, "max": None},
                                "notes_added_by_stage": 0,
                                "notes_removed_by_stage": 0,
                                "notes_merged_by_stage": 0,
                                "notes_altered_by_stage": 0,
                            },
                        }
                    }
                },
            )

    bars = [Bar(index=0, start_sec=0.0, end_sec=1.0, beats_sec=[0.0, 0.25, 0.5, 0.75])]
    quantized_inputs: list[RawNoteEvent] = []

    def fake_quantize(events, _grid, **_kwargs):
        quantized_inputs[:] = list(events)
        return [
            QuantizedNote(
                bar_index=0,
                beat_position=float(index) * 0.5,
                duration_beats=0.5,
                pitch_midi=note.pitch_midi,
                start_sec=note.start_sec,
                end_sec=note.end_sec,
            )
            for index, note in enumerate(events)
        ]

    pipeline = TabPipeline(
        transcriber=FakeTranscriber(),
        rhythm_extract_fn=lambda _drums, **_kwargs: ([0.0, 0.25, 0.5, 0.75], [0.0], "madmom"),
        bar_builder_fn=lambda _beats, _downbeats, **_kwargs: bars,
        onset_detect_fn=lambda _bass: [0.10, 0.34],
        cleanup_fn=lambda events, **_kwargs: list(events),
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
                fret=max(0, note.pitch_midi - 28),
            )
            for note in notes
        ],
        export_fn=lambda _notes, _bars, **_kwargs: ("\\tempo 120", [SyncPoint(bar_index=0, millisecond_offset=0)]),
        onset_note_generator=type(
            "FakeOnsetGenerator",
            (),
            {
                "generate": lambda self, _bass_wav: [
                    OnsetNoteCandidate(
                        pitch_midi=33,
                        start_sec=0.10,
                        end_sec=0.24,
                        confidence=0.72,
                    ),
                    OnsetNoteCandidate(
                        pitch_midi=36,
                        start_sec=0.34,
                        end_sec=0.48,
                        confidence=0.68,
                    ),
                ],
            },
        )(),
    )

    result = pipeline.run(Path("bass.wav"), Path("drums.wav"), bpm_hint=120.0, onset_recovery=False)

    assert [(round(note.start_sec, 2), note.pitch_midi) for note in quantized_inputs] == [(0.10, 33), (0.34, 36)]
    assert result.debug_info["raw_note_source_summary"]["onset_note_generator"] == 2
    assert result.debug_info["pipeline_trace"]["pipeline_stats"]["onset_candidates"]["note_count"] == 2
    assert result.debug_info["pipeline_trace"]["pipeline_stats"]["onset_candidates"]["candidate_flow"] == {
        "generator_enabled": True,
        "generator_mode": "fallback",
        "proposed_note_count": 2,
        "accepted_note_count": 2,
        "rejected_note_count": 0,
        "materially_changed_final_note_count": True,
        "analyzed_region_count": 2,
        "accepted_pitch_count": 2,
        "rejected_weak_region_count": 0,
        "average_region_pitch_confidence": pytest.approx(0.70),
        "octave_suppressed_count": 0,
        "pitch_corrected_region_count": 0,
        "accepted_pitch_range": {"min": 33, "max": 36},
    }


def test_tab_pipeline_real_onset_path_uses_region_pitch_estimator_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DECHORD_ONSET_NOTE_GENERATOR_ENABLE", "1")
    monkeypatch.setenv("DECHORD_ONSET_NOTE_GENERATOR_MODE", "fallback")
    monkeypatch.setenv("DECHORD_ONSET_DENSITY_NOTES_PER_SEC_THRESHOLD", "3.0")

    class FakeTranscriber:
        def transcribe(self, _bass_wav: Path) -> BassTranscriptionResult:
            return BassTranscriptionResult(
                engine="basic_pitch",
                midi_bytes=b"MThd",
                raw_notes=[],
                debug_info={"pipeline_trace": {"pipeline_stats": {}}},
            )

    quantized_inputs: list[RawNoteEvent] = []

    def fake_quantize(events, _grid, **_kwargs):
        quantized_inputs[:] = list(events)
        return [
            QuantizedNote(
                bar_index=0,
                beat_position=float(index) * 0.5,
                duration_beats=0.5,
                pitch_midi=note.pitch_midi,
                start_sec=note.start_sec,
                end_sec=note.end_sec,
            )
            for index, note in enumerate(events)
        ]

    called_regions: list[tuple[float, float]] = []

    def fake_estimate_pitch_for_region(audio, sr, *, region, config):
        called_regions.append(region)
        if region[0] < 0.2:
            return onset_note_generator_mod.OnsetRegionPitchEstimate(
                pitch_midi=33,
                confidence=0.74,
                support={
                    "region_start_sec": region[0],
                    "region_end_sec": region[1],
                    "initial_pitch_midi": 45,
                    "octave_suppressed": True,
                    "pitch_corrected": True,
                    "region_pitch_confidence": 0.74,
                    "evaluated_candidate_count": 4,
                },
            )
        return onset_note_generator_mod.OnsetRegionPitchEstimate(
            pitch_midi=35,
            confidence=0.71,
            support={
                "region_start_sec": region[0],
                "region_end_sec": region[1],
                "initial_pitch_midi": 35,
                "octave_suppressed": False,
                "pitch_corrected": False,
                "region_pitch_confidence": 0.71,
                "evaluated_candidate_count": 4,
            },
        )

    monkeypatch.setattr(onset_note_generator_mod, "estimate_pitch_for_region", fake_estimate_pitch_for_region)

    pipeline = TabPipeline(
        transcriber=FakeTranscriber(),
        rhythm_extract_fn=lambda _drums, **_kwargs: ([0.0, 0.25, 0.5, 0.75], [0.0], "madmom"),
        bar_builder_fn=lambda _beats, _downbeats, **_kwargs: [Bar(index=0, start_sec=0.0, end_sec=1.0, beats_sec=[0.0, 0.25, 0.5, 0.75])],
        onset_detect_fn=lambda _bass: [0.10, 0.34],
        cleanup_fn=lambda events, **_kwargs: list(events),
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
                fret=max(0, note.pitch_midi - 28),
            )
            for note in notes
        ],
        export_fn=lambda _notes, _bars, **_kwargs: ("\\tempo 120", [SyncPoint(bar_index=0, millisecond_offset=0)]),
    )
    pipeline._onset_note_generator = onset_note_generator_mod.OnsetNoteGenerator(
        audio_loader=lambda _path: ([0.1] * 8000, 8000),
        config=onset_note_generator_mod.OnsetNoteGeneratorConfig(
            onset_min_spacing_ms=70,
            onset_strength_threshold=0.2,
            onset_region_min_duration_ms=40,
            onset_region_max_duration_ms=180,
        ),
    )

    result = pipeline.run(Path("bass.wav"), Path("drums.wav"), bpm_hint=120.0, onset_recovery=False)

    assert len(called_regions) == 2
    assert [(round(note.start_sec, 2), note.pitch_midi) for note in quantized_inputs] == [(0.10, 33), (0.34, 35)]
    assert result.debug_info["raw_note_source_summary"]["onset_note_generator"] == 2
    assert (
        result.debug_info["pipeline_trace"]["pipeline_stats"]["onset_candidates"]["candidate_flow"]["pitch_corrected_region_count"]
        == 1
    )
