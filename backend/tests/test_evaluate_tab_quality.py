from __future__ import annotations

from pathlib import Path

import pytest

from scripts.evaluate_tab_quality import parse_alphatex_to_reference_notes
from scripts.evaluate_tab_quality import parse_cli_args
from scripts.evaluate_tab_quality import resolve_input_paths


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
