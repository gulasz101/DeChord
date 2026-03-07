#!/usr/bin/env python
from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import asdict
from dataclasses import dataclass
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.bass_transcriber import BasicPitchTranscriber
from app.services.bass_transcriber import RawNoteEvent
from app.services.bass_transcriber import parse_midi_to_raw_notes
from app.services.fingering import optimize_fingering
from app.services.gp5_reference import ReferenceNote
from app.services.note_cleanup import cleanup_params_for_bpm
from app.services.onset_recovery import recover_missing_onsets
from app.services.onset_recovery import recovery_params_for_bpm
from app.services.quantization import QuantizedNote
from app.services.rhythm_grid import Bar
from app.services.rhythm_grid import BarGrid
from app.services.rhythm_grid import compute_derived_bpm
from app.services.rhythm_grid import reconcile_tempo
from app.services.tab_comparator import compare_tabs
from app.services.tab_pipeline import TabPipeline
from scripts.evaluate_tab_quality import REPORTS_DIR
from scripts.evaluate_tab_quality import ResolvedInputs
from scripts.evaluate_tab_quality import _song_override
from scripts.evaluate_tab_quality import parse_cli_args
from scripts.evaluate_tab_quality import prefix_for_song_name
from scripts.evaluate_tab_quality import resolve_input_paths
from scripts.evaluate_tab_quality import split_to_stems
from scripts.evaluate_tab_quality import validate_inputs


CANONICAL_INPUTS = [
    ResolvedInputs(
        song_name="Muse - Hysteria",
        mp3_path=(Path(__file__).resolve().parent.parent.parent / "test songs" / "Muse - Hysteria.mp3").resolve(),
        gp5_path=(Path(__file__).resolve().parent.parent.parent / "test songs" / "Muse - Hysteria.gp5").resolve(),
    ),
    ResolvedInputs(
        song_name="Iron Maiden - The Trooper",
        mp3_path=(Path(__file__).resolve().parent.parent.parent / "test songs" / "Iron Maiden - The Trooper.mp3").resolve(),
        gp5_path=(Path(__file__).resolve().parent.parent.parent / "test songs" / "Iron Maiden - The Trooper.gp5").resolve(),
    ),
]


@dataclass(frozen=True)
class StageBarCounts:
    bar_index: int
    reference_count: int
    final_generated_count: int
    deficit: int
    stage_counts: dict[str, int]

    def to_markdown_row(self, stage_names: list[str]) -> str:
        stage_values = " | ".join(str(self.stage_counts.get(stage, 0)) for stage in stage_names)
        return (
            f"| {self.bar_index} | {self.reference_count} | {self.final_generated_count} | {self.deficit}"
            f" | {stage_values} |"
        )


@dataclass(frozen=True)
class StageSummary:
    stage: str
    note_count: int
    onset_precision: float
    onset_recall: float
    onset_f1: float
    pitch_accuracy: float
    repeated_note_bar_count: int
    average_notes_per_dense_bar: float
    matched_notes: int
    bar_note_counts: dict[int, int]


def _bar_note_counts(notes: list[ReferenceNote]) -> dict[int, int]:
    counts: dict[int, int] = defaultdict(int)
    for note in notes:
        counts[int(note.bar_index)] += 1
    return dict(counts)


def _find_bar_index(time_sec: float, bars: list[Bar]) -> int | None:
    for idx, bar in enumerate(bars):
        if bar.start_sec <= time_sec < bar.end_sec:
            return idx
    if bars and abs(time_sec - bars[-1].end_sec) <= 1e-6:
        return len(bars) - 1
    return None


def _raw_to_reference_notes(events: list[RawNoteEvent], bars: list[Bar], *, numerator: int) -> list[ReferenceNote]:
    notes: list[ReferenceNote] = []
    for event in sorted(events, key=lambda item: (item.start_sec, item.end_sec, item.pitch_midi)):
        bar_idx = _find_bar_index(event.start_sec, bars)
        if bar_idx is None:
            continue
        bar = bars[bar_idx]
        bar_duration = max(bar.end_sec - bar.start_sec, 1e-6)
        beat_position = ((event.start_sec - bar.start_sec) / bar_duration) * numerator
        clipped_end = min(event.end_sec, bar.end_sec)
        duration_beats = max(0.05, ((clipped_end - event.start_sec) / bar_duration) * numerator)
        notes.append(
            ReferenceNote(
                bar_index=int(bar.index),
                beat_position=max(0.0, float(beat_position)),
                duration_beats=float(duration_beats),
                pitch_midi=int(event.pitch_midi),
                string=1,
                fret=0,
            )
        )
    return notes


def _quantized_to_reference_notes(notes: list[QuantizedNote]) -> list[ReferenceNote]:
    return [
        ReferenceNote(
            bar_index=int(note.bar_index),
            beat_position=float(note.beat_position),
            duration_beats=float(note.duration_beats),
            pitch_midi=int(note.pitch_midi),
            string=1,
            fret=0,
        )
        for note in notes
    ]


def _fingered_to_reference_notes(notes: list) -> list[ReferenceNote]:
    return [
        ReferenceNote(
            bar_index=int(note.bar_index),
            beat_position=float(note.beat_position),
            duration_beats=float(note.duration_beats),
            pitch_midi=int(note.pitch_midi),
            string=int(note.string),
            fret=int(note.fret),
        )
        for note in notes
    ]


def _stage_summary(
    stage: str,
    *,
    reference: list[ReferenceNote],
    generated: list[ReferenceNote],
    bpm: float,
    dense_bars: set[int],
) -> StageSummary:
    comparison = compare_tabs(
        reference,
        generated,
        beat_tolerance=0.125,
        bpm=float(bpm),
        subdivision=16,
        onset_tolerance_ms=30.0,
    )
    bar_counts = _bar_note_counts(generated)
    repeated = 0
    by_bar_pitch: dict[int, dict[int, int]] = defaultdict(lambda: defaultdict(int))
    for note in generated:
        by_bar_pitch[int(note.bar_index)][int(note.pitch_midi)] += 1
    for pitch_counts in by_bar_pitch.values():
        if any(count > 1 for count in pitch_counts.values()):
            repeated += 1

    if dense_bars:
        dense_total = sum(bar_counts.get(bar, 0) for bar in dense_bars)
        avg_dense = dense_total / float(len(dense_bars))
    else:
        avg_dense = 0.0

    return StageSummary(
        stage=stage,
        note_count=len(generated),
        onset_precision=float(comparison.onset_precision_ms),
        onset_recall=float(comparison.onset_recall_ms),
        onset_f1=float(comparison.onset_f1_ms),
        pitch_accuracy=float(comparison.pitch_accuracy),
        repeated_note_bar_count=int(repeated),
        average_notes_per_dense_bar=float(avg_dense),
        matched_notes=int(comparison.total_matched),
        bar_note_counts=bar_counts,
    )


def _dense_reference_bars(reference: list[ReferenceNote]) -> set[int]:
    counts = _bar_note_counts(reference)
    if not counts:
        return set()
    sorted_counts = sorted(counts.values())
    p75_idx = max(0, int(round((len(sorted_counts) - 1) * 0.75)))
    threshold = max(6, sorted_counts[p75_idx])
    return {bar for bar, count in counts.items() if count >= threshold}


def _onset_match_ref_indices(
    reference: list[ReferenceNote],
    generated: list[ReferenceNote],
    *,
    bpm: float,
    onset_tolerance_ms: float = 30.0,
) -> set[int]:
    tolerance_beats = abs((bpm * (onset_tolerance_ms / 1000.0)) / 60.0)
    ref_by_bar: dict[int, list[tuple[int, ReferenceNote]]] = defaultdict(list)
    gen_by_bar: dict[int, list[ReferenceNote]] = defaultdict(list)

    for idx, note in enumerate(reference):
        ref_by_bar[int(note.bar_index)].append((idx, note))
    for note in generated:
        gen_by_bar[int(note.bar_index)].append(note)

    matched_ref_indices: set[int] = set()
    for bar_idx in sorted(set(ref_by_bar) | set(gen_by_bar)):
        ref_notes = ref_by_bar.get(bar_idx, [])
        gen_notes = gen_by_bar.get(bar_idx, [])
        used_gen: set[int] = set()
        for ref_idx, ref_note in ref_notes:
            best_idx = None
            best_delta = float("inf")
            for idx, gen_note in enumerate(gen_notes):
                if idx in used_gen:
                    continue
                delta = abs(float(ref_note.beat_position) - float(gen_note.beat_position))
                if delta <= tolerance_beats and delta < best_delta:
                    best_delta = delta
                    best_idx = idx
            if best_idx is not None:
                used_gen.add(best_idx)
                matched_ref_indices.add(ref_idx)
    return matched_ref_indices


def _reference_note_tags(reference: list[ReferenceNote], dense_bars: set[int]) -> list[dict[str, bool]]:
    grouped: dict[int, list[tuple[int, ReferenceNote]]] = defaultdict(list)
    for idx, note in enumerate(reference):
        grouped[int(note.bar_index)].append((idx, note))

    tags = [{"repeated_same_pitch": False, "short_note": False, "dense_bar": False} for _ in reference]
    for bar_idx, pairs in grouped.items():
        ordered = sorted(pairs, key=lambda item: (item[1].beat_position, item[0]))
        for local_idx, (ref_idx, note) in enumerate(ordered):
            prev_same = local_idx > 0 and ordered[local_idx - 1][1].pitch_midi == note.pitch_midi
            next_same = local_idx < (len(ordered) - 1) and ordered[local_idx + 1][1].pitch_midi == note.pitch_midi
            tags[ref_idx] = {
                "repeated_same_pitch": bool(prev_same or next_same),
                "short_note": bool(note.duration_beats <= 0.5),
                "dense_bar": bool(bar_idx in dense_bars),
            }
    return tags


def _missing_concentration(
    reference: list[ReferenceNote],
    *,
    matched_ref_indices: set[int],
    dense_bars: set[int],
) -> dict[str, float]:
    tags = _reference_note_tags(reference, dense_bars)
    missing = [idx for idx in range(len(reference)) if idx not in matched_ref_indices]
    if not missing:
        return {
            "missing_count": 0,
            "share_repeated_same_pitch": 0.0,
            "share_short_note": 0.0,
            "share_dense_bar": 0.0,
        }
    return {
        "missing_count": len(missing),
        "share_repeated_same_pitch": sum(1 for idx in missing if tags[idx]["repeated_same_pitch"]) / len(missing),
        "share_short_note": sum(1 for idx in missing if tags[idx]["short_note"]) / len(missing),
        "share_dense_bar": sum(1 for idx in missing if tags[idx]["dense_bar"]) / len(missing),
    }


def bar_deficit_top_n(
    reference_counts: dict[int, int],
    final_counts: dict[int, int],
    *,
    limit: int,
    stage_counts: dict[str, dict[int, int]] | None = None,
) -> list[StageBarCounts]:
    stage_counts = stage_counts or {}
    rows: list[StageBarCounts] = []
    all_bars = sorted(set(reference_counts) | set(final_counts))
    for bar_idx in all_bars:
        ref_count = int(reference_counts.get(bar_idx, 0))
        final_count = int(final_counts.get(bar_idx, 0))
        deficit = max(0, ref_count - final_count)
        if deficit <= 0:
            continue
        rows.append(
            StageBarCounts(
                bar_index=int(bar_idx),
                reference_count=ref_count,
                final_generated_count=final_count,
                deficit=deficit,
                stage_counts={stage: int(stage_map.get(bar_idx, 0)) for stage, stage_map in stage_counts.items()},
            )
        )
    rows.sort(key=lambda row: (-row.deficit, row.bar_index))
    return rows[:limit]


def _run_song_attribution(resolved: ResolvedInputs, *, quality: str = "high_accuracy_aggressive") -> dict[str, object]:
    reference_tab, _ = validate_inputs(resolved.mp3_path, resolved.gp5_path)
    pipeline = TabPipeline()

    report_prefix = prefix_for_song_name(resolved.song_name)
    stem_dir = (Path(__file__).resolve().parent.parent / "stems" / "test_songs" / report_prefix).resolve()
    stem_dir.mkdir(parents=True, exist_ok=True)
    stems = split_to_stems(str(resolved.mp3_path), stem_dir)
    bass = next(Path(stem.relative_path) for stem in stems if stem.stem_key == "bass")
    drums = next(Path(stem.relative_path) for stem in stems if stem.stem_key == "drums")

    overrides = _song_override(resolved.song_name)
    bpm_hint = overrides.get("bpm")

    numerator, _denominator = reference_tab.time_signature
    beats, downbeats, rhythm_source = pipeline._rhythm_extract_fn(
        drums,
        time_signature_numerator=numerator,
    )
    corrected_beats, corrected_downbeats, grid_correction_applied = pipeline._correct_metrical_grid(
        beats,
        downbeats,
        song_bpm=float(bpm_hint) if isinstance(bpm_hint, float) else None,
        beats_per_bar=numerator,
    )
    bars = pipeline._bar_builder_fn(corrected_beats, corrected_downbeats, time_signature_numerator=numerator)
    if not bars:
        raise RuntimeError(f"No bars produced for {resolved.song_name}")

    derived_bpm = compute_derived_bpm(corrected_beats)
    tempo_used = (
        float(bpm_hint)
        if isinstance(bpm_hint, float)
        else reconcile_tempo(derived_bpm=derived_bpm, bpm_hint=float(bpm_hint) if isinstance(bpm_hint, float) else None)
    )

    transcription = BasicPitchTranscriber().transcribe(bass)
    raw_events = parse_midi_to_raw_notes(transcription.midi_bytes)
    stabilized_events = list(transcription.raw_notes)

    onset_times: list[float] = []
    onset_split_starts: set[float] = set()
    recovered_events = list(stabilized_events)
    if quality in {"high_accuracy", "high_accuracy_aggressive"} and stabilized_events:
        onset_times = pipeline._onset_detect_fn(bass)
        if onset_times:
            onset_kwargs = recovery_params_for_bpm(tempo_used)
            recovered_events, onset_split_starts, _split_count = recover_missing_onsets(
                stabilized_events,
                onset_times,
                **onset_kwargs,
            )

    cleanup_params = cleanup_params_for_bpm(tempo_used)

    cleaned_events = pipeline._cleanup_fn(
        recovered_events,
        **cleanup_params,
        onset_times=onset_times,
        onset_split_starts=onset_split_starts,
    )
    quantized_notes = pipeline._quantize_fn(cleaned_events, BarGrid(bars=bars), subdivision=16)

    if quality in {"high_accuracy", "high_accuracy_aggressive"}:
        notes_per_bar_before = pipeline._notes_per_bar(quantized_notes, len(bars))
        bar_rms = pipeline._bar_rms_values(bass, bars)
        onset_peaks = pipeline._bar_onset_peaks(bass, bars)
        suspect_indices: list[int] = []

        if quality == "high_accuracy":
            median_bar_rms = pipeline._median(bar_rms)
            for bar_index, note_count in enumerate(notes_per_bar_before):
                rms = bar_rms[bar_index]
                triggered_by_rms = note_count == 0 and rms > 0 and rms >= (median_bar_rms * 0.9)
                if triggered_by_rms:
                    suspect_indices.append(bar_index)
        else:
            local_medians = pipeline._local_median_rms(bar_rms, half_window=8)
            for bar_index, note_count in enumerate(notes_per_bar_before):
                rms = bar_rms[bar_index]
                local_median = local_medians[bar_index]
                onsets = onset_peaks[bar_index] if bar_index < len(onset_peaks) else 0
                triggered_by_dense_sparse = onsets >= 6 and note_count <= max(2, int(onsets * 0.25))
                triggered_by_rms = note_count == 0 and rms > 0 and local_median > 0 and rms >= (local_median * 0.9)
                triggered_by_onsets = note_count == 0 and onsets >= 2
                if triggered_by_rms or triggered_by_onsets or triggered_by_dense_sparse:
                    suspect_indices.append(bar_index)

        second_pass_notes: list[RawNoteEvent] = []
        for bar_index in suspect_indices:
            bar = bars[bar_index]
            window_start = max(0.0, bar.start_sec - 0.2)
            window_end = bar.end_sec + 0.2
            window_notes = pipeline._transcribe_window_with_offset(
                bass,
                window_start=window_start,
                window_end=window_end,
            )
            onsets = onset_peaks[bar_index] if bar_index < len(onset_peaks) else 0
            note_count = notes_per_bar_before[bar_index]
            if onsets >= 6 and note_count <= max(2, int(onsets * 0.25)):
                window_notes = pipeline._anchor_second_pass_pitches(
                    window_notes,
                    reference_notes=recovered_events,
                    window_start=window_start,
                    window_end=window_end,
                )
            second_pass_notes.extend(window_notes)

        if second_pass_notes:
            merged_raw_notes = pipeline._merge_raw_notes(stabilized_events, second_pass_notes)
            cleaned_events = pipeline._cleanup_fn(
                merged_raw_notes,
                **cleanup_params,
                onset_times=onset_times,
                onset_split_starts=onset_split_starts,
            )
            quantized_notes = pipeline._quantize_fn(cleaned_events, BarGrid(bars=bars), subdivision=16)

    fingered_notes = optimize_fingering(quantized_notes, max_fret=24)

    reference_notes = list(reference_tab.notes)
    dense_bars = _dense_reference_bars(reference_notes)

    stage_note_map: dict[str, list[ReferenceNote]] = {
        "raw_transcriber_output": _raw_to_reference_notes(raw_events, bars, numerator=numerator),
        "post_phase3_octave_stabilization": _raw_to_reference_notes(stabilized_events, bars, numerator=numerator),
        "post_onset_recovery": _raw_to_reference_notes(recovered_events, bars, numerator=numerator),
        "post_cleanup": _raw_to_reference_notes(cleaned_events, bars, numerator=numerator),
        "post_quantization": _quantized_to_reference_notes(quantized_notes),
        "post_fingering_final": _fingered_to_reference_notes(fingered_notes),
    }

    stage_summaries = [
        _stage_summary(
            stage,
            reference=reference_notes,
            generated=stage_notes,
            bpm=tempo_used,
            dense_bars=dense_bars,
        )
        for stage, stage_notes in stage_note_map.items()
    ]

    stage_name_order = [summary.stage for summary in stage_summaries]
    stage_counts_by_name = {summary.stage: summary.bar_note_counts for summary in stage_summaries}
    reference_bar_counts = _bar_note_counts(reference_notes)
    final_stage_counts = stage_summaries[-1].bar_note_counts

    worst_rows = bar_deficit_top_n(
        reference_bar_counts,
        final_stage_counts,
        limit=10,
        stage_counts={name: stage_counts_by_name[name] for name in stage_name_order},
    )

    matched_raw = _onset_match_ref_indices(reference_notes, stage_note_map["raw_transcriber_output"], bpm=tempo_used)
    matched_final = _onset_match_ref_indices(reference_notes, stage_note_map["post_fingering_final"], bpm=tempo_used)

    recall_by_stage = {summary.stage: summary.onset_recall for summary in stage_summaries}
    ordered = stage_summaries
    stage_drops = []
    for idx in range(1, len(ordered)):
        prev_stage = ordered[idx - 1]
        cur_stage = ordered[idx]
        stage_drops.append(
            {
                "from": prev_stage.stage,
                "to": cur_stage.stage,
                "recall_delta": cur_stage.onset_recall - prev_stage.onset_recall,
                "note_count_delta": cur_stage.note_count - prev_stage.note_count,
            }
        )

    bottleneck = min(stage_drops, key=lambda item: item["recall_delta"]) if stage_drops else None

    return {
        "song": resolved.song_name,
        "quality": quality,
        "paths": {
            "mp3": str(resolved.mp3_path),
            "gp5": str(resolved.gp5_path),
            "bass_stem": str(bass),
            "drums_stem": str(drums),
        },
        "rhythm": {
            "rhythm_source": rhythm_source,
            "grid_correction_applied": grid_correction_applied,
            "bars": len(bars),
            "tempo_used": tempo_used,
            "derived_bpm": derived_bpm,
        },
        "reference": {
            "note_count": len(reference_notes),
            "dense_bar_indices": sorted(dense_bars),
            "bar_note_counts": reference_bar_counts,
        },
        "stages": [asdict(summary) for summary in stage_summaries],
        "stage_drops": stage_drops,
        "bottleneck": bottleneck,
        "phase4b": {
            "missing_in_raw": _missing_concentration(reference_notes, matched_ref_indices=matched_raw, dense_bars=dense_bars),
            "missing_in_final": _missing_concentration(
                reference_notes,
                matched_ref_indices=matched_final,
                dense_bars=dense_bars,
            ),
            "raw_onset_recall": recall_by_stage.get("raw_transcriber_output", 0.0),
            "final_onset_recall": recall_by_stage.get("post_fingering_final", 0.0),
            "bottleneck_stage": bottleneck,
            "transcription_engine_used": transcription.engine,
        },
        "worst_bars": [
            {
                "bar_index": row.bar_index,
                "reference_count": row.reference_count,
                "final_generated_count": row.final_generated_count,
                "deficit": row.deficit,
                "stage_counts": row.stage_counts,
            }
            for row in worst_rows
        ],
    }


def _write_hysteria_markdown(hysteria: dict[str, object]) -> str:
    stages = hysteria["stages"]
    lines = [
        "# Hysteria Phase 4 Stage Attribution",
        "",
        "## Stage Metrics",
        "",
        "| stage | note_count | onset_precision | onset_recall | onset_f1 | pitch_accuracy | repeated_note_bars | avg_notes_per_dense_bar |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for stage in stages:
        lines.append(
            "| {stage} | {note_count} | {onset_precision:.4f} | {onset_recall:.4f} | {onset_f1:.4f} | "
            "{pitch_accuracy:.4f} | {repeated_note_bar_count} | {average_notes_per_dense_bar:.2f} |".format(**stage)
        )

    phase4b = hysteria["phase4b"]
    bottleneck = phase4b.get("bottleneck_stage") or {}
    lines.extend(
        [
            "",
            "## Phase 4B Conclusion",
            "",
            f"- Transcription engine: `{phase4b.get('transcription_engine_used', 'unknown')}`.",
            (
                "- Missing notes in raw BasicPitch output: "
                f"{phase4b['missing_in_raw']['missing_count']} "
                f"(raw onset recall {phase4b['raw_onset_recall']:.4f})."
            ),
            (
                "- Missing notes in final output: "
                f"{phase4b['missing_in_final']['missing_count']} "
                f"(final onset recall {phase4b['final_onset_recall']:.4f})."
            ),
            (
                "- Largest recall drop stage: "
                f"`{bottleneck.get('from', 'n/a')}` -> `{bottleneck.get('to', 'n/a')}` "
                f"(delta {float(bottleneck.get('recall_delta', 0.0)):.4f})."
            ),
            (
                "- Missing-note concentration (final): repeated-same-pitch "
                f"{phase4b['missing_in_final']['share_repeated_same_pitch']:.2%}, "
                f"short-note {phase4b['missing_in_final']['share_short_note']:.2%}, "
                f"dense-bar {phase4b['missing_in_final']['share_dense_bar']:.2%}."
            ),
        ]
    )

    return "\n".join(lines) + "\n"


def _write_hysteria_worst_bars_markdown(hysteria: dict[str, object]) -> str:
    stage_names = [stage["stage"] for stage in hysteria["stages"]]
    lines = [
        "# Hysteria Phase 4 Worst Bars",
        "",
        "Bars ranked by largest reference-vs-final onset deficit.",
        "",
    ]
    header = "| bar | ref_count | final_count | deficit | " + " | ".join(stage_names) + " |"
    separator = "|---|---:|---:|---:|" + "---:|" * len(stage_names)
    lines.extend([header, separator])

    for row in hysteria["worst_bars"]:
        stage_counts = " | ".join(str(int(row["stage_counts"].get(stage, 0))) for stage in stage_names)
        lines.append(
            f"| {int(row['bar_index'])} | {int(row['reference_count'])} | {int(row['final_generated_count'])} | "
            f"{int(row['deficit'])} | {stage_counts} |"
        )

    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    args = parse_cli_args(argv)
    resolved = resolve_input_paths(args)

    if args.mp3 and args.gp5:
        targets = [resolved]
    else:
        targets = CANONICAL_INPUTS

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    outputs: dict[str, dict[str, object]] = {}

    for target in targets:
        report = _run_song_attribution(target, quality=args.quality)
        song_key = prefix_for_song_name(target.song_name)
        outputs[song_key] = report

        if song_key == "muse__hysteria":
            (REPORTS_DIR / "hysteria_phase4_stage_attribution.json").write_text(
                json.dumps(report, indent=2, sort_keys=True)
            )
            (REPORTS_DIR / "hysteria_phase4_stage_attribution.md").write_text(_write_hysteria_markdown(report))
            (REPORTS_DIR / "hysteria_phase4_worst_bars.md").write_text(_write_hysteria_worst_bars_markdown(report))
        if song_key == "iron_maiden__the_trooper":
            (REPORTS_DIR / "trooper_phase4_stage_attribution.json").write_text(
                json.dumps(report, indent=2, sort_keys=True)
            )

    print(json.dumps({"generated": sorted(outputs.keys())}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
