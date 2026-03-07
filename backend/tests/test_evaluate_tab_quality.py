from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.services.gp5_reference import ReferenceTab
from app.services.gp5_reference import ReferenceNote
from scripts.evaluate_tab_quality import ResolvedInputs
from scripts.evaluate_tab_quality import build_transcription_source_audit
from scripts.evaluate_tab_quality import evaluate_inputs
from scripts.evaluate_tab_quality import parse_alphatex_to_reference_notes
from scripts.evaluate_tab_quality import parse_cli_args
from scripts.evaluate_tab_quality import prefix_for_song_name
from scripts.evaluate_tab_quality import resolve_benchmark_config
from scripts.evaluate_tab_quality import resolve_input_paths
from scripts.evaluate_tab_quality import validate_inputs


def test_parse_alphatex_to_reference_notes_parses_notes_and_rests() -> None:
    alphatex = """\\tempo 120
\\ts 4 4
\\tuning E1 A1 D2 G2
0.4.4 r.8 2.3.8 | r.1
"""

    notes = parse_alphatex_to_reference_notes(alphatex)

    assert len(notes) == 2
    assert notes[0].bar_index == 0
    assert notes[0].beat_position == 0.0
    assert notes[0].pitch_midi == 28
    assert notes[1].beat_position == 1.5
    assert notes[1].pitch_midi == 35


def test_parse_cli_args_accepts_mp3_and_gp5_pair() -> None:
    args = parse_cli_args(
        [
            "--mp3",
            "../test songs/Muse - Hysteria.mp3",
            "--gp5",
            "../test songs/Muse - Hysteria.gp5",
        ]
    )

    assert args.mp3 == "../test songs/Muse - Hysteria.mp3"
    assert args.gp5 == "../test songs/Muse - Hysteria.gp5"


def test_parse_cli_args_accepts_optional_phase_suffix() -> None:
    args = parse_cli_args(
        [
            "--mp3",
            "../test songs/Muse - Hysteria.mp3",
            "--gp5",
            "../test songs/Muse - Hysteria.gp5",
            "--phase",
            "phase4_hysteria_final",
        ]
    )

    assert args.phase == "phase4_hysteria_final"


def test_parse_cli_args_accepts_benchmark_config_and_candidate_models() -> None:
    args = parse_cli_args(
        [
            "--mp3",
            "../test songs/Muse - Hysteria.mp3",
            "--gp5",
            "../test songs/Muse - Hysteria.gp5",
            "--config",
            "full",
            "--candidate-models",
            "htdemucs_ft,htdemucs_6s",
        ]
    )

    assert args.config == "full"
    assert args.candidate_models == "htdemucs_ft,htdemucs_6s"


@pytest.mark.parametrize(
    "argv",
    [
        ["--mp3", "../test songs/Muse - Hysteria.mp3"],
        ["--gp5", "../test songs/Muse - Hysteria.gp5"],
    ],
)
def test_parse_cli_args_rejects_half_pair(argv: list[str]) -> None:
    with pytest.raises(SystemExit):
        parse_cli_args(argv)


def test_parse_cli_args_accepts_song_dir_and_song_pair() -> None:
    args = parse_cli_args(
        [
            "--song-dir",
            "../test songs",
            "--song",
            "Muse - Hysteria",
        ]
    )

    assert args.song_dir == "../test songs"
    assert args.song == "Muse - Hysteria"


@pytest.mark.parametrize(
    "argv",
    [
        ["--song-dir", "../test songs"],
        ["--song", "Muse - Hysteria"],
    ],
)
def test_parse_cli_args_rejects_half_song_pair(argv: list[str]) -> None:
    with pytest.raises(SystemExit):
        parse_cli_args(argv)


def test_parse_cli_args_rejects_mixed_modes() -> None:
    with pytest.raises(SystemExit):
        parse_cli_args(
            [
                "--mp3",
                "../test songs/Muse - Hysteria.mp3",
                "--gp5",
                "../test songs/Muse - Hysteria.gp5",
                "--song-dir",
                "../test songs",
                "--song",
                "Muse - Hysteria",
            ]
        )


def test_resolve_input_paths_from_song_dir_and_song(tmp_path: Path) -> None:
    mp3 = tmp_path / "Muse - Hysteria.mp3"
    gp5 = tmp_path / "Muse - Hysteria.gp5"
    mp3.write_text("fake")
    gp5.write_text("fake")

    args = parse_cli_args(["--song-dir", str(tmp_path), "--song", "Muse - Hysteria"])
    resolved = resolve_input_paths(args)

    assert resolved.song_name == "Muse - Hysteria"
    assert resolved.mp3_path == mp3
    assert resolved.gp5_path == gp5


def test_resolve_input_paths_from_song_dir_requires_both_files(tmp_path: Path) -> None:
    (tmp_path / "Muse - Hysteria.mp3").write_text("fake")
    args = parse_cli_args(["--song-dir", str(tmp_path), "--song", "Muse - Hysteria"])

    with pytest.raises(FileNotFoundError, match="Missing song GP5"):
        resolve_input_paths(args)


def test_resolve_input_paths_from_explicit_paths(tmp_path: Path) -> None:
    mp3 = tmp_path / "Iron Maiden - The Trooper.mp3"
    gp5 = tmp_path / "Iron Maiden - The Trooper.gp5"
    mp3.write_text("fake")
    gp5.write_text("fake")

    args = parse_cli_args(["--mp3", str(mp3), "--gp5", str(gp5)])
    resolved = resolve_input_paths(args)

    assert resolved.song_name == "Iron Maiden - The Trooper"
    assert resolved.mp3_path == mp3.resolve()
    assert resolved.gp5_path == gp5.resolve()


def test_prefix_for_song_name_uses_artist_song_separator() -> None:
    assert prefix_for_song_name("Muse - Hysteria") == "muse__hysteria"
    assert prefix_for_song_name("Iron Maiden - The Trooper") == "iron_maiden__the_trooper"


def test_resolve_benchmark_config_full_enables_ensemble_and_candidate_selection() -> None:
    config = resolve_benchmark_config("full")

    assert config.name == "full"
    assert config.use_analysis_stem is True
    assert config.analysis_config.enable_bass_refinement is True
    assert config.analysis_config.enable_model_ensemble is True
    assert config.analysis_config.candidate_models == ["htdemucs_ft", "htdemucs"]


def test_resolve_benchmark_config_baseline_uses_raw_bass_stem() -> None:
    config = resolve_benchmark_config("baseline")

    assert config.name == "baseline"
    assert config.use_analysis_stem is False
    assert config.analysis_config is None


def test_validate_inputs_rejects_short_audio(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    mp3 = tmp_path / "track.mp3"
    gp5 = tmp_path / "track.gp5"
    mp3.write_text("fake")
    gp5.write_text("fake")

    monkeypatch.setattr("scripts.evaluate_tab_quality.probe_audio_duration_seconds", lambda _path: 9.99)
    monkeypatch.setattr(
        "scripts.evaluate_tab_quality.parse_gp5_bass_track",
        lambda _path, encoding=None: ReferenceTab(tempo=120.0, time_signature=(4, 4), bars=[SimpleNamespace(index=0)], notes=[SimpleNamespace()]),  # type: ignore[arg-type]
    )

    with pytest.raises(ValueError, match="at least 10 seconds"):
        validate_inputs(mp3, gp5)


def test_validate_inputs_rejects_missing_files(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="Missing MP3 file"):
        validate_inputs(tmp_path / "missing.mp3", tmp_path / "missing.gp5")


def test_validate_inputs_rejects_zero_gp5_notes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    mp3 = tmp_path / "track.mp3"
    gp5 = tmp_path / "track.gp5"
    mp3.write_text("fake")
    gp5.write_text("fake")

    monkeypatch.setattr("scripts.evaluate_tab_quality.probe_audio_duration_seconds", lambda _path: 11.0)
    monkeypatch.setattr(
        "scripts.evaluate_tab_quality.parse_gp5_bass_track",
        lambda _path, encoding=None: ReferenceTab(tempo=120.0, time_signature=(4, 4), bars=[SimpleNamespace(index=0)], notes=[]),  # type: ignore[arg-type]
    )

    with pytest.raises(ValueError, match="zero notes"):
        validate_inputs(mp3, gp5)


def test_evaluate_inputs_runs_full_pipeline_and_writes_deterministic_reports(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mp3 = tmp_path / "Muse - Hysteria.mp3"
    gp5 = tmp_path / "Muse - Hysteria.gp5"
    mp3.write_text("fake")
    gp5.write_text("fake")

    reference = ReferenceTab(
        tempo=120.0,
        time_signature=(4, 4),
        bars=[],
        notes=[
            ReferenceNote(
                bar_index=0,
                beat_position=0.0,
                duration_beats=1.0,
                pitch_midi=40,
                string=4,
                fret=12,
            )
        ],
    )
    monkeypatch.setattr("scripts.evaluate_tab_quality.validate_inputs", lambda _mp3, _gp5: (reference, 20.0))
    monkeypatch.setattr(
        "scripts.evaluate_tab_quality.split_to_stems",
        lambda _audio, _dir: [
            SimpleNamespace(stem_key="bass", relative_path=str(tmp_path / "bass.wav")),
            SimpleNamespace(stem_key="drums", relative_path=str(tmp_path / "drums.wav")),
        ],
    )
    monkeypatch.setattr("scripts.evaluate_tab_quality.REPORTS_DIR", tmp_path / "reports")
    monkeypatch.setattr("scripts.evaluate_tab_quality.time.perf_counter", lambda: 10.0)
    monkeypatch.setattr(
        "scripts.evaluate_tab_quality.BasicPitchTranscriber",
        lambda: SimpleNamespace(
            transcribe=lambda _bass: SimpleNamespace(
                engine="basic_pitch",
                raw_notes=[SimpleNamespace(start_sec=0.0, end_sec=0.5, pitch_midi=40, confidence=0.8)],
                debug_info={"basicpitch_octave_corrections_applied": 1},
            )
        ),
    )

    run_called: dict[str, object] = {"called": False}

    class FakePipeline:
        def run(self, bass_wav, drums_wav, *, bpm_hint, tab_generation_quality_mode):
            run_called["called"] = True
            run_called["bass_wav"] = str(bass_wav)
            run_called["drums_wav"] = str(drums_wav)
            run_called["quality"] = tab_generation_quality_mode
            return SimpleNamespace(
                alphatex="0.4.4 |",
                tempo_used=120.0,
                debug_info={
                    "derived_bpm": 120.0,
                    "rhythm_source": "librosa",
                    "raw_note_source_rows": [
                        {
                            "source": "basic_pitch",
                            "pitch_midi": 40,
                            "start_sec": 0.0,
                            "end_sec": 0.5,
                            "survived_cleanup": True,
                            "confidence_summary": {"confidence": 0.8},
                        }
                    ],
                    "dense_note_fusion_candidates": [],
                },
            )

    build_analysis_called = {"called": False}

    def fake_build_bass_analysis_stem(*, stems, output_dir, analysis_config, source_audio_path):
        build_analysis_called["called"] = True
        build_analysis_called["candidate_models"] = analysis_config.candidate_models
        return SimpleNamespace(
            path=tmp_path / "analysis" / "bass_analysis.wav",
            diagnostics={
                "selected_model": "htdemucs_ft",
                "candidate_scores": {"htdemucs_ft": 1.2, "htdemucs": 0.9},
                "ensemble_requested": 1,
                "guitar_assisted_cancellation_available": 1,
                "bleed_subtraction_applied": 1,
            },
        )

    monkeypatch.setattr("scripts.evaluate_tab_quality.build_bass_analysis_stem", fake_build_bass_analysis_stem)
    monkeypatch.setattr("scripts.evaluate_tab_quality.TabPipeline", FakePipeline)
    monkeypatch.setattr(
        "scripts.evaluate_tab_quality.compare_tabs",
        lambda *_args, **_kwargs: SimpleNamespace(
            precision=1.0,
            recall=1.0,
            f1_score=1.0,
            pitch_accuracy=1.0,
            fingering_accuracy=1.0,
            note_density_correlation=1.0,
            mean_timing_offset=0.0,
            onset_precision_ms=1.0,
            onset_recall_ms=1.0,
            onset_f1_ms=1.0,
            onset_precision_grid=1.0,
            onset_recall_grid=1.0,
            onset_f1_grid=1.0,
            octave_confusion={"exact": 1, "octave_plus_12": 0, "octave_minus_12": 0, "other": 0},
            total_ref_notes=1,
            total_gen_notes=1,
            total_matched=1,
        ),
    )

    output = evaluate_inputs(
        ResolvedInputs(song_name="Muse - Hysteria", mp3_path=mp3, gp5_path=gp5),
        quality="high_accuracy_aggressive",
        config_name="full",
    )

    assert run_called["called"] is True
    assert build_analysis_called["called"] is True
    assert run_called["bass_wav"].endswith("analysis/bass_analysis.wav")
    assert output["metrics_path"].endswith("muse__hysteria_metrics.json")
    assert output["debug_path"].endswith("muse__hysteria_debug.json")
    assert output["alphatex_path"].endswith("muse__hysteria_output.alphatex")
    assert output["transcription_audit_path"].endswith("muse__hysteria_transcription_audit.json")
    assert output["transcription_sources_path"].endswith("muse__hysteria_transcription_sources.json")

    audit = json.loads(Path(output["transcription_audit_path"]).read_text())
    assert audit["transcription_engine_used"] == "basic_pitch"
    assert audit["raw_note_count"] == 1
    assert "octave_error_count" in audit
    assert "non_octave_pitch_error_count" in audit
    source_audit = json.loads(Path(output["transcription_sources_path"]).read_text())
    assert source_audit["source_counts"] == {"basic_pitch": 1}
    assert source_audit["accepted_dense_candidates"] == 0
    metrics = json.loads(Path(output["metrics_path"]).read_text())
    assert metrics["benchmark_config"] == "full"
    assert metrics["runtime_seconds"]["total"] == 0.0
    assert metrics["analysis_diagnostics"]["selected_model"] == "htdemucs_ft"
    assert metrics["total_note_count_difference"] == 0


def test_evaluate_inputs_baseline_bypasses_analysis_stem(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mp3 = tmp_path / "Muse - Hysteria.mp3"
    gp5 = tmp_path / "Muse - Hysteria.gp5"
    mp3.write_text("fake")
    gp5.write_text("fake")

    reference = ReferenceTab(
        tempo=120.0,
        time_signature=(4, 4),
        bars=[],
        notes=[
            ReferenceNote(
                bar_index=0,
                beat_position=0.0,
                duration_beats=1.0,
                pitch_midi=40,
                string=4,
                fret=12,
            )
        ],
    )
    monkeypatch.setattr("scripts.evaluate_tab_quality.validate_inputs", lambda _mp3, _gp5: (reference, 20.0))
    monkeypatch.setattr(
        "scripts.evaluate_tab_quality.split_to_stems",
        lambda _audio, _dir: [
            SimpleNamespace(stem_key="bass", relative_path=str(tmp_path / "bass.wav")),
            SimpleNamespace(stem_key="drums", relative_path=str(tmp_path / "drums.wav")),
        ],
    )
    monkeypatch.setattr("scripts.evaluate_tab_quality.REPORTS_DIR", tmp_path / "reports")
    monkeypatch.setattr("scripts.evaluate_tab_quality.time.perf_counter", lambda: 10.0)
    monkeypatch.setattr(
        "scripts.evaluate_tab_quality.BasicPitchTranscriber",
        lambda: SimpleNamespace(
            transcribe=lambda _bass: SimpleNamespace(
                engine="basic_pitch",
                raw_notes=[SimpleNamespace(start_sec=0.0, end_sec=0.5, pitch_midi=40, confidence=0.8)],
                debug_info={},
            )
        ),
    )

    class FakePipeline:
        def run(self, bass_wav, drums_wav, *, bpm_hint, tab_generation_quality_mode):
            return SimpleNamespace(
                alphatex="0.4.4 |",
                tempo_used=120.0,
                debug_info={
                    "derived_bpm": 120.0,
                    "rhythm_source": "librosa",
                    "raw_note_source_rows": [],
                    "dense_note_fusion_candidates": [],
                },
            )

    def fail_build_bass_analysis_stem(**_kwargs):
        raise AssertionError("baseline config should not build analysis stem")

    monkeypatch.setattr("scripts.evaluate_tab_quality.build_bass_analysis_stem", fail_build_bass_analysis_stem)
    monkeypatch.setattr("scripts.evaluate_tab_quality.TabPipeline", FakePipeline)
    monkeypatch.setattr(
        "scripts.evaluate_tab_quality.compare_tabs",
        lambda *_args, **_kwargs: SimpleNamespace(
            precision=1.0,
            recall=1.0,
            f1_score=1.0,
            pitch_accuracy=1.0,
            fingering_accuracy=1.0,
            note_density_correlation=1.0,
            mean_timing_offset=0.0,
            onset_precision_ms=1.0,
            onset_recall_ms=1.0,
            onset_f1_ms=1.0,
            onset_precision_grid=1.0,
            onset_recall_grid=1.0,
            onset_f1_grid=1.0,
            octave_confusion={"exact": 1, "octave_plus_12": 0, "octave_minus_12": 0, "other": 0},
            total_ref_notes=1,
            total_gen_notes=1,
            total_matched=1,
            per_bar={0: SimpleNamespace(ref_count=1, gen_count=1)},
        ),
    )

    output = evaluate_inputs(
        ResolvedInputs(song_name="Muse - Hysteria", mp3_path=mp3, gp5_path=gp5),
        quality="high_accuracy_aggressive",
        config_name="baseline",
    )

    metrics = json.loads(Path(output["metrics_path"]).read_text())
    assert metrics["benchmark_config"] == "baseline"
    assert metrics["analysis_diagnostics"]["selected_model"] == "raw_bass_stem"


def test_evaluate_inputs_with_phase_writes_phase_suffixed_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mp3 = tmp_path / "Muse - Hysteria.mp3"
    gp5 = tmp_path / "Muse - Hysteria.gp5"
    mp3.write_text("fake")
    gp5.write_text("fake")

    reference = ReferenceTab(
        tempo=120.0,
        time_signature=(4, 4),
        bars=[],
        notes=[
            ReferenceNote(
                bar_index=0,
                beat_position=0.0,
                duration_beats=1.0,
                pitch_midi=40,
                string=4,
                fret=12,
            )
        ],
    )
    monkeypatch.setattr("scripts.evaluate_tab_quality.validate_inputs", lambda _mp3, _gp5: (reference, 20.0))
    monkeypatch.setattr(
        "scripts.evaluate_tab_quality.split_to_stems",
        lambda _audio, _dir: [
            SimpleNamespace(stem_key="bass", relative_path=str(tmp_path / "bass.wav")),
            SimpleNamespace(stem_key="drums", relative_path=str(tmp_path / "drums.wav")),
        ],
    )
    monkeypatch.setattr("scripts.evaluate_tab_quality.REPORTS_DIR", tmp_path / "reports")
    monkeypatch.setattr(
        "scripts.evaluate_tab_quality.BasicPitchTranscriber",
        lambda: SimpleNamespace(
            transcribe=lambda _bass: SimpleNamespace(
                engine="basic_pitch",
                raw_notes=[SimpleNamespace(start_sec=0.0, end_sec=0.5, pitch_midi=40, confidence=0.8)],
                debug_info={"basicpitch_octave_corrections_applied": 1},
            )
        ),
    )

    class FakePipeline:
        def run(self, bass_wav, drums_wav, *, bpm_hint, tab_generation_quality_mode):
            return SimpleNamespace(
                alphatex="0.4.4 |",
                tempo_used=120.0,
                debug_info={
                    "derived_bpm": 120.0,
                    "rhythm_source": "librosa",
                    "raw_note_source_rows": [],
                    "dense_note_fusion_candidates": [],
                },
            )

    monkeypatch.setattr("scripts.evaluate_tab_quality.TabPipeline", FakePipeline)
    monkeypatch.setattr(
        "scripts.evaluate_tab_quality.compare_tabs",
        lambda *_args, **_kwargs: SimpleNamespace(
            precision=1.0,
            recall=1.0,
            f1_score=1.0,
            pitch_accuracy=1.0,
            fingering_accuracy=1.0,
            note_density_correlation=1.0,
            mean_timing_offset=0.0,
            onset_precision_ms=1.0,
            onset_recall_ms=1.0,
            onset_f1_ms=1.0,
            onset_precision_grid=1.0,
            onset_recall_grid=1.0,
            onset_f1_grid=1.0,
            octave_confusion={"exact": 1, "octave_plus_12": 0, "octave_minus_12": 0, "other": 0},
            total_ref_notes=1,
            total_gen_notes=1,
            total_matched=1,
        ),
    )

    output = evaluate_inputs(
        ResolvedInputs(song_name="Muse - Hysteria", mp3_path=mp3, gp5_path=gp5),
        quality="high_accuracy_aggressive",
        phase="phase4_hysteria_final",
    )

    assert output["metrics_path"].endswith("muse__hysteria_phase4_hysteria_final_metrics.json")
    assert output["debug_path"].endswith("muse__hysteria_phase4_hysteria_final_debug.json")
    assert output["alphatex_path"].endswith("muse__hysteria_phase4_hysteria_final_output.alphatex")
    assert output["transcription_audit_path"].endswith(
        "muse__hysteria_phase4_hysteria_final_transcription_audit.json"
    )
    assert output["transcription_sources_path"].endswith(
        "muse__hysteria_phase4_hysteria_final_transcription_sources.json"
    )


def test_build_transcription_source_audit_counts_dense_matches_and_rejections() -> None:
    reference = ReferenceTab(
        tempo=120.0,
        time_signature=(4, 4),
        bars=[],
        notes=[
            ReferenceNote(
                bar_index=0,
                beat_position=0.0,
                duration_beats=1.0,
                pitch_midi=40,
                string=4,
                fret=12,
            ),
            ReferenceNote(
                bar_index=0,
                beat_position=1.0,
                duration_beats=1.0,
                pitch_midi=43,
                string=3,
                fret=10,
            ),
        ],
    )

    audit = build_transcription_source_audit(
        reference,
        {
            "raw_note_source_rows": [
                {
                    "source": "basic_pitch",
                    "pitch_midi": 40,
                    "start_sec": 0.0,
                    "end_sec": 0.4,
                    "survived_cleanup": True,
                    "confidence_summary": {"confidence": 0.9},
                },
                {
                    "source": "hybrid_merged",
                    "pitch_midi": 43,
                    "start_sec": 0.5,
                    "end_sec": 0.7,
                    "survived_cleanup": True,
                    "confidence_summary": {"raw_pitch_midi": 55},
                },
            ],
            "dense_note_fusion_candidates": [
                {"accepted": False, "rejection_reason": "pitch_far_from_anchor"},
                {"accepted": True, "rejection_reason": None},
            ],
        },
    )

    assert audit["source_counts"] == {"basic_pitch": 1, "hybrid_merged": 1}
    assert audit["accepted_dense_candidates"] == 1
    assert audit["rejected_dense_candidates"] == 1
    assert audit["accepted_dense_with_reference_onset_match"] == 1
    assert audit["accepted_dense_with_reference_onset_pitch_match"] == 1
    assert audit["rejected_dense_reasons"] == {"pitch_far_from_anchor": 1}
