from __future__ import annotations

from dataclasses import dataclass
import os

DEFAULT_PIPELINE_PRESET_NAME = "balanced_benchmark"


@dataclass(frozen=True)
class PipelinePresetPitchDefaults:
    pitch_stability_enable: bool
    note_admission_enable: bool
    raw_note_recall_enable: bool
    raw_note_sparse_region_boost_enable: bool
    onset_note_generator_enable: bool
    dense_note_generator_enable: bool
    note_dense_candidate_min_duration_ms: int
    note_dense_unstable_context_penalty: float
    note_dense_octave_neighbor_penalty: float


@dataclass(frozen=True)
class PipelinePresetStemDefaults:
    enable_bass_refinement: bool
    enable_model_ensemble: bool
    auto_enable_quality_mode_ensemble: bool


@dataclass(frozen=True)
class PipelinePresetBenchmarkDefaults:
    resource_monitor_enabled: bool
    max_memory_mb: int
    max_child_processes: int
    poll_interval_sec: float


@dataclass(frozen=True)
class PipelinePreset:
    name: str
    description: str
    recommended_quality_mode: str
    recommended_benchmark_config: str
    pitch_defaults: PipelinePresetPitchDefaults
    stem_defaults: PipelinePresetStemDefaults
    benchmark_defaults: PipelinePresetBenchmarkDefaults


_BENCHMARK_DEFAULTS = PipelinePresetBenchmarkDefaults(
    resource_monitor_enabled=True,
    max_memory_mb=12_000,
    max_child_processes=4,
    poll_interval_sec=2.0,
)


PIPELINE_PRESETS: dict[str, PipelinePreset] = {
    "stable_baseline": PipelinePreset(
        name="stable_baseline",
        description="Safe bounded baseline with refinement enabled and recall-expansion features off.",
        recommended_quality_mode="standard",
        recommended_benchmark_config="refinement",
        pitch_defaults=PipelinePresetPitchDefaults(
            pitch_stability_enable=False,
            note_admission_enable=True,
            raw_note_recall_enable=False,
            raw_note_sparse_region_boost_enable=False,
            onset_note_generator_enable=False,
            dense_note_generator_enable=False,
            note_dense_candidate_min_duration_ms=120,
            note_dense_unstable_context_penalty=1.0,
            note_dense_octave_neighbor_penalty=1.0,
        ),
        stem_defaults=PipelinePresetStemDefaults(
            enable_bass_refinement=True,
            enable_model_ensemble=False,
            auto_enable_quality_mode_ensemble=False,
        ),
        benchmark_defaults=_BENCHMARK_DEFAULTS,
    ),
    "distorted_bass_recall": PipelinePreset(
        name="distorted_bass_recall",
        description="Recall-oriented aggressive profile for dense distorted bass passages.",
        recommended_quality_mode="high_accuracy_aggressive",
        recommended_benchmark_config="baseline",
        pitch_defaults=PipelinePresetPitchDefaults(
            pitch_stability_enable=True,
            note_admission_enable=True,
            raw_note_recall_enable=False,
            raw_note_sparse_region_boost_enable=False,
            onset_note_generator_enable=False,
            dense_note_generator_enable=True,
            note_dense_candidate_min_duration_ms=55,
            note_dense_unstable_context_penalty=0.20,
            note_dense_octave_neighbor_penalty=0.25,
        ),
        stem_defaults=PipelinePresetStemDefaults(
            enable_bass_refinement=False,
            enable_model_ensemble=False,
            auto_enable_quality_mode_ensemble=False,
        ),
        benchmark_defaults=_BENCHMARK_DEFAULTS,
    ),
    "balanced_benchmark": PipelinePreset(
        name="balanced_benchmark",
        description="Phase-5-style compromise: aggressive second-pass recovery without dense-generator default drift.",
        recommended_quality_mode="high_accuracy_aggressive",
        recommended_benchmark_config="baseline",
        pitch_defaults=PipelinePresetPitchDefaults(
            pitch_stability_enable=False,
            note_admission_enable=True,
            raw_note_recall_enable=False,
            raw_note_sparse_region_boost_enable=False,
            onset_note_generator_enable=False,
            dense_note_generator_enable=False,
            note_dense_candidate_min_duration_ms=120,
            note_dense_unstable_context_penalty=1.0,
            note_dense_octave_neighbor_penalty=1.0,
        ),
        stem_defaults=PipelinePresetStemDefaults(
            enable_bass_refinement=False,
            enable_model_ensemble=False,
            auto_enable_quality_mode_ensemble=False,
        ),
        benchmark_defaults=_BENCHMARK_DEFAULTS,
    ),
}


def active_pipeline_preset_name() -> str | None:
    value = os.getenv("DECHORD_PIPELINE_PRESET")
    if value is None:
        return None
    normalized = value.strip().lower()
    return normalized or None


def resolve_pipeline_preset(name: str | None = None) -> PipelinePreset:
    normalized = (name or "").strip().lower()
    if not normalized:
        normalized = DEFAULT_PIPELINE_PRESET_NAME
    return PIPELINE_PRESETS.get(normalized, PIPELINE_PRESETS[DEFAULT_PIPELINE_PRESET_NAME])
