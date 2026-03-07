from __future__ import annotations

import numpy as np
import pytest

from app.midi import PitchStabilityConfig
from app.midi import _get_pitch_stability_config
from app.midi import stabilize_bass_pitch_track


def _times(frame_count: int, step_sec: float = 0.1) -> np.ndarray:
    return np.arange(frame_count, dtype=float) * step_sec


def test_stabilize_bass_pitch_track_corrects_isolated_octave_outlier() -> None:
    frame_midi = np.array([40.0, 40.1, 52.0, 39.9, 40.0], dtype=float)
    voiced_prob = np.array([0.92, 0.94, 0.90, 0.93, 0.91], dtype=float)

    stabilized, events, diagnostics = stabilize_bass_pitch_track(
        frame_midi=frame_midi,
        voiced_prob=voiced_prob,
        times=_times(len(frame_midi)),
        onset_frames=np.array([], dtype=int),
        config=PitchStabilityConfig(),
    )

    assert stabilized.tolist() == [40, 40, 40, 40, 40]
    assert [(event[0], event[1], event[2]) for event in events] == [(0.0, 0.5, 40)]
    assert diagnostics["octave_corrections_applied"] >= 1


def test_stabilize_bass_pitch_track_suppresses_pitch_jitter_without_note_churn() -> None:
    frame_midi = np.array([40.0, 40.4, 39.7, 40.2, 39.8, 40.1], dtype=float)
    voiced_prob = np.array([0.88, 0.83, 0.86, 0.84, 0.87, 0.89], dtype=float)

    stabilized, events, diagnostics = stabilize_bass_pitch_track(
        frame_midi=frame_midi,
        voiced_prob=voiced_prob,
        times=_times(len(frame_midi)),
        onset_frames=np.array([], dtype=int),
        config=PitchStabilityConfig(),
    )

    assert stabilized.tolist() == [40, 40, 40, 40, 40, 40]
    assert len(events) == 1
    assert events[0][2] == 40
    assert diagnostics["suppressed_short_transitions"] >= 1


def test_stabilize_bass_pitch_track_preserves_real_note_change_after_sustained_evidence() -> None:
    frame_midi = np.array([40.0, 40.0, 40.1, 43.0, 43.1, 43.0, 43.0], dtype=float)
    voiced_prob = np.array([0.9, 0.9, 0.88, 0.93, 0.94, 0.92, 0.9], dtype=float)

    stabilized, events, _diagnostics = stabilize_bass_pitch_track(
        frame_midi=frame_midi,
        voiced_prob=voiced_prob,
        times=_times(len(frame_midi)),
        onset_frames=np.array([3], dtype=int),
        config=PitchStabilityConfig(pitch_transition_hysteresis_frames=2),
    )

    assert stabilized.tolist() == [40, 40, 40, 43, 43, 43, 43]
    assert [(event[0], event[1], event[2]) for event in events] == [
        (0.0, 0.3, 40),
        (0.3, 0.7, 43),
    ]


def test_stabilize_bass_pitch_track_merges_brief_low_confidence_gap_into_one_note() -> None:
    frame_midi = np.array([38.0, 38.0, np.nan, np.nan, 38.1, 38.0], dtype=float)
    voiced_prob = np.array([0.91, 0.9, 0.1, 0.08, 0.89, 0.9], dtype=float)

    stabilized, events, diagnostics = stabilize_bass_pitch_track(
        frame_midi=frame_midi,
        voiced_prob=voiced_prob,
        times=_times(len(frame_midi)),
        onset_frames=np.array([], dtype=int),
        config=PitchStabilityConfig(pitch_merge_gap_ms=250),
    )

    assert stabilized.tolist() == [38, 38, 38, 38, 38, 38]
    assert [(event[0], event[1], event[2]) for event in events] == [(0.0, 0.6, 38)]
    assert diagnostics["merged_gap_regions"] >= 1


def test_stabilize_bass_pitch_track_suppresses_short_false_note_intrusion() -> None:
    frame_midi = np.array([40.0, 40.0, 47.0, 40.0, 40.0], dtype=float)
    voiced_prob = np.array([0.92, 0.9, 0.58, 0.91, 0.92], dtype=float)

    stabilized, events, diagnostics = stabilize_bass_pitch_track(
        frame_midi=frame_midi,
        voiced_prob=voiced_prob,
        times=_times(len(frame_midi)),
        onset_frames=np.array([], dtype=int),
        config=PitchStabilityConfig(pitch_transition_hysteresis_frames=2),
    )

    assert stabilized.tolist() == [40, 40, 40, 40, 40]
    assert len(events) == 1
    assert events[0][2] == 40
    assert diagnostics["suppressed_short_transitions"] >= 1


def test_stabilize_bass_pitch_track_prefers_lower_fundamental_when_harmonic_is_stronger() -> None:
    frame_midi = np.array([52.0, 52.0, 52.0, 52.0], dtype=float)
    voiced_prob = np.array([0.82, 0.84, 0.83, 0.81], dtype=float)
    freqs = np.array([82.41, 164.82], dtype=float)
    spectrogram = np.array(
        [
            [10.0, 11.5, 10.8, 11.2],
            [4.0, 4.1, 4.2, 4.0],
        ],
        dtype=float,
    )

    stabilized, events, diagnostics = stabilize_bass_pitch_track(
        frame_midi=frame_midi,
        voiced_prob=voiced_prob,
        times=_times(len(frame_midi)),
        onset_frames=np.array([], dtype=int),
        freqs=freqs,
        spectrogram=spectrogram,
        config=PitchStabilityConfig(),
    )

    assert stabilized.tolist() == [40, 40, 40, 40]
    assert [(event[0], event[1], event[2]) for event in events] == [(0.0, 0.4, 40)]
    assert diagnostics["harmonic_rechecks_applied"] >= 1


def test_get_pitch_stability_config_reads_env_overrides(monkeypatch) -> None:
    monkeypatch.setenv("DECHORD_PITCH_STABILITY_ENABLE", "0")
    monkeypatch.setenv("DECHORD_PITCH_MIN_CONFIDENCE", "0.55")
    monkeypatch.setenv("DECHORD_PITCH_TRANSITION_HYSTERESIS_FRAMES", "4")
    monkeypatch.setenv("DECHORD_PITCH_OCTAVE_JUMP_PENALTY", "1.25")
    monkeypatch.setenv("DECHORD_PITCH_MAX_CENTS_DRIFT_WITHIN_NOTE", "35")
    monkeypatch.setenv("DECHORD_PITCH_MIN_NOTE_DURATION_MS", "90")
    monkeypatch.setenv("DECHORD_PITCH_MERGE_GAP_MS", "45")
    monkeypatch.setenv("DECHORD_PITCH_SMOOTHING_WINDOW_FRAMES", "7")
    monkeypatch.setenv("DECHORD_PITCH_HARMONIC_RECHECK_ENABLE", "0")

    config = _get_pitch_stability_config()

    assert config.pitch_stability_enable is False
    assert config.pitch_min_confidence == pytest.approx(0.55)
    assert config.pitch_transition_hysteresis_frames == 4
    assert config.pitch_octave_jump_penalty == pytest.approx(1.25)
    assert config.pitch_max_cents_drift_within_note == pytest.approx(35.0)
    assert config.pitch_min_note_duration_ms == 90
    assert config.pitch_merge_gap_ms == 45
    assert config.pitch_smoothing_window_frames == 7
    assert config.pitch_harmonic_recheck_enable is False


def test_stabilize_bass_pitch_track_returns_raw_segmentation_when_disabled() -> None:
    frame_midi = np.array([40.0, 52.0, 40.0, 40.0], dtype=float)
    voiced_prob = np.array([0.9, 0.9, 0.9, 0.9], dtype=float)

    stabilized, events, diagnostics = stabilize_bass_pitch_track(
        frame_midi=frame_midi,
        voiced_prob=voiced_prob,
        times=_times(len(frame_midi)),
        onset_frames=np.array([], dtype=int),
        config=PitchStabilityConfig(pitch_stability_enable=False),
    )

    assert stabilized.tolist() == [40, 52, 40, 40]
    assert [(event[0], event[1], event[2]) for event in events] == [
        (0.0, 0.1, 40),
        (0.1, 0.2, 52),
        (0.2, 0.4, 40),
    ]
    assert diagnostics["stabilizer_enabled"] is False
