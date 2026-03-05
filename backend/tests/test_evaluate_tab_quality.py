from __future__ import annotations

import pytest

from scripts.evaluate_tab_quality import parse_alphatex_to_reference_notes
from scripts.evaluate_tab_quality import parse_cli_args


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
