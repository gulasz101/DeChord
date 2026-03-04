from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from app.services.alphatex_exporter import SyncPoint, export_alphatex
from app.services.bass_transcriber import BasicPitchTranscriber, BassTranscriber
from app.services.fingering import FingeredNote, optimize_fingering
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
        bars = self._bar_builder_fn(beats, downbeats, time_signature_numerator=numerator)
        if not bars:
            raise RuntimeError("No bars were produced from rhythm extraction.")

        derived_bpm = compute_derived_bpm(beats)
        tempo_used = reconcile_tempo(derived_bpm=derived_bpm, bpm_hint=bpm_hint)

        transcription = self._transcriber.transcribe(bass_wav)
        cleaned_notes = self._cleanup_fn(transcription.raw_notes)
        quantized_notes = self._quantize_fn(cleaned_notes, BarGrid(bars=bars), subdivision=subdivision)
        fingered_notes = self._fingering_fn(quantized_notes, max_fret=max_fret)

        alphatex, sync_points = self._export_fn(
            fingered_notes,
            bars,
            tempo_used=tempo_used,
            time_signature=(numerator, denominator),
            sync_every_bars=sync_every_bars,
        )

        debug_info = {
            "rhythm_source": rhythm_source,
            "beat_count": len(beats),
            "downbeat_count": len(downbeats),
            "raw_note_count": len(transcription.raw_notes),
            "cleaned_note_count": len(cleaned_notes),
            "quantized_note_count": len(quantized_notes),
            "fingered_note_count": len(fingered_notes),
            "derived_bpm": derived_bpm,
            "bpm_hint": bpm_hint,
            "tempo_used": tempo_used,
        }

        return TabPipelineResult(
            alphatex=alphatex,
            tempo_used=tempo_used,
            bars=bars,
            sync_points=sync_points,
            midi_bytes=transcription.midi_bytes,
            debug_info=debug_info,
        )
