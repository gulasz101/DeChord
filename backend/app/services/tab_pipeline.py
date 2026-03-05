from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from statistics import median
from tempfile import NamedTemporaryFile
from typing import Callable, Literal
import wave

from app.services.alphatex_exporter import SyncPoint, export_alphatex
from app.services.bass_transcriber import BasicPitchTranscriber, BassTranscriber
from app.services.fingering import (
    FingeredNote,
    candidate_sanity_probe,
    optimize_fingering,
    optimize_fingering_with_debug,
)
from app.services.note_cleanup import cleanup_note_events
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
    fingered_notes: list[FingeredNote]
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
    ) -> None:
        self._transcriber = transcriber or BasicPitchTranscriber()
        self._rhythm_extract_fn = rhythm_extract_fn or extract_beats_and_downbeats
        self._bar_builder_fn = bar_builder_fn or build_bars_from_beats_downbeats
        self._cleanup_fn = cleanup_fn or cleanup_note_events
        self._quantize_fn = quantize_fn or quantize_note_events
        self._fingering_fn = fingering_fn or optimize_fingering
        self._export_fn = export_fn or export_alphatex

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
        cleaned_notes = self._cleanup_fn(transcription.raw_notes)
        quantized_notes = self._quantize_fn(cleaned_notes, BarGrid(bars=bars), subdivision=subdivision)
        quality_mode_suspect_silence = tab_generation_quality_mode in {"high_accuracy", "high_accuracy_aggressive"}
        quality_diagnostics: dict[str, object] = {
            "QUALITY_MODE_SUSPECT_SILENCE": quality_mode_suspect_silence,
        }

        if quality_mode_suspect_silence:
            notes_per_bar_before = self._notes_per_bar(quantized_notes, len(bars))
            bar_rms = self._bar_rms_values(bass_wav, bars)
            onset_peaks = self._bar_onset_peaks(bass_wav, bars)
            suspect_rows: list[dict[str, object]] = []

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
                    if note_count != 0:
                        continue
                    triggered_by_rms = rms > 0 and local_median > 0 and rms >= (local_median * 0.9)
                    triggered_by_onsets = onsets >= 2
                    if triggered_by_rms or triggered_by_onsets:
                        suspect_rows.append(
                            {
                                "bar_index": bar_index,
                                "rms": rms,
                                "local_median_rms": local_median,
                                "onset_peaks": onsets,
                                "triggered_by_rms": triggered_by_rms,
                                "triggered_by_onsets": triggered_by_onsets,
                            }
                        )
            suspect_indices = [int(row["bar_index"]) for row in suspect_rows]

            second_pass_notes: list = []
            for bar_index in suspect_indices:
                bar = bars[bar_index]
                window_start = max(0.0, bar.start_sec - 0.2)
                window_end = bar.end_sec + 0.2
                second_pass_notes.extend(self._transcribe_window_with_offset(bass_wav, window_start=window_start, window_end=window_end))

            if second_pass_notes:
                merged_raw_notes = self._merge_raw_notes(transcription.raw_notes, second_pass_notes)
                cleaned_notes = self._cleanup_fn(merged_raw_notes)
                quantized_notes = self._quantize_fn(cleaned_notes, BarGrid(bars=bars), subdivision=subdivision)

            notes_per_bar_after = self._notes_per_bar(quantized_notes, len(bars))
            notes_added_second_pass = max(0, sum(notes_per_bar_after) - sum(notes_per_bar_before))
            quality_diagnostics.update(
                {
                    "suspect_silence_bars_count": len(suspect_indices),
                    "suspect_bars": suspect_rows,
                    "notes_added_second_pass": notes_added_second_pass,
                    "notes_per_bar_before_high_accuracy": notes_per_bar_before,
                    "notes_per_bar_after_high_accuracy": notes_per_bar_after,
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

        debug_info = {
            "rhythm_source": rhythm_source,
            "beat_count": len(corrected_beats),
            "downbeat_count": len(corrected_downbeats),
            "raw_note_count": len(transcription.raw_notes),
            "cleaned_note_count": len(cleaned_notes),
            "quantized_note_count": len(quantized_notes),
            "fingered_note_count": len(fingered_notes),
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
            **quality_diagnostics,
        }

        return TabPipelineResult(
            alphatex=alphatex,
            tempo_used=tempo_used,
            bars=export_bars,
            sync_points=sync_points,
            midi_bytes=transcription.midi_bytes,
            fingered_notes=fingered_notes,
            debug_info=debug_info,
        )

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
