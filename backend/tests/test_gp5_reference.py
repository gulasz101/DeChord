from __future__ import annotations

import pytest
from pathlib import Path

from app.services.gp5_reference import parse_gp5_bass_track


def test_parse_gp5_bass_track_reads_bass_notes() -> None:
    gp5 = Path(__file__).resolve().parent.parent.parent / "test songs" / "Muse - Hysteria.gp5"
    if not gp5.exists():
        pytest.skip("Fixture 'Muse - Hysteria.gp5' not present in this environment")

    reference = parse_gp5_bass_track(gp5)

    assert reference.tempo > 0
    assert reference.time_signature == (4, 4)
    assert len(reference.bars) > 0
    assert len(reference.notes) > 0

    first = reference.notes[0]
    assert first.bar_index >= 0
    assert 0.0 <= first.beat_position < 4.0
    assert first.pitch_midi >= 28
