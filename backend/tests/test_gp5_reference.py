from __future__ import annotations

from pathlib import Path

import pytest

from app.services.gp5_reference import ReferenceNote, parse_gp5_bass_track

TEST_SONGS = Path(__file__).resolve().parent.parent.parent / "test songs"
HYSTERIA_GP5 = TEST_SONGS / "Muse - Hysteria.gp5"
TROOPER_GP5 = TEST_SONGS / "Iron Maiden - The Trooper.gp5"


@pytest.mark.skipif(not HYSTERIA_GP5.exists(), reason="test song not available")
def test_parse_hysteria_bass_track() -> None:
    result = parse_gp5_bass_track(HYSTERIA_GP5)
    assert result.tempo > 0
    assert result.time_signature == (4, 4)
    assert len(result.notes) > 0
    assert len(result.bars) > 0
    # Hysteria bar 0 has 16 sixteenth notes on string 3
    bar0_notes = [n for n in result.notes if n.bar_index == 0]
    assert len(bar0_notes) == 16
    assert all(n.duration_beats == 0.25 for n in bar0_notes)


@pytest.mark.skipif(not TROOPER_GP5.exists(), reason="test song not available")
def test_parse_trooper_bass_track() -> None:
    result = parse_gp5_bass_track(TROOPER_GP5, encoding="latin1")
    assert result.tempo == 162
    assert len(result.notes) > 0
    bar0_notes = [n for n in result.notes if n.bar_index == 0]
    assert len(bar0_notes) == 10


def test_reference_note_has_required_fields() -> None:
    note = ReferenceNote(
        bar_index=0,
        beat_position=0.0,
        duration_beats=0.25,
        pitch_midi=33,
        string=3,
        fret=0,
    )
    assert note.pitch_midi == 33
    assert note.string == 3
    assert note.fret == 0
