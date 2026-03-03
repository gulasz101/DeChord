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
