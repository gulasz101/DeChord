from __future__ import annotations

from scripts.evaluate_tab_quality import parse_alphatex_to_reference_notes


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
