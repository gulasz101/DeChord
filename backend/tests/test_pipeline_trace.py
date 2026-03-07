from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.services.alphatex_exporter import SyncPoint
from app.services.bass_transcriber import BasicPitchTranscriber, BassTranscriptionResult, RawNoteEvent
from app.services.dense_note_generator import DenseNoteCandidate
from app.services.fingering import FingeredNote
from app.services.onset_note_generator import OnsetNoteCandidate
from app.services.pipeline_trace import build_pipeline_trace_report
from app.services.quantization import QuantizedNote
from app.services.rhythm_grid import Bar
from app.services.tab_pipeline import TabPipeline


def test_basic_pitch_transcriber_emits_stage_metrics() -> None:
    raw_notes = [
        RawNoteEvent(pitch_midi=40, start_sec=0.0, end_sec=0.24, confidence=0.95),
        RawNoteEvent(pitch_midi=52, start_sec=0.25, end_sec=0.30, confidence=0.92),
        RawNoteEvent(pitch_midi=40, start_sec=0.31, end_sec=0.56, confidence=0.94),
        RawNoteEvent(pitch_midi=43, start_sec=0.80, end_sec=0.84, confidence=0.20),
    ]

    transcriber = BasicPitchTranscriber(
        midi_transcribe_fn=lambda _path: b"MThd",
        parse_notes_fn=lambda _midi_bytes: list(raw_notes),
    )

    result = transcriber.transcribe(Path("bass.wav"))

    pipeline_stats = result.debug_info["pipeline_trace"]["pipeline_stats"]

    assert set(pipeline_stats) == {"basic_pitch_raw", "pitch_stabilized", "admission_filtered"}
    assert pipeline_stats["basic_pitch_raw"]["note_count"] == 4
    assert pipeline_stats["basic_pitch_raw"]["candidate_flow"] == {
        "pre_filter_note_count": 4,
        "post_filter_note_count": 4,
        "filtered_out_note_count": 0,
        "filter_rejection_histogram": {},
    }
    assert pipeline_stats["pitch_stabilized"]["note_count"] == 2
    assert pipeline_stats["admission_filtered"]["note_count"] == 1
    assert pipeline_stats["admission_filtered"]["notes_removed_by_stage"] == 1
    assert isinstance(pipeline_stats["pitch_stabilized"], dict)
    assert isinstance(pipeline_stats["admission_filtered"], dict)


def test_tab_pipeline_emits_all_stage_metrics_and_consistent_counts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stage1 = [
        RawNoteEvent(pitch_midi=40, start_sec=0.0, end_sec=0.20, confidence=0.9),
        RawNoteEvent(pitch_midi=40, start_sec=0.30, end_sec=0.50, confidence=0.9),
    ]
    stage2 = list(stage1)
    stage3 = [stage1[0]]

    class FakeTranscriber:
        def transcribe(self, _bass_wav: Path) -> BassTranscriptionResult:
            return BassTranscriptionResult(
                engine="basic_pitch",
                midi_bytes=b"MThd",
                raw_notes=list(stage3),
                debug_info={
                    "pipeline_trace": {
                        "pipeline_stats": {
                            "basic_pitch_raw": {
                                "note_count": 2,
                                "average_duration_ms": 200.0,
                                "median_duration_ms": 200.0,
                                "short_note_threshold_ms": 80,
                                "short_note_count": 0,
                                "octave_jump_count": 0,
                                "confidence_stats": {"mean": 0.9, "min": 0.9, "max": 0.9},
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
                                "average_duration_ms": 200.0,
                                "median_duration_ms": 200.0,
                                "short_note_threshold_ms": 80,
                                "short_note_count": 0,
                                "octave_jump_count": 0,
                                "confidence_stats": {"mean": 0.9, "min": 0.9, "max": 0.9},
                                "notes_added_by_stage": 0,
                                "notes_removed_by_stage": 0,
                                "notes_merged_by_stage": 0,
                                "notes_altered_by_stage": 0,
                            },
                            "admission_filtered": {
                                "note_count": 1,
                                "average_duration_ms": 200.0,
                                "median_duration_ms": 200.0,
                                "short_note_threshold_ms": 80,
                                "short_note_count": 0,
                                "octave_jump_count": 0,
                                "confidence_stats": {"mean": 0.9, "min": 0.9, "max": 0.9},
                                "notes_added_by_stage": 0,
                                "notes_removed_by_stage": 1,
                                "notes_merged_by_stage": 0,
                                "notes_altered_by_stage": 0,
                            },
                            "onset_candidates": {
                                "note_count": 0,
                                "average_duration_ms": 0.0,
                                "median_duration_ms": 0.0,
                                "short_note_threshold_ms": 40,
                                "short_note_count": 0,
                                "octave_jump_count": 0,
                                "pitch_range": {"min": None, "max": None},
                                "confidence_stats": {"mean": None, "min": None, "max": None},
                                "notes_added_by_stage": 0,
                                "notes_removed_by_stage": 0,
                                "notes_merged_by_stage": 0,
                                "notes_altered_by_stage": 0,
                                "candidate_flow": {
                                    "generator_enabled": True,
                                    "generator_mode": "merged",
                                    "proposed_note_count": 0,
                                    "accepted_note_count": 0,
                                    "rejected_note_count": 0,
                                    "materially_changed_final_note_count": False,
                                    "analyzed_region_count": 0,
                                    "accepted_pitch_count": 0,
                                    "rejected_weak_region_count": 0,
                                    "average_region_pitch_confidence": None,
                                    "octave_suppressed_count": 0,
                                    "pitch_corrected_region_count": 0,
                                    "accepted_pitch_range": {"min": None, "max": None},
                                },
                            },
                        }
                    }
                },
            )

    bars = [Bar(index=0, start_sec=0.0, end_sec=1.0, beats_sec=[0.0, 0.25, 0.5, 0.75])]
    dense_candidates = [
        DenseNoteCandidate(pitch_midi=40, start_sec=0.10, end_sec=0.18, confidence=0.92),
        DenseNoteCandidate(pitch_midi=40, start_sec=0.20, end_sec=0.28, confidence=0.91),
    ]
    quantize_inputs: list[RawNoteEvent] = []

    def fake_quantize(events, _grid, **_kwargs):
        quantize_inputs[:] = list(events)
        return [
            QuantizedNote(
                bar_index=0,
                beat_position=float(index),
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
        onset_detect_fn=lambda _bass: [0.05, 0.12, 0.19, 0.26, 0.33, 0.40],
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
                "generate": lambda self, **_kwargs: list(dense_candidates),
            },
        )(),
    )
    monkeypatch.setattr(TabPipeline, "_bar_rms_values", staticmethod(lambda _bass, _bars: [0.1]))
    monkeypatch.setattr(TabPipeline, "_bar_onset_peaks", staticmethod(lambda _bass, _bars: [6]))
    monkeypatch.setattr(
        TabPipeline,
        "_confidence_gate_dense_note_candidates",
        staticmethod(
            lambda candidates, **_kwargs: (
                [candidates[0]],
                [{"accepted": True, "rejection_reason": None}, {"accepted": False, "rejection_reason": "weak_local_support"}],
            )
        ),
    )

    result = pipeline.run(
        Path("bass.wav"),
        Path("drums.wav"),
        bpm_hint=120.0,
        tab_generation_quality_mode="high_accuracy_aggressive",
        onset_recovery=False,
    )

    pipeline_stats = result.debug_info["pipeline_trace"]["pipeline_stats"]

    assert set(pipeline_stats) == {
        "basic_pitch_raw",
        "pitch_stabilized",
        "admission_filtered",
        "onset_candidates",
        "dense_candidates",
        "dense_accepted",
        "final_notes",
    }
    assert pipeline_stats["onset_candidates"]["candidate_flow"] == {
        "generator_enabled": True,
        "generator_mode": "merged",
        "proposed_note_count": 0,
        "accepted_note_count": 0,
        "rejected_note_count": 0,
        "materially_changed_final_note_count": False,
        "analyzed_region_count": 0,
        "accepted_pitch_count": 0,
        "rejected_weak_region_count": 0,
        "average_region_pitch_confidence": None,
        "octave_suppressed_count": 0,
        "pitch_corrected_region_count": 0,
        "accepted_pitch_range": {"min": None, "max": None},
    }
    assert pipeline_stats["dense_candidates"]["note_count"] == 2
    assert pipeline_stats["dense_candidates"]["candidate_flow"] == {
        "proposed_note_count": 2,
    }
    assert pipeline_stats["dense_accepted"]["note_count"] == 1
    assert pipeline_stats["dense_accepted"]["candidate_flow"] == {
        "proposed_note_count": 2,
        "accepted_note_count": 1,
        "rejected_note_count": 1,
        "rejection_histogram": {"weak_local_support": 1},
    }
    assert pipeline_stats["dense_accepted"]["note_count"] <= pipeline_stats["dense_candidates"]["note_count"]
    assert pipeline_stats["final_notes"]["note_count"] == len(quantize_inputs)
    assert result.debug_info["quantized_note_count"] == pipeline_stats["final_notes"]["note_count"]


def test_tab_pipeline_onset_trace_reports_region_pitch_metrics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DECHORD_ONSET_NOTE_GENERATOR_ENABLE", "1")
    monkeypatch.setenv("DECHORD_ONSET_NOTE_GENERATOR_MODE", "merged")

    class FakeTranscriber:
        def transcribe(self, _bass_wav: Path) -> BassTranscriptionResult:
            return BassTranscriptionResult(
                engine="basic_pitch",
                midi_bytes=b"MThd",
                raw_notes=[],
                debug_info={"pipeline_trace": {"pipeline_stats": {}}},
            )

    bars = [Bar(index=0, start_sec=0.0, end_sec=1.0, beats_sec=[0.0, 0.25, 0.5, 0.75])]
    quantize_inputs: list[RawNoteEvent] = []

    def fake_quantize(events, _grid, **_kwargs):
        quantize_inputs[:] = list(events)
        return [
            QuantizedNote(
                bar_index=0,
                beat_position=0.0,
                duration_beats=0.5,
                pitch_midi=note.pitch_midi,
                start_sec=note.start_sec,
                end_sec=note.end_sec,
            )
            for note in events
        ]

    pipeline = TabPipeline(
        transcriber=FakeTranscriber(),
        rhythm_extract_fn=lambda _drums, **_kwargs: ([0.0, 0.25, 0.5, 0.75], [0.0], "madmom"),
        bar_builder_fn=lambda _beats, _downbeats, **_kwargs: bars,
        onset_detect_fn=lambda _bass: [0.10, 0.34, 0.58],
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
                "generate": lambda self, _bass_wav, onset_times=None: [
                    OnsetNoteCandidate(
                        pitch_midi=33,
                        start_sec=0.10,
                        end_sec=0.24,
                        confidence=0.72,
                        support={
                            "region_start_sec": 0.10,
                            "region_end_sec": 0.24,
                            "initial_pitch_midi": 45,
                            "octave_suppressed": True,
                            "pitch_corrected": True,
                            "region_pitch_confidence": 0.72,
                            "analyzed_region_count": 3,
                            "accepted_pitch_count": 2,
                            "rejected_weak_region_count": 1,
                        },
                    ),
                    OnsetNoteCandidate(
                        pitch_midi=35,
                        start_sec=0.34,
                        end_sec=0.46,
                        confidence=0.66,
                        support={
                            "region_start_sec": 0.34,
                            "region_end_sec": 0.46,
                            "initial_pitch_midi": 35,
                            "octave_suppressed": False,
                            "pitch_corrected": False,
                            "region_pitch_confidence": 0.66,
                            "analyzed_region_count": 3,
                            "accepted_pitch_count": 2,
                            "rejected_weak_region_count": 1,
                        },
                    ),
                ],
            },
        )(),
    )

    result = pipeline.run(Path("bass.wav"), Path("drums.wav"), bpm_hint=120.0, onset_recovery=False)

    onset_flow = result.debug_info["pipeline_trace"]["pipeline_stats"]["onset_candidates"]["candidate_flow"]

    assert len(quantize_inputs) == 2
    assert onset_flow["analyzed_region_count"] == 3
    assert onset_flow["accepted_pitch_count"] == 2
    assert onset_flow["rejected_weak_region_count"] == 1
    assert onset_flow["octave_suppressed_count"] == 1
    assert onset_flow["pitch_corrected_region_count"] == 1
    assert onset_flow["average_region_pitch_confidence"] == pytest.approx(0.69)
    assert onset_flow["accepted_pitch_range"] == {"min": 33, "max": 35}


def test_build_pipeline_trace_report_has_stable_json_structure() -> None:
    report = build_pipeline_trace_report(
        song_name="Muse - Hysteria",
        pipeline_stats={
            "basic_pitch_raw": {
                "note_count": 2,
                "average_duration_ms": 120.0,
                "median_duration_ms": 120.0,
                "short_note_threshold_ms": 80,
                "short_note_count": 1,
                "octave_jump_count": 0,
                "confidence_stats": {"mean": 0.8, "min": 0.7, "max": 0.9},
                "notes_added_by_stage": 0,
                "notes_removed_by_stage": 0,
                "notes_merged_by_stage": 0,
                "notes_altered_by_stage": 0,
                "candidate_flow": {
                    "pre_filter_note_count": 3,
                    "post_filter_note_count": 2,
                    "filtered_out_note_count": 1,
                    "filter_rejection_histogram": {"below_confidence_floor": 1},
                },
            },
            "pitch_stabilized": {
                "note_count": 1,
                "average_duration_ms": 240.0,
                "median_duration_ms": 240.0,
                "short_note_threshold_ms": 80,
                "short_note_count": 0,
                "octave_jump_count": 0,
                "confidence_stats": {"mean": 0.85, "min": 0.85, "max": 0.85},
                "notes_added_by_stage": 0,
                "notes_removed_by_stage": 1,
                "notes_merged_by_stage": 1,
                "notes_altered_by_stage": 1,
            },
        },
    )

    payload = json.loads(json.dumps(report, sort_keys=True))

    assert payload == {
        "pipeline_stats": {
            "basic_pitch_raw": {
                "average_duration_ms": 120.0,
                "candidate_flow": {
                    "filter_rejection_histogram": {"below_confidence_floor": 1},
                    "filtered_out_note_count": 1,
                    "post_filter_note_count": 2,
                    "pre_filter_note_count": 3,
                },
                "confidence_stats": {"max": 0.9, "mean": 0.8, "min": 0.7},
                "median_duration_ms": 120.0,
                "note_count": 2,
                "notes_added_by_stage": 0,
                "notes_altered_by_stage": 0,
                "notes_merged_by_stage": 0,
                "notes_removed_by_stage": 0,
                "octave_jump_count": 0,
                "short_note_count": 1,
                "short_note_threshold_ms": 80,
            },
            "pitch_stabilized": {
                "average_duration_ms": 240.0,
                "confidence_stats": {"max": 0.85, "mean": 0.85, "min": 0.85},
                "median_duration_ms": 240.0,
                "note_count": 1,
                "notes_added_by_stage": 0,
                "notes_altered_by_stage": 1,
                "notes_merged_by_stage": 1,
                "notes_removed_by_stage": 1,
                "octave_jump_count": 0,
                "short_note_count": 0,
                "short_note_threshold_ms": 80,
            },
        },
        "song": "Muse - Hysteria",
    }
