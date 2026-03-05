from app.tabs import (
    MidiNoteEvent,
    TabNote,
    build_gp5_from_tab_positions,
    map_midi_to_eadg_positions,
)


def test_map_midi_to_eadg_positions_limits_to_4_string_range():
    events = [
        MidiNoteEvent(note=40, start=0.0, end=0.5),  # E1
        MidiNoteEvent(note=52, start=0.5, end=1.0),  # E2
        MidiNoteEvent(note=57, start=1.0, end=1.5),  # A2
    ]

    tab_notes = map_midi_to_eadg_positions(
        b"ignored",
        parse_midi_fn=lambda _midi: events,
    )

    assert len(tab_notes) == 3
    assert all(1 <= note.string <= 4 for note in tab_notes)
    assert all(0 <= note.fret <= 24 for note in tab_notes)


def test_map_midi_to_eadg_positions_is_deterministic():
    events = [
        MidiNoteEvent(note=43, start=0.0, end=0.5),
        MidiNoteEvent(note=47, start=0.5, end=1.0),
        MidiNoteEvent(note=50, start=1.0, end=1.5),
    ]

    first = map_midi_to_eadg_positions(b"x", parse_midi_fn=lambda _midi: events)
    second = map_midi_to_eadg_positions(b"x", parse_midi_fn=lambda _midi: events)

    assert first == second


def test_build_gp5_from_tab_positions_returns_non_empty_bytes():
    tab_notes = [
        TabNote(string=4, fret=0, start=0.0, end=0.5, midi_note=40),
        TabNote(string=3, fret=2, start=0.5, end=1.0, midi_note=47),
    ]

    gp_bytes = build_gp5_from_tab_positions(tab_notes)

    assert isinstance(gp_bytes, bytes)
    assert len(gp_bytes) > 16


def test_build_gp5_from_tab_positions_splits_into_multiple_measures():
    import tempfile
    from pathlib import Path

    import guitarpro

    tab_notes = []
    for idx in range(24):
        tab_notes.append(
            TabNote(
                string=4,
                fret=(idx % 8),
                start=idx * 0.25,
                end=(idx * 0.25) + 0.25,
                midi_note=40 + (idx % 12),
            )
        )

    gp_bytes = build_gp5_from_tab_positions(tab_notes)
    with tempfile.TemporaryDirectory(prefix="dechord-tabs-test-") as tmp_dir:
        gp_path = Path(tmp_dir) / "test.gp5"
        gp_path.write_bytes(gp_bytes)
        parsed = guitarpro.parse(gp_path)

    assert len(parsed.measureHeaders) > 1
    assert len(parsed.tracks[0].measures) > 1
