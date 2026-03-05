from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from app.services.gp5_reference import ReferenceTab
from app.services.gp5_reference import ReferenceNote
from scripts.evaluate_tab_quality import ResolvedInputs
from scripts.evaluate_tab_quality import evaluate_inputs
from scripts.evaluate_tab_quality import parse_alphatex_to_reference_notes
from scripts.evaluate_tab_quality import prefix_for_song_name
from scripts.evaluate_tab_quality import parse_cli_args
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
                debug_info={"derived_bpm": 120.0, "rhythm_source": "librosa"},
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
    )

    assert run_called["called"] is True
    assert output["metrics_path"].endswith("muse__hysteria_metrics.json")
    assert output["debug_path"].endswith("muse__hysteria_debug.json")
    assert output["alphatex_path"].endswith("muse__hysteria_output.alphatex")
