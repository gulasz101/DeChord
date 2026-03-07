from __future__ import annotations

import argparse

import pytest

from app.midi import _get_pitch_stability_config
from app.pipeline_presets import DEFAULT_PIPELINE_PRESET_NAME
from app.pipeline_presets import resolve_pipeline_preset
from app.stems import _get_stem_analysis_config
from scripts.evaluate_tab_quality import resolve_resource_monitor_config


def test_resolve_pipeline_preset_defaults_to_balanced_benchmark() -> None:
    preset = resolve_pipeline_preset()

    assert preset.name == DEFAULT_PIPELINE_PRESET_NAME
    assert preset.name == "balanced_benchmark"
    assert preset.recommended_quality_mode == "high_accuracy_aggressive"
    assert preset.pitch_defaults.dense_note_generator_enable is False
    assert preset.stem_defaults.enable_model_ensemble is False


def test_resolve_pipeline_preset_invalid_name_falls_back_to_balanced_benchmark() -> None:
    preset = resolve_pipeline_preset("definitely_not_a_real_preset")

    assert preset.name == "balanced_benchmark"


def test_resolve_pipeline_preset_distorted_bass_recall_keeps_dense_note_generator_enabled() -> None:
    preset = resolve_pipeline_preset("distorted_bass_recall")

    assert preset.recommended_quality_mode == "high_accuracy_aggressive"
    assert preset.pitch_defaults.dense_note_generator_enable is True
    assert preset.pitch_defaults.onset_note_generator_enable is False
    assert preset.stem_defaults.enable_bass_refinement is False
    assert preset.stem_defaults.enable_model_ensemble is False


def test_pitch_stability_config_uses_preset_defaults_but_allows_env_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DECHORD_PIPELINE_PRESET", "stable_baseline")

    config = _get_pitch_stability_config()

    assert config.pitch_stability_enable is False
    assert config.dense_note_generator_enable is False

    monkeypatch.setenv("DECHORD_PITCH_STABILITY_ENABLE", "1")
    monkeypatch.setenv("DECHORD_DENSE_NOTE_GENERATOR_ENABLE", "1")

    overridden = _get_pitch_stability_config()

    assert overridden.pitch_stability_enable is True
    assert overridden.dense_note_generator_enable is True


def test_stem_analysis_config_uses_preset_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DECHORD_PIPELINE_PRESET", "stable_baseline")

    config = _get_stem_analysis_config()

    assert config.enable_bass_refinement is True
    assert config.enable_model_ensemble is False
    assert config.candidate_models == [config.demucs_model]


def test_resource_monitor_config_uses_preset_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DECHORD_PIPELINE_PRESET", "distorted_bass_recall")
    args = argparse.Namespace(
        resource_monitor=False,
        max_memory_mb=None,
        max_child_procs=None,
        resource_monitor_poll_sec=None,
    )

    config = resolve_resource_monitor_config(args)

    assert config.enabled is True
    assert config.max_memory_mb == 12000
    assert config.max_child_processes == 4
    assert config.poll_interval_sec == pytest.approx(2.0)
