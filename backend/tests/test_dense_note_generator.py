from __future__ import annotations

from app.services.bass_transcriber import RawNoteEvent
from app.services.dense_note_generator import DenseNoteCandidate
from app.services.dense_note_generator import DenseNoteGenerator


def test_dense_note_generator_targets_missing_onsets_and_anchors_repeated_pitch() -> None:
    generator = DenseNoteGenerator(
        pitch_estimator=lambda _audio, _sr, onset, end, anchor_pitch: (
            {0.20: (52, 0.58), 0.40: (39, 0.66)}[round(onset, 2)]
        ),
        audio_loader=lambda _path: ([0.0] * 32, 22050),
    )
    base_notes = [
        RawNoteEvent(pitch_midi=40, start_sec=0.10, end_sec=0.18, confidence=0.9),
        RawNoteEvent(pitch_midi=40, start_sec=0.55, end_sec=0.62, confidence=0.9),
    ]
    context_notes = [
        RawNoteEvent(pitch_midi=40, start_sec=0.10, end_sec=0.18, confidence=0.9),
        RawNoteEvent(pitch_midi=40, start_sec=0.55, end_sec=0.62, confidence=0.9),
        RawNoteEvent(pitch_midi=40, start_sec=0.70, end_sec=0.78, confidence=0.9),
    ]

    candidates = generator.generate(
        bass_wav="ignored.wav",
        window_start=0.0,
        window_end=0.8,
        onset_times=[0.10, 0.20, 0.40, 0.55],
        base_notes=base_notes,
        context_notes=context_notes,
    )

    assert [(round(note.start_sec, 2), note.pitch_midi) for note in candidates] == [(0.2, 40), (0.4, 40)]
    assert all(note.source_tag == "dense_note_generator" for note in candidates)
    assert candidates[0].support["repeated_note_mode"] is True
    assert candidates[0].support["anchor_pitch"] == 40
    assert candidates[0].support["raw_pitch_midi"] == 52
    assert candidates[0].confidence > 0.6


def test_dense_note_generator_drops_unpitched_or_low_confidence_candidates() -> None:
    calls: list[float] = []

    def estimator(_audio, _sr, onset, end, anchor_pitch):
        calls.append(round(onset, 2))
        if round(onset, 2) == 0.12:
            return None
        return (34, 0.12)

    generator = DenseNoteGenerator(
        pitch_estimator=estimator,
        audio_loader=lambda _path: ([0.0] * 32, 22050),
    )

    candidates = generator.generate(
        bass_wav="ignored.wav",
        window_start=0.0,
        window_end=0.5,
        onset_times=[0.12, 0.28],
        base_notes=[],
        context_notes=[RawNoteEvent(pitch_midi=34, start_sec=0.0, end_sec=0.08, confidence=0.8)],
    )

    assert calls == [0.12, 0.28]
    assert candidates == []


def test_dense_note_generator_caps_dense_onset_windows_to_missing_candidates() -> None:
    observed_onsets: list[float] = []

    def estimator(_audio, _sr, onset, end, anchor_pitch):
        observed_onsets.append(round(onset, 2))
        return (40, 0.8)

    generator = DenseNoteGenerator(
        pitch_estimator=estimator,
        audio_loader=lambda _path: ([0.0] * 32, 22050),
        minimum_onset_gap_sec=0.08,
        max_window_onsets=3,
    )

    candidates = generator.generate(
        bass_wav="ignored.wav",
        window_start=0.0,
        window_end=1.0,
        onset_times=[0.1, 0.12, 0.2, 0.4, 0.6, 0.8],
        base_notes=[RawNoteEvent(pitch_midi=40, start_sec=0.1, end_sec=0.16, confidence=0.9)],
        context_notes=[RawNoteEvent(pitch_midi=40, start_sec=0.1, end_sec=0.16, confidence=0.9)],
    )

    assert observed_onsets == [0.4, 0.6, 0.8]
    assert [round(candidate.start_sec, 2) for candidate in candidates] == [0.4, 0.6, 0.8]


def test_dense_note_candidate_to_raw_note_preserves_core_fields() -> None:
    candidate = DenseNoteCandidate(
        pitch_midi=38,
        start_sec=1.0,
        end_sec=1.14,
        confidence=0.73,
        source_tag="dense_note_generator",
        support={"anchor_pitch": 38},
    )

    raw_note = candidate.to_raw_note()

    assert raw_note.pitch_midi == 38
    assert raw_note.start_sec == 1.0
    assert raw_note.end_sec == 1.14
    assert raw_note.confidence == 0.73
