from __future__ import annotations

import math

import pytest

from app.services.bass_transcriber import RawNoteEvent
from app.services.onset_note_generator import (
    OnsetNoteGenerator,
    OnsetNoteGeneratorConfig,
    OnsetRegionPitchEstimate,
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
    assert isinstance(estimate, OnsetRegionPitchEstimate)
    assert estimate.pitch_midi == 33
    assert estimate.confidence >= 0.35
    assert estimate.support["octave_suppressed"] is True
    assert estimate.support["initial_pitch_midi"] == 45
    assert estimate.support["evaluated_candidate_count"] <= 6


def test_estimate_pitch_for_region_keeps_true_higher_pitch_without_lower_support() -> None:
    sr = 8000
    duration_sec = 0.16
    total_samples = int(sr * duration_sec)
    audio = []
    for idx in range(total_samples):
        t = idx / sr
        audio.append(
            (0.08 * math.sin(2.0 * math.pi * 55.0 * t))
            + (0.85 * math.sin(2.0 * math.pi * 110.0 * t))
            + (0.35 * math.sin(2.0 * math.pi * 220.0 * t))
        )

    estimate = estimate_pitch_for_region(
        audio,
        sr,
        region=(0.0, duration_sec),
        config=OnsetNoteGeneratorConfig(),
    )

    assert estimate is not None
    assert estimate.pitch_midi == 45
    assert estimate.support["octave_suppressed"] is False
    assert estimate.support["initial_pitch_midi"] == 45


def test_estimate_pitch_for_region_rejects_noisy_weak_regions() -> None:
    sr = 8000
    duration_sec = 0.18
    total_samples = int(sr * duration_sec)
    audio = [
        (0.002 * math.sin(2.0 * math.pi * 170.0 * (idx / sr))) + (0.0015 if idx % 29 == 0 else -0.0015)
        for idx in range(total_samples)
    ]

    estimate = estimate_pitch_for_region(
        audio,
        sr,
        region=(0.0, duration_sec),
        config=OnsetNoteGeneratorConfig(),
    )

    assert estimate is None


def test_estimate_pitch_for_region_uses_frame_consensus_after_harmonic_attack() -> None:
    sr = 8000
    duration_sec = 0.20
    total_samples = int(sr * duration_sec)
    audio = []
    for idx in range(total_samples):
        t = idx / sr
        if t < 0.035:
            audio.append(
                (0.04 * math.sin(2.0 * math.pi * 55.0 * t))
                + (0.92 * math.sin(2.0 * math.pi * 110.0 * t))
                + (0.25 * math.sin(2.0 * math.pi * 220.0 * t))
            )
            continue
        audio.append(
            (0.32 * math.sin(2.0 * math.pi * 55.0 * t))
            + (0.58 * math.sin(2.0 * math.pi * 110.0 * t))
            + (0.18 * math.sin(2.0 * math.pi * 165.0 * t))
        )

    estimate = estimate_pitch_for_region(
        audio,
        sr,
        region=(0.0, duration_sec),
        config=OnsetNoteGeneratorConfig(),
    )

    assert estimate is not None
    assert estimate.pitch_midi == 33
    assert estimate.support["frame_primary_pitch_midi"] == 33
    assert estimate.support["frame_support_ratio"] >= 0.5
    assert estimate.support["frame_candidate_count"] >= 3


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

    assert [note.pitch_midi for note in candidates] == [33, 35, 38]
    assert [note.start_sec for note in candidates] == pytest.approx([0.05, 0.28, 0.53], abs=0.02)
    assert all(note.end_sec > note.start_sec for note in candidates)
    assert all(note.confidence > 0.0 for note in candidates)
    assert all(28 <= note.pitch_midi <= 64 for note in candidates)
    assert all(note.source_tag == "onset_note_generator" for note in candidates)
    assert all(int(note.support["evaluated_candidate_count"]) <= 6 for note in candidates)


def test_generate_onset_note_candidates_rejects_empty_or_implausible_regions() -> None:
    generator = OnsetNoteGenerator(
        audio_loader=lambda _path: ([0.0] * 8000, 8000),
        config=OnsetNoteGeneratorConfig(onset_strength_threshold=0.9),
    )

    assert generator.generate("empty.wav") == []
