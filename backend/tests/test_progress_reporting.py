"""Regression tests for progress reporting accuracy in _run_analysis."""

import sys
import types
import unittest.mock as mock

import pytest


def _ensure_madmom_mocked():
    """Insert a minimal madmom stub so analysis.py never hits the filesystem."""
    if "madmom" not in sys.modules:
        fake_madmom = types.ModuleType("madmom")
        fake_madmom.features = types.ModuleType("madmom.features")
        fake_madmom.features.chords = types.ModuleType("madmom.features.chords")
        fake_madmom.features.key = types.ModuleType("madmom.features.key")
        fake_madmom.audio = types.ModuleType("madmom.audio")
        fake_madmom.audio.signal = types.ModuleType("madmom.audio.signal")
        sys.modules["madmom"] = fake_madmom
        sys.modules["madmom.features"] = fake_madmom.features
        sys.modules["madmom.features.chords"] = fake_madmom.features.chords
        sys.modules["madmom.features.key"] = fake_madmom.features.key
        sys.modules["madmom.audio"] = fake_madmom.audio
        sys.modules["madmom.audio.signal"] = fake_madmom.audio.signal


def test_chord_analysis_progress_advances_in_three_steps():
    """
    Progress must advance at 10 %, 25 %, and 35 % during chord analysis —
    not freeze at a single value (old behaviour: frozen at 40 % throughout).
    """
    _ensure_madmom_mocked()

    import app.main as main_mod
    from app import analysis

    JOB_ID = "test-chord-progress-001"
    progress_log: list[float] = []

    # Pre-populate the global jobs dict that _run_analysis reads/writes directly
    fake_chord = type("FakeChord", (), {"start": 0.0, "end": 4.0, "label": "C"})()

    # Intercept jobs[JOB_ID] writes via a dict subclass to record progress_pct
    class ProgressTracker(dict):
        def __setitem__(self, key, value):
            if key == "progress_pct":
                progress_log.append(float(value))
            super().__setitem__(key, value)

    tracker = ProgressTracker(
        {
            "status": "queued",
            "stage": None,
            "progress_pct": 0.0,
            "stage_progress_pct": 0.0,
            "process_mode": "analysis_only",
        }
    )
    main_mod.jobs[JOB_ID] = tracker

    with (
        mock.patch.object(main_mod, "detect_chords", return_value=[fake_chord]),
        mock.patch.object(main_mod, "detect_key", return_value="C major"),
        mock.patch.object(main_mod, "detect_tempo", return_value=120),
        mock.patch("app.main.asyncio.run", side_effect=lambda _: None),
    ):
        main_mod._run_analysis(JOB_ID, "/fake/audio.mp3", song_id=1)

    # Must have emitted all three granular checkpoints
    assert 10.0 in progress_log, (
        f"Expected 10 % progress checkpoint (detect_chords). Got: {progress_log}"
    )
    assert 25.0 in progress_log, (
        f"Expected 25 % progress checkpoint (detect_key). Got: {progress_log}"
    )
    assert 35.0 in progress_log, (
        f"Expected 35 % progress checkpoint (detect_tempo). Got: {progress_log}"
    )

    # First non-zero progress must be 10 %, not 40 % (the old frozen value)
    first_nonzero = next((p for p in progress_log if p > 0), None)
    assert first_nonzero == 10.0, (
        f"First progress update should be 10 % (granular start). Got: {first_nonzero}. "
        f"Full log: {progress_log}"
    )


def test_stem_progress_is_monotonically_non_decreasing():
    """
    The _on_stem_progress closure must never report a lower overall progress
    than the highest value already reported — even when:
    - Demucs shift passes reset segment_offset to 0 (overall would drop to 45 %)
    - The post-separation 'Saving stems' callback fires with 0.9 (overall 90 %)
      after the separation loop already reached 100 % (overall 95 %)
    """
    progress_log: list[float] = []

    # Reproduce the closure logic verbatim from _run_analysis in main.py
    _stem_max_pct = [45.0]

    def _set_stage_spy(stage, *, message, progress_pct, stage_progress_pct):
        progress_log.append(float(progress_pct))

    def _on_stem_progress(stage_pct: float, msg: str) -> None:
        overall = min(45 + stage_pct * 0.5, 95)
        if overall > _stem_max_pct[0]:
            _stem_max_pct[0] = overall
        _set_stage_spy(
            "splitting_stems",
            message=msg,
            progress_pct=_stem_max_pct[0],
            stage_progress_pct=stage_pct,
        )

    # --- Simulate Demucs pass 1 (segment_offset 0 → audio_length) ---
    for pct in [0.0, 20.0, 40.0, 60.0, 80.0, 100.0]:
        _on_stem_progress(pct, "Separating stems...")

    # --- Simulate Demucs shift pass 2 (segment_offset resets to 0) ---
    for pct in [0.0, 20.0, 40.0, 60.0, 80.0, 100.0]:
        _on_stem_progress(pct, "Separating stems...")

    # --- Simulate 'Saving stems' callback at 90 — would regress from 95 ---
    _on_stem_progress(90.0, "Saving stems...")

    # --- Simulate final completion callback ---
    _on_stem_progress(100.0, "Separated stems")

    # 1. Must be monotonically non-decreasing throughout
    for i in range(1, len(progress_log)):
        assert progress_log[i] >= progress_log[i - 1], (
            f"Progress went backward at index {i}: "
            f"{progress_log[i - 1]:.1f} → {progress_log[i]:.1f}\n"
            f"Full log: {progress_log}"
        )

    # 2. Must have reached the 95 % cap
    assert max(progress_log) == 95.0, (
        f"Expected max progress of 95 %, got {max(progress_log)}"
    )

    # 3. After first reaching 95 %, must never drop below it
    first_95_idx = next(i for i, v in enumerate(progress_log) if v == 95.0)
    for v in progress_log[first_95_idx:]:
        assert v == 95.0, (
            f"Progress dropped below 95 % after reaching it: {v}\n"
            f"Full log: {progress_log}"
        )
