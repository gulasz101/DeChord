from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from statistics import median
from tempfile import NamedTemporaryFile
from typing import Callable, Literal, Protocol
import wave

from app.midi import _get_pitch_stability_config
from app.services.alphatex_exporter import SyncPoint, export_alphatex
from app.services.bass_transcriber import BasicPitchTranscriber, BassTranscriber
from app.services.dense_note_generator import DenseNoteCandidate, DenseNoteGenerator
from app.services.fingering import (
    FingeredNote,
    candidate_sanity_probe,
    optimize_fingering,
    optimize_fingering_with_debug,
)
from app.services.note_cleanup import cleanup_note_events, cleanup_params_for_bpm
from app.services.onset_recovery import recover_missing_onsets, recovery_params_for_bpm
from app.services.pipeline_trace import build_pipeline_trace_report, build_stage_metrics
from app.services.quantization import QuantizedNote, quantize_note_events
from app.services.rhythm_grid import (
    Bar,
    BarGrid,
    build_bars_from_beats_downbeats,
    compute_derived_bpm,
    extract_beats_and_downbeats,
    reconcile_tempo,
)

RhythmExtractFn = Callable[..., tuple[list[float], list[float], str]]
BarBuilderFn = Callable[..., list[Bar]]
CleanupFn = Callable[..., list]
QuantizeFn = Callable[..., list[QuantizedNote]]
FingeringFn = Callable[..., list[FingeredNote]]
ExportFn = Callable[..., tuple[str, list[SyncPoint]]]
OnsetDetectFn = Callable[[Path], list[float]]


class DenseNoteGeneratorLike(Protocol):
    def generate(
        self,
        *,
        bass_wav: Path,
        window_start: float,
        window_end: float,
        onset_times: list[float],
        base_notes: list,
        context_notes: list,
    ) -> list[DenseNoteCandidate]: ...


class FingeringCollapseError(RuntimeError):
    def __init__(self, message: str, *, debug_info: dict[str, object]) -> None:
        super().__init__(message)
        self.debug_info = debug_info


@dataclass(frozen=True)
class TabPipelineResult:
    alphatex: str
    tempo_used: float
    bars: list[Bar]
    sync_points: list[SyncPoint]
    midi_bytes: bytes
    debug_info: dict[str, object]


class TabPipeline:
    def __init__(
        self,
        *,
        transcriber: BassTranscriber | None = None,
        rhythm_extract_fn: RhythmExtractFn | None = None,
        bar_builder_fn: BarBuilderFn | None = None,
        cleanup_fn: CleanupFn | None = None,
        quantize_fn: QuantizeFn | None = None,
        fingering_fn: FingeringFn | None = None,
        export_fn: ExportFn | None = None,
        onset_detect_fn: OnsetDetectFn | None = None,
        dense_note_generator: DenseNoteGeneratorLike | None = None,
    ) -> None:
        self._transcriber = transcriber or BasicPitchTranscriber()
        self._rhythm_extract_fn = rhythm_extract_fn or extract_beats_and_downbeats
        self._bar_builder_fn = bar_builder_fn or build_bars_from_beats_downbeats
        self._cleanup_fn = cleanup_fn or cleanup_note_events
        self._quantize_fn = quantize_fn or quantize_note_events
        self._fingering_fn = fingering_fn or optimize_fingering
        self._export_fn = export_fn or export_alphatex
        self._onset_detect_fn = onset_detect_fn or self._detect_onsets_librosa
        self._dense_note_generator = dense_note_generator or DenseNoteGenerator()

    def run(
        self,
        bass_wav: Path,
        drums_wav: Path,
        *,
        tab_generation_quality_mode: Literal["standard", "high_accuracy", "high_accuracy_aggressive"] = "standard",
        bpm_hint: float | None = None,
        time_signature: tuple[int, int] = (4, 4),
        subdivision: int = 16,
        max_fret: int = 24,
        sync_every_bars: int = 8,
        onset_recovery: bool | None = None,
    ) -> TabPipelineResult:
        numerator, denominator = time_signature
        beats, downbeats, rhythm_source = self._rhythm_extract_fn(
            drums_wav,
            time_signature_numerator=numerator,
        )
        raw_beat_bpm = compute_derived_bpm(beats)
        song_bpm = float(bpm_hint) if bpm_hint is not None else None
        corrected_beats, corrected_downbeats, grid_correction_applied = self._correct_metrical_grid(
            beats,
            downbeats,
            song_bpm=song_bpm,
            beats_per_bar=numerator,
        )
        corrected_beat_bpm = compute_derived_bpm(corrected_beats)
        bars = self._bar_builder_fn(corrected_beats, corrected_downbeats, time_signature_numerator=numerator)
        if not bars:
            raise RuntimeError("No bars were produced from rhythm extraction.")

        audio_duration_sec = self._audio_duration_seconds(bass_wav)
        derived_bpm = compute_derived_bpm(corrected_beats)
        tempo_used = float(song_bpm) if song_bpm is not None else reconcile_tempo(derived_bpm=derived_bpm, bpm_hint=bpm_hint)

        transcription = self._transcriber.transcribe(bass_wav)
        note_config = _get_pitch_stability_config()
        quality_mode_suspect_silence = tab_generation_quality_mode in {"high_accuracy", "high_accuracy_aggressive"}
        should_onset_recovery = (
            onset_recovery
            if onset_recovery is not None
            else tab_generation_quality_mode in {"high_accuracy", "high_accuracy_aggressive"}
        )
        onset_times: list[float] = []
        analysis_onset_times: list[float] = []
        pre_cleanup_notes = transcription.raw_notes
        quantize_input_notes = list(pre_cleanup_notes)
        onset_recovery_applied = False
        onset_split_starts: set[float] = set()
        onset_split_count = 0
        all_dense_candidates: list[DenseNoteCandidate] = []
        accepted_dense_candidates: list[DenseNoteCandidate] = []
        if (should_onset_recovery and pre_cleanup_notes) or quality_mode_suspect_silence:
            analysis_onset_times = self._onset_detect_fn(bass_wav)
        if should_onset_recovery and pre_cleanup_notes:
            onset_times = analysis_onset_times
            if onset_times:
                onset_kwargs = recovery_params_for_bpm(tempo_used)
                pre_cleanup_notes, onset_split_starts, onset_split_count = recover_missing_onsets(
                    pre_cleanup_notes,
                    onset_times,
                    **onset_kwargs,
                )
                onset_recovery_applied = True

        cleanup_kwargs = cleanup_params_for_bpm(tempo_used)
        cleanup_stats_pass1: dict[str, int] = {}
        cleaned_notes = self._cleanup_fn(
            pre_cleanup_notes,
            **cleanup_kwargs,
            onset_times=onset_times,
            onset_split_starts=onset_split_starts,
            stats=cleanup_stats_pass1,
        )
        quantize_input_notes = list(cleaned_notes)
        quantized_notes = self._quantize_fn(cleaned_notes, BarGrid(bars=bars), subdivision=subdivision)
        quality_diagnostics: dict[str, object] = {
            "QUALITY_MODE_SUSPECT_SILENCE": quality_mode_suspect_silence,
        }
        raw_note_source_rows = self._build_raw_note_source_rows(
            pre_cleanup_notes,
            dense_candidates=[],
            cleaned_notes=cleaned_notes,
        )

        if quality_mode_suspect_silence:
            notes_per_bar_before = self._notes_per_bar(quantized_notes, len(bars))
            bar_rms = self._bar_rms_values(bass_wav, bars)
            onset_peaks = self._bar_onset_peaks(bass_wav, bars)
            suspect_rows: list[dict[str, object]] = []
            dense_bar_fusion_candidates: list[dict[str, object]] = []
            dense_note_fusion_candidates: list[dict[str, object]] = []

            if tab_generation_quality_mode == "high_accuracy":
                median_bar_rms = self._median(bar_rms)
                for bar_index, note_count in enumerate(notes_per_bar_before):
                    rms = bar_rms[bar_index]
                    triggered_by_rms = note_count == 0 and rms > 0 and rms >= (median_bar_rms * 0.9)
                    if triggered_by_rms:
                        suspect_rows.append(
                            {
                                "bar_index": bar_index,
                                "rms": rms,
                                "local_median_rms": median_bar_rms,
                                "onset_peaks": onset_peaks[bar_index] if bar_index < len(onset_peaks) else 0,
                                "triggered_by_rms": True,
                                "triggered_by_onsets": False,
                            }
                        )
            else:
                local_medians = self._local_median_rms(bar_rms, half_window=8)
                for bar_index, note_count in enumerate(notes_per_bar_before):
                    rms = bar_rms[bar_index]
                    local_median = local_medians[bar_index]
                    onsets = onset_peaks[bar_index] if bar_index < len(onset_peaks) else 0
                    triggered_by_dense_sparse = onsets >= 6 and note_count <= max(2, int(onsets * 0.25))
                    triggered_by_rms = note_count == 0 and rms > 0 and local_median > 0 and rms >= (local_median * 0.9)
                    triggered_by_onsets = note_count == 0 and onsets >= 2
                    if triggered_by_rms or triggered_by_onsets or triggered_by_dense_sparse:
                        suspect_rows.append(
                            {
                                "bar_index": bar_index,
                                "rms": rms,
                                "local_median_rms": local_median,
                                "onset_peaks": onsets,
                                "triggered_by_rms": triggered_by_rms,
                                "triggered_by_onsets": triggered_by_onsets,
                                "triggered_by_dense_sparse": triggered_by_dense_sparse,
                            }
                        )
            second_pass_notes: list = []
            for row in suspect_rows:
                bar_index = int(row["bar_index"])
                bar = bars[bar_index]
                window_start = max(0.0, bar.start_sec - 0.2)
                window_end = bar.end_sec + 0.2
                local_context = [
                    note
                    for note in pre_cleanup_notes
                    if max(0.0, window_start - 0.6) <= float(note.start_sec) < min(audio_duration_sec, window_end + 0.6)
                ]
                dense_candidates: list[DenseNoteCandidate] = []
                if row.get("triggered_by_dense_sparse") and analysis_onset_times:
                    dense_candidates = self._dense_note_generator.generate(
                        bass_wav=bass_wav,
                        window_start=window_start,
                        window_end=window_end,
                        onset_times=analysis_onset_times,
                        base_notes=pre_cleanup_notes,
                        context_notes=local_context,
                    )
                    all_dense_candidates.extend(dense_candidates)
                    accepted_candidates, dense_rows = self._confidence_gate_dense_note_candidates(
                        dense_candidates,
                        reference_notes=pre_cleanup_notes,
                        base_notes=pre_cleanup_notes + [candidate.to_raw_note() for candidate in accepted_dense_candidates],
                        bar_index=bar_index,
                        onset_peak_count=onset_peaks[bar_index] if bar_index < len(onset_peaks) else 0,
                        window_start=window_start,
                        window_end=window_end,
                    )
                    accepted_dense_candidates.extend(accepted_candidates)
                    dense_note_fusion_candidates.extend(dense_rows)

                if row.get("triggered_by_dense_sparse") and accepted_dense_candidates:
                    continue

                window_notes = self._transcribe_window_with_offset(
                    bass_wav,
                    window_start=window_start,
                    window_end=window_end,
                )
                if row.get("triggered_by_dense_sparse"):
                    window_notes, candidate_rows = self._confidence_gate_dense_bar_candidates(
                        window_notes,
                        reference_notes=pre_cleanup_notes,
                        base_notes=transcription.raw_notes,
                        bar_index=bar_index,
                        onset_peak_count=onset_peaks[bar_index] if bar_index < len(onset_peaks) else 0,
                        window_start=window_start,
                        window_end=window_end,
                    )
                    dense_bar_fusion_candidates.extend(candidate_rows)
                second_pass_notes.extend(window_notes)

            merged_additions = second_pass_notes + [candidate.to_raw_note() for candidate in accepted_dense_candidates]
            if merged_additions:
                merged_raw_notes = self._merge_raw_notes(pre_cleanup_notes, merged_additions)
                cleanup_stats_pass2: dict[str, int] = {}
                cleaned_notes = self._cleanup_fn(
                    merged_raw_notes,
                    **cleanup_kwargs,
                    onset_times=onset_times,
                    onset_split_starts=onset_split_starts,
                    stats=cleanup_stats_pass2,
                )
                quantize_input_notes = list(cleaned_notes)
                quantized_notes = self._quantize_fn(cleaned_notes, BarGrid(bars=bars), subdivision=subdivision)
                quality_diagnostics["cleanup_stats_second_pass"] = cleanup_stats_pass2
                raw_note_source_rows = self._build_raw_note_source_rows(
                    merged_raw_notes,
                    dense_candidates=accepted_dense_candidates,
                    cleaned_notes=cleaned_notes,
                )

            notes_per_bar_after = self._notes_per_bar(quantized_notes, len(bars))
            notes_added_second_pass = max(0, sum(notes_per_bar_after) - sum(notes_per_bar_before))
            quality_diagnostics.update(
                {
                    "suspect_silence_bars_count": len(suspect_rows),
                    "suspect_bars": suspect_rows,
                    "notes_added_second_pass": notes_added_second_pass,
                    "notes_per_bar_before_high_accuracy": notes_per_bar_before,
                    "notes_per_bar_after_high_accuracy": notes_per_bar_after,
                    "dense_bar_fusion_candidates": dense_bar_fusion_candidates,
                    "dense_bar_fusion_summary": self._dense_bar_fusion_summary(dense_bar_fusion_candidates),
                    "dense_note_fusion_candidates": dense_note_fusion_candidates,
                    "dense_note_fusion_summary": self._dense_note_fusion_summary(dense_note_fusion_candidates),
                }
            )

        candidate_probe = candidate_sanity_probe(max_fret=max_fret)
        if not candidate_probe["all_ok"]:
            raise FingeringCollapseError(
                "candidate sanity probe failed",
                debug_info={
                    "stage_counts": {
                        "raw": len(transcription.raw_notes),
                        "cleaned": len(cleaned_notes),
                        "quantized": len(quantized_notes),
                        "fingered": 0,
                        "exported": 0,
                    },
                    "candidate_probe": candidate_probe,
                    "fingering": {
                        "dropped_reasons": {},
                        "tuning_midi": {},
                        "max_fret": max_fret,
                        "octave_salvaged_notes": 0,
                    },
                },
            )

        if self._fingering_fn is optimize_fingering:
            fingered_notes, fingering_debug = optimize_fingering_with_debug(quantized_notes, max_fret=max_fret)
        else:
            fingered_notes = self._fingering_fn(quantized_notes, max_fret=max_fret)
            fingering_debug = {
                "dropped_reasons": {},
                "dropped_note_count": max(0, len(quantized_notes) - len(fingered_notes)),
                "playable_note_count": len(fingered_notes),
                "input_note_count": len(quantized_notes),
                "octave_salvage_enabled": False,
                "octave_salvaged_notes": 0,
                "tuning_midi": {},
                "max_fret": max_fret,
            }

        if quantized_notes and not fingered_notes:
            raise FingeringCollapseError(
                "fingering dropped all quantized notes",
                debug_info={
                    "stage_counts": {
                        "raw": len(transcription.raw_notes),
                        "cleaned": len(cleaned_notes),
                        "quantized": len(quantized_notes),
                        "fingered": 0,
                        "exported": 0,
                    },
                    "candidate_probe": candidate_probe,
                    "fingering": fingering_debug,
                },
            )

        export_bars = self._extend_bars_to_cover_audio(
            bars,
            audio_duration_sec=audio_duration_sec,
            beats_per_bar=numerator,
        )

        alphatex, sync_points = self._export_fn(
            fingered_notes,
            export_bars,
            tempo_used=tempo_used,
            time_signature=(numerator, denominator),
            sync_every_bars=sync_every_bars,
            )

        transcription_trace = dict(getattr(transcription, "debug_info", {}) or {}).get("pipeline_trace")
        transcription_stage_stats = {}
        if isinstance(transcription_trace, dict):
            raw_pipeline_stats = transcription_trace.get("pipeline_stats")
            if isinstance(raw_pipeline_stats, dict):
                transcription_stage_stats = dict(raw_pipeline_stats)
        cleanup_stats_second_pass = quality_diagnostics.get("cleanup_stats_second_pass", {})
        merged_cleanup_count = int(cleanup_stats_pass1.get("merged_same_pitch", 0))
        if isinstance(cleanup_stats_second_pass, dict):
            merged_cleanup_count += int(cleanup_stats_second_pass.get("merged_same_pitch", 0))
        pipeline_trace_report = build_pipeline_trace_report(
            song_name=str(bass_wav.stem),
            pipeline_stats={
                "basic_pitch_raw": dict(transcription_stage_stats.get("basic_pitch_raw", build_stage_metrics([]))),
                "pitch_stabilized": dict(transcription_stage_stats.get("pitch_stabilized", build_stage_metrics([]))),
                "admission_filtered": dict(
                    transcription_stage_stats.get(
                        "admission_filtered",
                        build_stage_metrics(
                            list(pre_cleanup_notes),
                            short_note_threshold_ms=note_config.note_min_duration_ms,
                        ),
                    )
                ),
                "dense_candidates": build_stage_metrics(
                    list(all_dense_candidates),
                    short_note_threshold_ms=note_config.note_dense_candidate_min_duration_ms,
                    added_override=len(all_dense_candidates),
                    removed_override=0,
                    altered_override=0,
                ),
                "dense_accepted": build_stage_metrics(
                    [candidate.to_raw_note() for candidate in accepted_dense_candidates],
                    short_note_threshold_ms=note_config.note_dense_candidate_min_duration_ms,
                    added_override=len(accepted_dense_candidates),
                    removed_override=max(0, len(all_dense_candidates) - len(accepted_dense_candidates)),
                    altered_override=0,
                ),
                "final_notes": build_stage_metrics(
                    list(quantized_notes),
                    previous_notes=quantize_input_notes,
                    short_note_threshold_ms=note_config.note_min_duration_ms,
                    merged_count=merged_cleanup_count,
                ),
            },
        )

        debug_info = {
            "rhythm_source": rhythm_source,
            "beat_count": len(corrected_beats),
            "downbeat_count": len(corrected_downbeats),
            "raw_note_count": len(transcription.raw_notes),
            "raw_notes_count": len(transcription.raw_notes),
            "after_onset_recovery_count": len(pre_cleanup_notes),
            "cleaned_note_count": len(cleaned_notes),
            "after_cleanup_count": len(cleaned_notes),
            "quantized_note_count": len(quantized_notes),
            "after_quantize_count": len(quantized_notes),
            "fingered_note_count": len(fingered_notes),
            "after_fingering_count": len(fingered_notes),
            "after_fingering": len(fingered_notes),
            "after_exporting": len(fingered_notes),
            "derived_bpm": derived_bpm,
            "bpm_hint": bpm_hint,
            "tempo_used": tempo_used,
            "song_bpm": song_bpm,
            "beat_bpm_estimate_raw": raw_beat_bpm,
            "beat_bpm_estimate_corrected": corrected_beat_bpm,
            "grid_correction_applied": grid_correction_applied,
            "stage_counts": {
                "raw": len(transcription.raw_notes),
                "cleaned": len(cleaned_notes),
                "quantized": len(quantized_notes),
                "fingered": len(fingered_notes),
                "exported": len(fingered_notes),
            },
            "candidate_probe": candidate_probe,
            "fingering": fingering_debug,
            "tab_generation_quality_mode": tab_generation_quality_mode,
            "tab_last_sync_ms": sync_points[-1].millisecond_offset if sync_points else 0,
            "audio_duration_sec": audio_duration_sec,
            "total_bars": len(export_bars),
            "cleanup_params": cleanup_kwargs,
            "cleanup_stats": cleanup_stats_pass1,
            "onset_recovery_applied": onset_recovery_applied,
            "onset_count": len(onset_times),
            "analysis_onset_count": len(analysis_onset_times),
            "onset_split_count": onset_split_count,
            "raw_note_source_rows": raw_note_source_rows,
            "raw_note_source_summary": self._raw_note_source_summary(raw_note_source_rows),
            "pipeline_trace": pipeline_trace_report,
            **quality_diagnostics,
        }

        return TabPipelineResult(
            alphatex=alphatex,
            tempo_used=tempo_used,
            bars=export_bars,
            sync_points=sync_points,
            midi_bytes=transcription.midi_bytes,
            debug_info=debug_info,
        )

    @staticmethod
    def _detect_onsets_librosa(bass_wav: Path) -> list[float]:
        try:
            import librosa
        except ModuleNotFoundError:
            return []

        y, sr = librosa.load(str(bass_wav), sr=22050, mono=True)
        if y.size == 0:
            return []
        onset_frames = librosa.onset.onset_detect(y=y, sr=sr, units="frames")
        onset_times = librosa.frames_to_time(onset_frames, sr=sr)
        return [float(timestamp) for timestamp in onset_times]

    @staticmethod
    def _notes_per_bar(quantized_notes: list[QuantizedNote], bar_count: int) -> list[int]:
        counts = [0 for _ in range(bar_count)]
        for note in quantized_notes:
            if 0 <= note.bar_index < bar_count:
                counts[note.bar_index] += 1
        return counts

    @staticmethod
    def _median(values: list[float]) -> float:
        if not values:
            return 0.0
        sorted_values = sorted(values)
        mid = len(sorted_values) // 2
        if len(sorted_values) % 2 == 1:
            return sorted_values[mid]
        return (sorted_values[mid - 1] + sorted_values[mid]) / 2.0

    @staticmethod
    def _local_median_rms(values: list[float], *, half_window: int) -> list[float]:
        if not values:
            return []
        medians: list[float] = []
        for idx in range(len(values)):
            start = max(0, idx - half_window)
            end = min(len(values), idx + half_window + 1)
            medians.append(TabPipeline._median(values[start:end]))
        return medians

    @staticmethod
    def _audio_duration_seconds(audio_wav: Path) -> float:
        try:
            with wave.open(str(audio_wav), "rb") as wav_file:
                frame_rate = wav_file.getframerate()
                frame_count = wav_file.getnframes()
        except Exception:
            return 0.0
        if frame_rate <= 0:
            return 0.0
        return frame_count / frame_rate

    @staticmethod
    def _bar_rms_values(bass_wav: Path, bars: list[Bar]) -> list[float]:
        with wave.open(str(bass_wav), "rb") as wav_file:
            channels = wav_file.getnchannels()
            sample_width = wav_file.getsampwidth()
            frame_rate = wav_file.getframerate()
            raw_frames = wav_file.readframes(wav_file.getnframes())

        if sample_width != 2:
            return [0.0 for _ in bars]

        total_samples = len(raw_frames) // sample_width
        if total_samples <= 0:
            return [0.0 for _ in bars]
        samples = [
            int.from_bytes(raw_frames[i : i + sample_width], byteorder="little", signed=True)
            for i in range(0, len(raw_frames), sample_width)
        ]
        if channels > 1:
            mono_samples = []
            for idx in range(0, len(samples), channels):
                frame = samples[idx : idx + channels]
                if frame:
                    mono_samples.append(sum(frame) / len(frame))
            samples = mono_samples

        rms_values: list[float] = []
        for bar in bars:
            start_index = max(0, int(bar.start_sec * frame_rate))
            end_index = min(len(samples), int(bar.end_sec * frame_rate))
            if end_index <= start_index:
                rms_values.append(0.0)
                continue
            segment = samples[start_index:end_index]
            squared_sum = sum(float(sample) * float(sample) for sample in segment)
            rms_values.append((squared_sum / len(segment)) ** 0.5 / 32768.0)
        return rms_values

    @staticmethod
    def _bar_onset_peaks(bass_wav: Path, bars: list[Bar]) -> list[int]:
        try:
            import librosa  # type: ignore
        except Exception:
            return [0 for _ in bars]

        y, sr = librosa.load(str(bass_wav), sr=None, mono=True)
        if len(y) == 0:
            return [0 for _ in bars]
        onset_env = librosa.onset.onset_strength(y=y, sr=sr)
        frame_times = librosa.frames_to_time(range(len(onset_env)), sr=sr)

        peaks_per_bar: list[int] = []
        for bar in bars:
            idxs = [i for i, t in enumerate(frame_times) if bar.start_sec <= float(t) < bar.end_sec]
            if not idxs:
                peaks_per_bar.append(0)
                continue
            segment = onset_env[min(idxs) : max(idxs) + 1]
            peaks = librosa.util.peak_pick(
                segment,
                pre_max=2,
                post_max=2,
                pre_avg=2,
                post_avg=2,
                delta=0.1,
                wait=2,
            )
            peaks_per_bar.append(int(len(peaks)))
        return peaks_per_bar

    @staticmethod
    def _infer_downbeats_from_beats(beats: list[float], *, beats_per_bar: int) -> list[float]:
        if beats_per_bar <= 0:
            beats_per_bar = 4
        return [beat for idx, beat in enumerate(beats) if idx % beats_per_bar == 0]

    @staticmethod
    def _correct_metrical_grid(
        beats: list[float],
        downbeats: list[float],
        *,
        song_bpm: float | None,
        beats_per_bar: int,
    ) -> tuple[list[float], list[float], str]:
        if len(beats) < 2 or song_bpm is None or song_bpm <= 0:
            return beats, downbeats, "none"

        beat_bpm_raw = compute_derived_bpm(beats)
        if beat_bpm_raw is None or beat_bpm_raw <= 0:
            return beats, downbeats, "none"

        rel_diff = abs(beat_bpm_raw - song_bpm) / song_bpm
        if rel_diff <= 0.15:
            return beats, downbeats, "none"

        is_double = abs(beat_bpm_raw - (song_bpm * 2.0)) / (song_bpm * 2.0) <= 0.15
        if is_double:
            corrected_beats = beats[::2]
            corrected_downbeats = downbeats[::2] if downbeats else TabPipeline._infer_downbeats_from_beats(
                corrected_beats, beats_per_bar=beats_per_bar
            )
            return corrected_beats, corrected_downbeats, "double_time"

        is_half = abs(beat_bpm_raw - (song_bpm * 0.5)) / (song_bpm * 0.5) <= 0.15
        if is_half:
            corrected_beats: list[float] = []
            for idx in range(len(beats) - 1):
                start = beats[idx]
                end = beats[idx + 1]
                corrected_beats.append(start)
                corrected_beats.append((start + end) / 2.0)
            corrected_beats.append(beats[-1])
            corrected_beats = sorted(set(corrected_beats))
            corrected_downbeats = TabPipeline._infer_downbeats_from_beats(corrected_beats, beats_per_bar=beats_per_bar)
            return corrected_beats, corrected_downbeats, "half_time"

        return beats, downbeats, "none"

    @staticmethod
    def _extend_bars_to_cover_audio(
        bars: list[Bar],
        *,
        audio_duration_sec: float,
        beats_per_bar: int,
    ) -> list[Bar]:
        if not bars:
            return bars
        if audio_duration_sec <= 0:
            return bars

        durations = [bar.end_sec - bar.start_sec for bar in bars if bar.end_sec > bar.start_sec]
        bar_duration = median(durations) if durations else 0.0
        if bar_duration <= 0:
            return bars

        extended = list(bars)
        while (audio_duration_sec - extended[-1].start_sec) >= bar_duration:
            previous = extended[-1]
            next_start = previous.end_sec
            next_end = next_start + bar_duration
            beat_step = bar_duration / max(beats_per_bar, 1)
            beats_sec = [next_start + (beat_step * idx) for idx in range(max(beats_per_bar, 1))]
            extended.append(
                Bar(
                    index=previous.index + 1,
                    start_sec=next_start,
                    end_sec=next_end,
                    beats_sec=beats_sec,
                )
            )
        return extended

    def _transcribe_window_with_offset(
        self,
        bass_wav: Path,
        *,
        window_start: float,
        window_end: float,
    ) -> list:
        with wave.open(str(bass_wav), "rb") as source_wav:
            channels = source_wav.getnchannels()
            sample_width = source_wav.getsampwidth()
            frame_rate = source_wav.getframerate()
            frame_count = source_wav.getnframes()
            start_frame = max(0, int(window_start * frame_rate))
            end_frame = min(frame_count, int(window_end * frame_rate))
            if end_frame <= start_frame:
                return []
            source_wav.setpos(start_frame)
            segment_frames = source_wav.readframes(end_frame - start_frame)

        with NamedTemporaryFile(suffix=".wav", delete=False) as tmp_wav:
            tmp_path = Path(tmp_wav.name)
        try:
            with wave.open(str(tmp_path), "wb") as target_wav:
                target_wav.setnchannels(channels)
                target_wav.setsampwidth(sample_width)
                target_wav.setframerate(frame_rate)
                target_wav.writeframes(segment_frames)

            transcription = self._transcribe_with_optional_sensitivity(tmp_path)
            return [
                type(note)(
                    pitch_midi=note.pitch_midi,
                    start_sec=note.start_sec + window_start,
                    end_sec=note.end_sec + window_start,
                    confidence=note.confidence,
                )
                for note in transcription.raw_notes
            ]
        finally:
            tmp_path.unlink(missing_ok=True)

    def _transcribe_with_optional_sensitivity(self, bass_wav: Path):
        try:
            return self._transcriber.transcribe(bass_wav, sensitivity="high")
        except TypeError:
            return self._transcriber.transcribe(bass_wav)

    @staticmethod
    def _merge_raw_notes(base_notes: list, additional_notes: list) -> list:
        merged = list(base_notes)
        seen = {
            (
                note.pitch_midi,
                round(note.start_sec, 6),
                round(note.end_sec, 6),
            )
            for note in base_notes
        }
        for note in additional_notes:
            key = (note.pitch_midi, round(note.start_sec, 6), round(note.end_sec, 6))
            if key in seen:
                continue
            merged.append(note)
            seen.add(key)
        merged.sort(key=lambda note: (note.start_sec, note.end_sec, note.pitch_midi))
        return merged

    @staticmethod
    def _build_raw_note_source_rows(
        pre_cleanup_notes: list,
        *,
        dense_candidates: list[DenseNoteCandidate],
        cleaned_notes: list,
    ) -> list[dict[str, object]]:
        dense_by_key = {
            (round(candidate.start_sec, 6), round(candidate.end_sec, 6), int(candidate.pitch_midi)): candidate
            for candidate in dense_candidates
        }
        rows: list[dict[str, object]] = []
        for note in sorted(pre_cleanup_notes, key=lambda item: (item.start_sec, item.end_sec, item.pitch_midi)):
            key = (round(note.start_sec, 6), round(note.end_sec, 6), int(note.pitch_midi))
            dense_candidate = dense_by_key.get(key)
            source = "basic_pitch"
            confidence_summary: dict[str, object] = {"confidence": float(note.confidence)}
            if dense_candidate is not None:
                raw_pitch = dense_candidate.support.get("raw_pitch_midi")
                source = "hybrid_merged" if isinstance(raw_pitch, int) and int(raw_pitch) != int(dense_candidate.pitch_midi) else "dense_note_generator"
                confidence_summary.update(dense_candidate.support)
            rows.append(
                {
                    "source": source,
                    "pitch_midi": int(note.pitch_midi),
                    "start_sec": float(note.start_sec),
                    "end_sec": float(note.end_sec),
                    "survived_cleanup": TabPipeline._note_survived_cleanup(note, cleaned_notes),
                    "confidence_summary": confidence_summary,
                }
            )
        return rows

    @staticmethod
    def _note_survived_cleanup(note, cleaned_notes: list) -> bool:
        for cleaned in cleaned_notes:
            if abs(float(cleaned.start_sec) - float(note.start_sec)) <= 0.05 and int(cleaned.pitch_midi) == int(note.pitch_midi):
                return True
        return False

    @staticmethod
    def _raw_note_source_summary(rows: list[dict[str, object]]) -> dict[str, int]:
        counts = Counter(str(row.get("source", "unknown")) for row in rows)
        return dict(sorted((key, int(value)) for key, value in counts.items()))

    @staticmethod
    def _confidence_gate_dense_bar_candidates(
        second_pass_notes: list,
        *,
        reference_notes: list,
        base_notes: list,
        bar_index: int,
        onset_peak_count: int,
        window_start: float,
        window_end: float,
    ) -> tuple[list, list[dict[str, object]]]:
        note_config = _get_pitch_stability_config()
        local_reference = [note for note in reference_notes if window_start <= note.start_sec < window_end]
        if not local_reference:
            rejected = [
                {
                    "bar_index": bar_index,
                    "candidate_onset_sec": float(note.start_sec),
                    "candidate_raw_pitch": int(note.pitch_midi),
                    "adjusted_pitch": int(note.pitch_midi),
                    "local_pitch_anchor": None,
                    "accepted": False,
                    "rejection_reason": "weak_local_support",
                    "confidence_components": {"total_score": 0.0, "local_support_ratio": 0.0},
                }
                for note in second_pass_notes
            ]
            return [], rejected

        dominant_pitch = max(
            {int(note.pitch_midi) for note in local_reference},
            key=lambda pitch: sum(1 for note in local_reference if int(note.pitch_midi) == pitch),
        )
        local_counts = Counter(int(note.pitch_midi) for note in local_reference)
        repeated_note_mode = TabPipeline._is_dense_repeated_note_mode(local_counts, onset_peak_count=onset_peak_count)
        onset_support_score = max(0.0, min(1.0, float(onset_peak_count) / 8.0))
        accepted_notes: list = []
        candidate_rows: list[dict[str, object]] = []
        collision_pool = list(base_notes)
        for note in second_pass_notes:
            raw_pitch = int(note.pitch_midi)
            nearest_octave_distance = TabPipeline._nearest_octave_distance(raw_pitch, dominant_pitch)
            anchor_distance = abs(raw_pitch - dominant_pitch)
            local_support_ratio = float(local_counts.get(raw_pitch, 0)) / float(max(1, len(local_reference)))
            candidate_duration_sec = max(0.0, float(note.end_sec) - float(note.start_sec))
            unstable_context = TabPipeline._dense_context_is_unstable(local_reference)
            octave_neighbor_conflict = TabPipeline._has_octave_neighbor_conflict(
                collision_pool,
                candidate_start=float(note.start_sec),
                candidate_end=float(note.end_sec),
                candidate_pitch=raw_pitch,
                candidate_confidence=float(note.confidence),
                proximity_sec=max(0.08, note_config.note_merge_gap_ms / 1000.0),
            )
            octave_inconsistent = abs(anchor_distance - 12) <= 1 and local_support_ratio < 0.2
            adjusted_pitch = dominant_pitch if repeated_note_mode or anchor_distance > 1 else raw_pitch
            if not (28 <= adjusted_pitch <= 64):
                adjusted_pitch = max(28, min(64, adjusted_pitch))
            register_ok = 28 <= adjusted_pitch <= 64

            duplicate_existing = any(
                abs(float(existing.start_sec) - float(note.start_sec)) <= 0.08 and int(existing.pitch_midi) == adjusted_pitch
                for existing in collision_pool
            )
            anchor_proximity_score = 1.0 - min(1.0, float(min(anchor_distance, nearest_octave_distance)) / 12.0)
            register_score = 1.0 if register_ok else 0.0
            octave_score = 0.0 if octave_inconsistent else 1.0
            repeated_mode_score = 1.0 if repeated_note_mode and adjusted_pitch == dominant_pitch else 0.0
            duplicate_score = 0.0 if duplicate_existing else 1.0
            duration_score = min(1.0, candidate_duration_sec / max(note_config.note_dense_candidate_min_duration_ms / 1000.0, 0.001))
            context_penalty = note_config.note_dense_unstable_context_penalty if unstable_context else 0.0
            octave_neighbor_penalty = note_config.note_dense_octave_neighbor_penalty if octave_neighbor_conflict else 0.0

            total_score = (
                (0.35 * onset_support_score)
                + (0.25 * anchor_proximity_score)
                + (0.15 * register_score)
                + (0.1 * octave_score)
                + (0.1 * local_support_ratio)
                + (0.05 * repeated_mode_score)
                + (0.05 * duration_score)
                - context_penalty
                - octave_neighbor_penalty
            )

            accepted = True
            rejection_reason: str | None = None
            if duplicate_existing:
                accepted = False
                rejection_reason = "duplicate_existing_note"
            elif onset_support_score < 0.2:
                accepted = False
                rejection_reason = "insufficient_onset_support"
            elif not register_ok:
                accepted = False
                rejection_reason = "out_of_register"
            elif octave_neighbor_conflict:
                accepted = False
                rejection_reason = "octave_neighbor_conflict"
            elif candidate_duration_sec < (note_config.note_dense_candidate_min_duration_ms / 1000.0) and total_score < 0.75:
                accepted = False
                rejection_reason = "candidate_too_short"
            elif unstable_context and total_score < 0.55:
                accepted = False
                rejection_reason = "unstable_local_context"
            elif octave_inconsistent and nearest_octave_distance > 4 and onset_support_score < 0.5 and local_support_ratio < 0.1:
                accepted = False
                rejection_reason = "octave_inconsistent"
            elif anchor_distance > 18 and local_support_ratio < 0.2:
                accepted = False
                rejection_reason = "pitch_far_from_anchor"
            elif total_score < 0.35 and onset_support_score < 0.5 and local_support_ratio < 0.05:
                accepted = False
                rejection_reason = "weak_local_support"

            if accepted:
                accepted_note = type(note)(
                    pitch_midi=adjusted_pitch,
                    start_sec=note.start_sec,
                    end_sec=note.end_sec,
                    confidence=note.confidence,
                )
                accepted_notes.append(accepted_note)
                collision_pool.append(accepted_note)

            candidate_rows.append(
                {
                    "bar_index": bar_index,
                    "candidate_onset_sec": float(note.start_sec),
                    "candidate_raw_pitch": raw_pitch,
                    "adjusted_pitch": int(adjusted_pitch),
                    "local_pitch_anchor": int(dominant_pitch),
                    "accepted": accepted,
                    "rejection_reason": rejection_reason,
                    "confidence_components": {
                        "onset_support_score": float(onset_support_score),
                        "anchor_proximity_score": float(anchor_proximity_score),
                        "register_score": float(register_score),
                        "octave_score": float(octave_score),
                        "local_support_ratio": float(local_support_ratio),
                        "repeated_mode_score": float(repeated_mode_score),
                        "duplicate_score": float(duplicate_score),
                        "duration_score": float(duration_score),
                        "unstable_context": bool(unstable_context),
                        "octave_neighbor_conflict": bool(octave_neighbor_conflict),
                        "total_score": float(total_score),
                        "anchor_distance_semitones": int(anchor_distance),
                        "nearest_octave_distance_semitones": int(nearest_octave_distance),
                        "repeated_note_mode": bool(repeated_note_mode),
                    },
                }
            )
        return accepted_notes, candidate_rows

    @staticmethod
    def _confidence_gate_dense_note_candidates(
        dense_candidates: list[DenseNoteCandidate],
        *,
        reference_notes: list,
        base_notes: list,
        bar_index: int,
        onset_peak_count: int,
        window_start: float,
        window_end: float,
    ) -> tuple[list[DenseNoteCandidate], list[dict[str, object]]]:
        note_config = _get_pitch_stability_config()
        local_reference = [note for note in reference_notes if window_start <= note.start_sec < window_end]
        if not local_reference:
            rejected = [
                {
                    "bar_index": bar_index,
                    "candidate_onset_sec": float(candidate.start_sec),
                    "candidate_raw_pitch": int(candidate.support.get("raw_pitch_midi", candidate.pitch_midi)),
                    "adjusted_pitch": int(candidate.pitch_midi),
                    "local_pitch_anchor": None,
                    "accepted": False,
                    "rejection_reason": "weak_local_support",
                    "confidence_components": {"total_score": 0.0, "local_support_ratio": 0.0},
                }
                for candidate in dense_candidates
            ]
            return [], rejected

        dominant_pitch = max(
            {int(note.pitch_midi) for note in local_reference},
            key=lambda pitch: sum(1 for note in local_reference if int(note.pitch_midi) == pitch),
        )
        local_counts = Counter(int(note.pitch_midi) for note in local_reference)
        repeated_note_mode = TabPipeline._is_dense_repeated_note_mode(local_counts, onset_peak_count=onset_peak_count)
        onset_support_score = max(0.0, min(1.0, float(onset_peak_count) / 8.0))
        accepted_candidates: list[DenseNoteCandidate] = []
        candidate_rows: list[dict[str, object]] = []
        collision_pool = list(base_notes)

        for candidate in dense_candidates:
            adjusted_pitch = int(candidate.pitch_midi)
            raw_pitch = int(candidate.support.get("raw_pitch_midi", candidate.pitch_midi))
            anchor_distance = abs(adjusted_pitch - dominant_pitch)
            local_support_ratio = float(local_counts.get(adjusted_pitch, 0)) / float(max(1, len(local_reference)))
            candidate_duration_sec = max(0.0, float(candidate.end_sec) - float(candidate.start_sec))
            unstable_context = TabPipeline._dense_context_is_unstable(local_reference)
            octave_neighbor_conflict = TabPipeline._has_octave_neighbor_conflict(
                collision_pool,
                candidate_start=float(candidate.start_sec),
                candidate_end=float(candidate.end_sec),
                candidate_pitch=adjusted_pitch,
                candidate_confidence=float(candidate.confidence),
                proximity_sec=max(0.08, note_config.note_merge_gap_ms / 1000.0),
            )
            duplicate_existing = any(
                abs(float(existing.start_sec) - float(candidate.start_sec)) <= 0.08 and int(existing.pitch_midi) == adjusted_pitch
                for existing in collision_pool
            )
            anchor_proximity_score = 1.0 - min(1.0, float(TabPipeline._nearest_octave_distance(adjusted_pitch, dominant_pitch)) / 12.0)
            repeated_mode_score = 1.0 if repeated_note_mode and adjusted_pitch == dominant_pitch else 0.0
            register_score = 1.0 if 28 <= adjusted_pitch <= 64 else 0.0
            duration_score = min(1.0, candidate_duration_sec / max(note_config.note_dense_candidate_min_duration_ms / 1000.0, 0.001))
            total_score = (
                (0.4 * float(candidate.confidence))
                + (0.2 * onset_support_score)
                + (0.15 * anchor_proximity_score)
                + (0.1 * local_support_ratio)
                + (0.1 * register_score)
                + (0.05 * repeated_mode_score)
                + (0.05 * duration_score)
                - (note_config.note_dense_unstable_context_penalty if unstable_context else 0.0)
                - (note_config.note_dense_octave_neighbor_penalty if octave_neighbor_conflict else 0.0)
            )

            accepted = True
            rejection_reason: str | None = None
            if duplicate_existing:
                accepted = False
                rejection_reason = "duplicate_existing_note"
            elif adjusted_pitch < 28 or adjusted_pitch > 64:
                accepted = False
                rejection_reason = "out_of_register"
            elif octave_neighbor_conflict:
                accepted = False
                rejection_reason = "octave_neighbor_conflict"
            elif candidate_duration_sec < (note_config.note_dense_candidate_min_duration_ms / 1000.0) and total_score < 0.85:
                accepted = False
                rejection_reason = "candidate_too_short"
            elif unstable_context and total_score < 0.55:
                accepted = False
                rejection_reason = "unstable_local_context"
            elif anchor_distance > 18 and local_support_ratio < 0.2:
                accepted = False
                rejection_reason = "pitch_far_from_anchor"
            elif total_score < 0.4:
                accepted = False
                rejection_reason = "weak_local_support"

            if accepted:
                accepted_candidates.append(candidate)
                collision_pool.append(candidate.to_raw_note())

            candidate_rows.append(
                {
                    "bar_index": bar_index,
                    "candidate_onset_sec": float(candidate.start_sec),
                    "candidate_raw_pitch": raw_pitch,
                    "adjusted_pitch": adjusted_pitch,
                    "local_pitch_anchor": int(dominant_pitch),
                    "accepted": accepted,
                    "rejection_reason": rejection_reason,
                    "confidence_components": {
                        "candidate_confidence": float(candidate.confidence),
                        "onset_support_score": float(onset_support_score),
                        "anchor_proximity_score": float(anchor_proximity_score),
                        "local_support_ratio": float(local_support_ratio),
                        "repeated_mode_score": float(repeated_mode_score),
                        "duration_score": float(duration_score),
                        "unstable_context": bool(unstable_context),
                        "octave_neighbor_conflict": bool(octave_neighbor_conflict),
                        "total_score": float(total_score),
                        "anchor_distance_semitones": int(anchor_distance),
                        "repeated_note_mode": bool(repeated_note_mode),
                    },
                }
            )

        return accepted_candidates, candidate_rows

    @staticmethod
    def _nearest_octave_distance(pitch_midi: int, anchor_pitch: int) -> int:
        distances = [abs((pitch_midi + (12 * offset)) - anchor_pitch) for offset in (-2, -1, 0, 1, 2)]
        return int(min(distances))

    @staticmethod
    def _dense_context_is_unstable(local_reference: list) -> bool:
        if len(local_reference) < 3:
            return False
        pitches = [int(note.pitch_midi) for note in local_reference]
        unique_pitches = len(set(pitches))
        pitch_span = max(pitches) - min(pitches)
        return unique_pitches >= 3 or (unique_pitches >= 2 and pitch_span >= 5)

    @staticmethod
    def _has_octave_neighbor_conflict(
        notes: list,
        *,
        candidate_start: float,
        candidate_end: float,
        candidate_pitch: int,
        candidate_confidence: float,
        proximity_sec: float,
    ) -> bool:
        for note in notes:
            note_pitch = int(note.pitch_midi)
            if abs(note_pitch - int(candidate_pitch)) != 12:
                continue
            note_start = float(note.start_sec)
            note_end = float(note.end_sec)
            time_close = (
                abs(note_start - candidate_start) <= proximity_sec
                or abs(note_end - candidate_start) <= proximity_sec
                or not (note_end < candidate_start or note_start > candidate_end)
            )
            if not time_close:
                continue
            if float(getattr(note, "confidence", 1.0)) + 0.05 < candidate_confidence:
                continue
            return True
        return False

    @staticmethod
    def _is_dense_repeated_note_mode(local_counts: Counter[int], *, onset_peak_count: int) -> bool:
        total = sum(local_counts.values())
        if total <= 0:
            return False
        dominant_share = max(local_counts.values()) / float(total)
        pitch_diversity = len(local_counts)
        return onset_peak_count >= 6 and pitch_diversity <= 2 and dominant_share >= 0.6

    @staticmethod
    def _dense_bar_fusion_summary(candidates: list[dict[str, object]]) -> dict[str, object]:
        accepted = [row for row in candidates if row.get("accepted") is True]
        rejected = [row for row in candidates if row.get("accepted") is False]
        reasons = Counter(str(row.get("rejection_reason")) for row in rejected if row.get("rejection_reason"))

        def avg_distance(rows: list[dict[str, object]]) -> float:
            distances = []
            for row in rows:
                confidence = row.get("confidence_components") if isinstance(row.get("confidence_components"), dict) else {}
                value = confidence.get("anchor_distance_semitones") if isinstance(confidence, dict) else None
                if isinstance(value, int | float):
                    distances.append(float(value))
            if not distances:
                return 0.0
            return sum(distances) / float(len(distances))

        return {
            "candidates": len(candidates),
            "accepted": len(accepted),
            "rejected": len(rejected),
            "rejection_histogram": dict(sorted(reasons.items())),
            "avg_pitch_distance_from_anchor_accepted": avg_distance(accepted),
            "avg_pitch_distance_from_anchor_rejected": avg_distance(rejected),
        }

    @staticmethod
    def _dense_note_fusion_summary(candidates: list[dict[str, object]]) -> dict[str, object]:
        accepted = [row for row in candidates if row.get("accepted") is True]
        rejected = [row for row in candidates if row.get("accepted") is False]
        reasons = Counter(str(row.get("rejection_reason")) for row in rejected if row.get("rejection_reason"))
        return {
            "candidates": len(candidates),
            "accepted": len(accepted),
            "rejected": len(rejected),
            "rejection_histogram": dict(sorted(reasons.items())),
        }
