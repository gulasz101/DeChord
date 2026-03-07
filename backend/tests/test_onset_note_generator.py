from __future__ import annotations

import math

import pytest

from app.services.bass_transcriber import RawNoteEvent
from app.services.onset_note_generator import (
    OnsetNoteGenerator,
    OnsetNoteGeneratorConfig,
    build_onset_regions,
    detect_bass_onsets,
    estimate_pitch_for_region,
)


def _sine_pulse_signal(
    *,
    sample_rate: int,
    pulses: list[tuple[float, float, float]],
    duration_sec: float,
) -> list[float]:
    samples: list[float] = []
    total_samples = int(sample_rate * duration_sec)
    for idx in range(total_samples):
        t = idx / sample_rate
        value = 0.0
        for start_sec, pulse_duration_sec, frequency_hz in pulses:
            rel = t - start_sec
            if 0.0 <= rel < pulse_duration_sec:
                envelope = min(1.0, rel / 0.01) * min(1.0, (pulse_duration_sec - rel) / 0.01)
                value += 0.85 * envelope * math.sin(2.0 * math.pi * frequency_hz * rel)
        samples.append(value)
    return samples


def test_detect_bass_onsets_finds_expected_synthetic_pulses() -> None:
    sr = 4000
    audio = _sine_pulse_signal(
        sample_rate=sr,
        pulses=[(0.10, 0.12, 55.0), (0.36, 0.12, 62.0), (0.64, 0.12, 73.0)],
        duration_sec=1.0,
    )

    onsets = detect_bass_onsets(
        audio,
        sr,
        config=OnsetNoteGeneratorConfig(onset_min_spacing_ms=70, onset_strength_threshold=0.2),
    )

    assert len(onsets) == 3
    assert onsets == pytest.approx([0.10, 0.36, 0.64], abs=0.03)


def test_detect_bass_onsets_respects_spacing_and_bounds_noise() -> None:
    sr = 4000
    audio = _sine_pulse_signal(
        sample_rate=sr,
        pulses=[(0.10, 0.08, 55.0), (0.13, 0.08, 55.0), (0.50, 0.08, 55.0)],
        duration_sec=1.0,
    )
    audio = [sample + (0.015 if index % 17 == 0 else -0.015) for index, sample in enumerate(audio)]

    onsets = detect_bass_onsets(
        audio,
        sr,
        config=OnsetNoteGeneratorConfig(onset_min_spacing_ms=70, onset_strength_threshold=0.35),
    )

    assert len(onsets) == 2
    assert onsets[0] == pytest.approx(0.10, abs=0.04)
    assert onsets[1] == pytest.approx(0.50, abs=0.04)


def test_build_onset_regions_enforces_min_and_max_duration() -> None:
    regions = build_onset_regions(
        [0.10, 0.20, 0.60],
        audio_duration_sec=0.95,
        config=OnsetNoteGeneratorConfig(
            onset_region_min_duration_ms=50,
            onset_region_max_duration_ms=180,
        ),
    )

    assert regions == pytest.approx(
        [
            (0.10, 0.20),
            (0.20, 0.38),
            (0.60, 0.78),
        ],
        abs=0.001,
    )


def test_estimate_pitch_for_region_prefers_bass_fundamental_over_octave() -> None:
    sr = 8000
    duration_sec = 0.18
    total_samples = int(sr * duration_sec)
    audio = []
    for idx in range(total_samples):
        t = idx / sr
        audio.append(
            (0.22 * math.sin(2.0 * math.pi * 55.0 * t))
            + (0.65 * math.sin(2.0 * math.pi * 110.0 * t))
            + (0.20 * math.sin(2.0 * math.pi * 165.0 * t))
        )

    estimate = estimate_pitch_for_region(
        audio,
        sr,
        region=(0.0, duration_sec),
        config=OnsetNoteGeneratorConfig(),
    )

    assert estimate is not None
    pitch_midi, confidence = estimate
    assert pitch_midi == 33
    assert confidence >= 0.35


def test_generate_onset_note_candidates_emits_bounded_candidates() -> None:
    sr = 4000
    audio = _sine_pulse_signal(
        sample_rate=sr,
        pulses=[(0.05, 0.10, 55.0), (0.28, 0.10, 62.0), (0.53, 0.10, 73.0)],
        duration_sec=0.9,
    )
    generator = OnsetNoteGenerator(
        audio_loader=lambda _path: (audio, sr),
        config=OnsetNoteGeneratorConfig(
            onset_min_spacing_ms=70,
            onset_strength_threshold=0.2,
            onset_region_min_duration_ms=40,
            onset_region_max_duration_ms=180,
        ),
    )

    candidates = generator.generate("synthetic.wav")

    assert [(round(note.start_sec, 2), note.pitch_midi) for note in candidates] == [
        (0.05, 33),
        (0.28, 38),
        (0.53, 43),
    ]
    assert all(note.end_sec > note.start_sec for note in candidates)
    assert all(note.confidence > 0.0 for note in candidates)
    assert all(28 <= note.pitch_midi <= 64 for note in candidates)
    assert all(note.source_tag == "onset_note_generator" for note in candidates)


def test_generate_onset_note_candidates_rejects_empty_or_implausible_regions() -> None:
    generator = OnsetNoteGenerator(
        audio_loader=lambda _path: ([0.0] * 8000, 8000),
        config=OnsetNoteGeneratorConfig(onset_strength_threshold=0.9),
    )

    assert generator.generate("empty.wav") == []
