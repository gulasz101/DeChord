# backend/app/main.py
import asyncio
from dataclasses import replace
import hashlib
import logging
import os
import re
import shutil
import tempfile
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Literal

logger = logging.getLogger(__name__)

from fastapi import FastAPI, File, Form, HTTPException, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.analysis import AnalysisResult, analyze_audio
from app.db import (
    claim_identity_user,
    close_db,
    execute,
    get_default_project,
    get_default_user,
    get_user_by_id,
    init_db,
    resolve_identity_user,
)
from app.midi import transcribe_bass_stem_to_midi
from app.models import ProcessMode
from app.pipeline_presets import active_pipeline_preset_name, resolve_pipeline_preset
from app.services.tab_pipeline import FingeringCollapseError, TabPipeline
from app.stems import (
    BassAnalysisStemResult,
    StemResult,
    _get_stem_analysis_config,
    build_stems_zip,
    build_bass_analysis_stem,
    split_to_stems,
)
from app.tabs import build_gp5_from_tab_positions, map_midi_to_eadg_positions

app = FastAPI(title="DeChord API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
STEMS_DIR = Path("stems")
STEMS_DIR.mkdir(exist_ok=True)

# In-memory job store (single-user local)
jobs: dict[str, dict] = {}
executor = ThreadPoolExecutor(max_workers=2)
tab_pipeline = TabPipeline()


def _get_analysis_config_for_quality_mode(
    quality_mode: Literal["standard", "high_accuracy", "high_accuracy_aggressive"],
):
    config = _get_stem_analysis_config()
    preset_name = active_pipeline_preset_name()
    preset = resolve_pipeline_preset(preset_name) if preset_name is not None else None
    quality_mode_auto_ensemble = (
        preset.stem_defaults.auto_enable_quality_mode_ensemble
        if preset is not None
        else True
    )
    should_enable_ensemble = config.enable_model_ensemble or (
        quality_mode_auto_ensemble
        and quality_mode
        in {
            "high_accuracy",
            "high_accuracy_aggressive",
        }
    )
    if should_enable_ensemble == config.enable_model_ensemble:
        return config
    return replace(config, enable_model_ensemble=should_enable_ensemble)


def _get_uploaded_stems_analysis_config(
    quality_mode: Literal["standard", "high_accuracy", "high_accuracy_aggressive"],
):
    config = _get_analysis_config_for_quality_mode(quality_mode)
    if not config.enable_model_ensemble:
        return config
    logger.info(
        "Uploaded Demucs stems route has no source mix; disabling ensemble candidate reseparation for analysis."
    )
    return replace(config, enable_model_ensemble=False)


class NoteCreate(BaseModel):
    type: Literal["time", "chord"]
    text: str = Field(min_length=1)
    timestamp_sec: float | None = None
    chord_index: int | None = None
    toast_duration_sec: float | None = None


class NoteUpdate(BaseModel):
    text: str | None = None
    toast_duration_sec: float | None = None


class NoteResolveUpdate(BaseModel):
    resolved: bool


class PlaybackPrefsUpdate(BaseModel):
    speed_percent: int = Field(ge=40, le=200)
    volume: float = Field(ge=0.0, le=1.0)
    loop_start_index: int | None = None
    loop_end_index: int | None = None


class IdentityResolveRequest(BaseModel):
    fingerprint_token: str = Field(min_length=6, max_length=256)


class IdentityClaimRequest(BaseModel):
    user_id: int
    username: str = Field(
        min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9_][a-zA-Z0-9_.-]*$"
    )
    password: str = Field(min_length=8, max_length=256)


class SongTabRegenerateRequest(BaseModel):
    source_stem_key: str = Field(min_length=1, max_length=64)


class BandCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=128)


class ProjectCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=512)


def _row_to_dict(row) -> dict:
    return row.asdict() if hasattr(row, "asdict") else dict(row)


def _build_author_avatar(display_name: str | None) -> str | None:
    if display_name is None:
        return None
    parts = [part[0].upper() for part in display_name.split() if part]
    if not parts:
        return None
    return "".join(parts[:2])


async def _load_song_notes(song_id: int) -> list[dict]:
    notes_rs = await execute(
        """
        SELECT
            id,
            author_user_id,
            author_name,
            author_avatar,
            type,
            timestamp_sec,
            chord_index,
            text,
            toast_duration_sec,
            resolved,
            created_at,
            updated_at
        FROM notes
        WHERE song_id = ?
        ORDER BY created_at ASC, id ASC
        """,
        [song_id],
    )
    return [
        {
            "id": row[0],
            "author_user_id": row[1],
            "author_name": row[2],
            "author_avatar": row[3],
            "type": row[4],
            "timestamp_sec": row[5],
            "chord_index": row[6],
            "text": row[7],
            "toast_duration_sec": row[8],
            "resolved": bool(row[9]),
            "created_at": row[10],
            "updated_at": row[11],
        }
        for row in notes_rs.rows
    ]


async def _create_song_record(
    filename: str | None,
    mime_type: str | None,
    audio_blob: bytes,
    *,
    project_id: int | None = None,
) -> int:
    user = await get_default_user()
    resolved_project_id = project_id
    if resolved_project_id is None:
        project = await get_default_project()
        resolved_project_id = int(project["id"])
    title = Path(filename or "Untitled").stem or "Untitled"
    rs = await execute(
        """
        INSERT INTO songs (user_id, project_id, title, original_filename, mime_type, audio_blob)
        VALUES (?, ?, ?, ?, ?, ?)
        RETURNING id
        """,
        [user["id"], resolved_project_id, title, filename, mime_type, audio_blob],
    )
    return int(rs.rows[0][0])


async def _persist_analysis(song_id: int, result: AnalysisResult) -> None:
    # Keep one latest analysis per song for simplicity.
    prev = await execute("SELECT id FROM analyses WHERE song_id = ?", [song_id])
    for row in prev.rows:
        analysis_id = int(row[0])
        await execute(
            "DELETE FROM analysis_chords WHERE analysis_id = ?", [analysis_id]
        )
    await execute("DELETE FROM analyses WHERE song_id = ?", [song_id])

    analysis_insert = await execute(
        """
        INSERT INTO analyses (song_id, song_key, tempo, duration)
        VALUES (?, ?, ?, ?)
        RETURNING id
        """,
        [song_id, result.key, result.tempo, result.duration],
    )
    analysis_id = int(analysis_insert.rows[0][0])

    for idx, chord in enumerate(result.chords):
        await execute(
            """
            INSERT INTO analysis_chords (analysis_id, chord_index, start_sec, end_sec, label)
            VALUES (?, ?, ?, ?, ?)
            """,
            [analysis_id, idx, chord.start, chord.end, chord.label],
        )


async def _persist_stems(song_id: int, stems: list[StemResult]) -> None:
    await _persist_generated_stems(song_id, stems)


def _is_user_uploaded_stem_path(relative_path: str) -> bool:
    path = Path(relative_path)
    return any(part in {"upload", "uploads", "uploaded"} for part in path.parts)


def _build_stem_display_name(
    stem_key: str, relative_path: str, source_type: str
) -> str:
    path = Path(relative_path)
    if source_type == "user" and path.name:
        return path.name
    return stem_key.replace("_", " ").title()


def _build_version_label(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


async def _serialize_song_stem(row) -> dict:
    source_type = str(row[5] or "system")
    display_name = row[6] or _build_stem_display_name(
        str(row[1]), str(row[2]), source_type
    )
    version_label = row[7] or "legacy"
    uploaded_by_name = row[8]
    return {
        "id": int(row[0]),
        "stem_key": row[1],
        "source_type": source_type,
        "display_name": display_name,
        "version_label": version_label,
        "uploaded_by_name": uploaded_by_name,
        "is_archived": False,
        "relative_path": row[2],
        "mime_type": row[3],
        "duration": row[4],
        "created_at": row[9],
    }


async def _load_active_song_stem(song_id: int, stem_key: str) -> dict | None:
    rs = await execute(
        """
        SELECT id, stem_key, relative_path, mime_type, duration, source_type, display_name, version_label, uploaded_by_name, created_at
        FROM song_stems
        WHERE song_id = ? AND stem_key = ?
        LIMIT 1
        """,
        [song_id, stem_key],
    )
    if not rs.rows:
        return None
    return await _serialize_song_stem(rs.rows[0])


async def _replace_song_stem(
    song_id: int,
    *,
    stem_key: str,
    relative_path: str,
    mime_type: str | None,
    duration: float | None,
    source_type: str,
    display_name: str,
    version_label: str,
    uploaded_by_name: str | None,
) -> None:
    await execute(
        "DELETE FROM song_stems WHERE song_id = ? AND stem_key = ?",
        [song_id, stem_key],
    )
    await execute(
        """
        INSERT INTO song_stems (
            song_id, stem_key, relative_path, mime_type, duration, source_type, display_name, version_label, uploaded_by_name
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            song_id,
            stem_key,
            relative_path,
            mime_type,
            duration,
            source_type,
            display_name,
            version_label,
            uploaded_by_name,
        ],
    )


async def _persist_generated_stems(song_id: int, stems: list[StemResult]) -> None:
    regen_version = _build_version_label("regen")
    generated_keys = {stem.stem_key for stem in stems}
    existing_stems = await _load_song_stems(song_id)
    for stem in existing_stems:
        if stem["source_type"] != "system":
            continue
        if stem["stem_key"] in generated_keys:
            continue
        await execute(
            "DELETE FROM song_stems WHERE song_id = ? AND stem_key = ?",
            [song_id, stem["stem_key"]],
        )
    for stem in stems:
        current = await _load_active_song_stem(song_id, stem.stem_key)
        if current is not None and current["source_type"] == "user":
            continue
        await _replace_song_stem(
            song_id,
            stem_key=stem.stem_key,
            relative_path=stem.relative_path,
            mime_type=stem.mime_type,
            duration=stem.duration,
            source_type="system",
            display_name=_build_stem_display_name(
                stem.stem_key, stem.relative_path, "system"
            ),
            version_label=regen_version,
            uploaded_by_name=None,
        )


async def _persist_midi(
    song_id: int,
    *,
    source_stem_key: str,
    midi_blob: bytes,
    engine: str,
    provenance: dict | None = None,
    status: str = "complete",
    error_message: str | None = None,
) -> int:
    stem = (
        provenance
        if provenance is not None
        else await _load_active_song_stem(song_id, source_stem_key)
    )
    await execute(
        "DELETE FROM song_midis WHERE song_id = ? AND source_stem_key = ?",
        [song_id, source_stem_key],
    )
    rs = await execute(
        """
        INSERT INTO song_midis (
            song_id,
            source_stem_key,
            source_stem_id,
            source_stem_source_type,
            source_stem_display_name,
            source_stem_version_label,
            source_stem_uploaded_by_name,
            midi_blob,
            midi_format,
            engine,
            status,
            error_message
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'mid', ?, ?, ?)
        RETURNING id
        """,
        [
            song_id,
            source_stem_key,
            stem["id"] if stem is not None else None,
            stem["source_type"] if stem is not None else "system",
            stem["display_name"]
            if stem is not None
            else _build_stem_display_name(source_stem_key, source_stem_key, "system"),
            stem["version_label"] if stem is not None else "transient",
            stem["uploaded_by_name"] if stem is not None else None,
            midi_blob,
            engine,
            status,
            error_message,
        ],
    )
    return int(rs.rows[0][0])


async def _persist_tab(
    song_id: int,
    *,
    source_midi_id: int,
    tab_blob: bytes,
    tab_format: str = "gp5",
    tuning: str = "E1,A1,D2,G2",
    strings: int = 4,
    generator_version: str = "v1",
    status: str = "complete",
    error_message: str | None = None,
) -> None:
    await execute("DELETE FROM song_tabs WHERE song_id = ?", [song_id])
    await execute(
        """
        INSERT INTO song_tabs (
            song_id, source_midi_id, tab_blob, tab_format, tuning, strings, generator_version, status, error_message
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            song_id,
            source_midi_id,
            tab_blob,
            tab_format,
            tuning,
            strings,
            generator_version,
            status,
            error_message,
        ],
    )


def _generate_gp5_from_midi(midi_blob: bytes) -> bytes:
    tab_notes = map_midi_to_eadg_positions(midi_blob)
    if not tab_notes:
        raise RuntimeError("No playable EADG notes were generated from MIDI.")
    return build_gp5_from_tab_positions(tab_notes)


async def _load_latest_analysis(song_id: int) -> dict | None:
    analysis_rs = await execute(
        """
        SELECT id, song_key, tempo, duration
        FROM analyses
        WHERE song_id = ?
        ORDER BY created_at DESC, id DESC
        LIMIT 1
        """,
        [song_id],
    )
    if not analysis_rs.rows:
        return None

    analysis = _row_to_dict(analysis_rs.rows[0])
    chords_rs = await execute(
        """
        SELECT chord_index, start_sec, end_sec, label
        FROM analysis_chords
        WHERE analysis_id = ?
        ORDER BY chord_index ASC
        """,
        [analysis["id"]],
    )

    return {
        "key": analysis["song_key"],
        "tempo": analysis["tempo"],
        "duration": analysis["duration"],
        "chords": [
            {
                "start": row[1],
                "end": row[2],
                "label": row[3],
            }
            for row in chords_rs.rows
        ],
    }


async def _load_song_row(song_id: int) -> dict | None:
    song_rs = await execute(
        """
        SELECT id, title, original_filename, mime_type, audio_blob, created_at
        FROM songs
        WHERE id = ?
        LIMIT 1
        """,
        [song_id],
    )
    if not song_rs.rows:
        return None
    row = song_rs.rows[0]
    return {
        "id": int(row[0]),
        "title": row[1],
        "original_filename": row[2],
        "mime_type": row[3],
        "audio_blob": row[4],
        "created_at": row[5],
    }


async def _load_song_stems(song_id: int) -> list[dict]:
    stems_rs = await execute(
        """
        SELECT id, stem_key, relative_path, mime_type, duration, source_type, display_name, version_label, uploaded_by_name, created_at
        FROM song_stems
        WHERE song_id = ?
        ORDER BY stem_key ASC
        """,
        [song_id],
    )
    return [await _serialize_song_stem(row) for row in stems_rs.rows]


async def _load_song_tab_meta(song_id: int) -> dict | None:
    rs = await execute(
        """
        SELECT
            t.id,
            m.source_stem_key,
            t.source_midi_id,
            m.source_stem_id,
            m.source_stem_source_type,
            m.source_stem_display_name,
            m.source_stem_version_label,
            t.tab_format,
            t.tuning,
            t.strings,
            t.generator_version,
            t.status,
            t.error_message,
            t.created_at,
            t.updated_at
        FROM song_tabs t
        JOIN song_midis m ON m.id = t.source_midi_id
        WHERE t.song_id = ?
        ORDER BY t.updated_at DESC, t.id DESC
        LIMIT 1
        """,
        [song_id],
    )
    if not rs.rows:
        return None
    row = rs.rows[0]
    return {
        "id": row[0],
        "source_stem_key": row[1],
        "source_midi_id": row[2],
        "source_stem_id": row[3],
        "source_type": row[4],
        "source_display_name": row[5]
        or _build_stem_display_name(str(row[1]), str(row[1]), str(row[4] or "system")),
        "source_version_label": row[6],
        "tab_format": row[7],
        "tuning": row[8],
        "strings": row[9],
        "generator_version": row[10],
        "status": row[11],
        "error_message": row[12],
        "created_at": row[13],
        "updated_at": row[14],
    }


def _write_song_audio_tempfile(
    song_id: int, original_filename: str | None, audio_blob: bytes
) -> Path:
    suffix = Path(original_filename or "").suffix or ".mp3"
    temp_dir = Path(tempfile.mkdtemp(prefix=f"dechord-song-{song_id}-"))
    audio_path = temp_dir / f"source{suffix}"
    audio_path.write_bytes(audio_blob)
    return audio_path


async def _regenerate_song_tabs(song_id: int, source_stem_key: str) -> dict:
    stems = await _load_song_stems(song_id)
    stems_by_key = {
        str(stem["stem_key"]): Path(str(stem["relative_path"])) for stem in stems
    }
    if source_stem_key not in stems_by_key:
        raise HTTPException(404, "Requested source stem not found.")
    drums_path = stems_by_key.get("drums")
    if drums_path is None:
        raise HTTPException(422, "Drums stem missing; cannot build rhythm grid.")
    analysis_stems = dict(stems_by_key)
    analysis_stems["bass"] = stems_by_key[source_stem_key]

    analysis_output_dir = STEMS_DIR / str(song_id) / "analysis"
    analysis_output_dir.mkdir(parents=True, exist_ok=True)
    analysis_stem_result = build_bass_analysis_stem(
        stems=analysis_stems,
        output_dir=analysis_output_dir,
        analysis_config=_get_uploaded_stems_analysis_config("standard"),
        source_audio_path=None,
    )
    tab_result = tab_pipeline.run(
        analysis_stem_result.path,
        drums_path,
        bpm_hint=None,
        time_signature=(4, 4),
        subdivision=16,
        max_fret=24,
        sync_every_bars=8,
        tab_generation_quality_mode="standard",
        onset_recovery=None,
    )
    midi_id = await _persist_midi(
        song_id,
        source_stem_key=source_stem_key,
        midi_blob=tab_result.midi_bytes,
        engine="basic_pitch",
    )
    await _persist_tab(
        song_id,
        source_midi_id=midi_id,
        tab_blob=tab_result.alphatex.encode("utf-8"),
        tab_format="alphatex",
        generator_version="v2-rhythm-grid",
    )
    tab_meta = await _load_song_tab_meta(song_id)
    if tab_meta is None:
        raise RuntimeError("Expected tab metadata after regeneration.")
    return tab_meta


def _run_analysis(job_id: str, audio_path: str, song_id: int):
    def set_stage(
        stage: str,
        *,
        message: str,
        progress_pct: float,
        stage_progress_pct: float,
    ) -> None:
        job = jobs[job_id]
        job["stage"] = stage
        job["message"] = message
        job["progress"] = message
        job["progress_pct"] = progress_pct
        job["stage_progress_pct"] = stage_progress_pct
        history = job.setdefault("stage_history", [])
        if not history or history[-1] != stage:
            history.append(stage)

    try:
        jobs[job_id]["status"] = "processing"
        set_stage(
            "analyzing_chords",
            message="Analyzing audio...",
            progress_pct=40,
            stage_progress_pct=50,
        )
        result = analyze_audio(audio_path)

        if jobs[job_id].get("process_mode") == "analysis_and_stems":
            logger.info("Job %s: starting stem splitting for song %s", job_id, song_id)
            try:
                set_stage(
                    "splitting_stems",
                    message="Splitting stems...",
                    progress_pct=45,
                    stage_progress_pct=0,
                )
                stems = split_to_stems(
                    audio_path=audio_path,
                    output_dir=STEMS_DIR / str(song_id),
                    on_progress=lambda stage_pct, msg: set_stage(
                        "splitting_stems",
                        message=msg,
                        progress_pct=min(45 + stage_pct * 0.5, 95),
                        stage_progress_pct=stage_pct,
                    ),
                )
                asyncio.run(_persist_stems(song_id, stems))
                jobs[job_id]["stems_status"] = "complete"
                jobs[job_id]["stems_error"] = None
                bass_stem = next(
                    (stem for stem in stems if stem.stem_key == "bass"), None
                )
                drums_stem = next(
                    (stem for stem in stems if stem.stem_key == "drums"), None
                )
                analysis_stem_result: BassAnalysisStemResult | None = None
                if bass_stem is None:
                    jobs[job_id]["midi_status"] = "failed"
                    jobs[job_id]["midi_error"] = (
                        "Bass stem missing; cannot transcribe MIDI."
                    )
                    jobs[job_id]["tab_status"] = "not_requested"
                    jobs[job_id]["tab_error"] = None
                elif drums_stem is None:
                    jobs[job_id]["midi_status"] = "not_requested"
                    jobs[job_id]["midi_error"] = None
                    jobs[job_id]["tab_status"] = "failed"
                    jobs[job_id]["tab_error"] = (
                        "Drums stem missing; cannot build rhythm grid."
                    )
                else:
                    try:
                        tab_generation_quality = jobs[job_id].get(
                            "tab_generation_quality", "standard"
                        )
                        stem_paths = {
                            stem.stem_key: Path(stem.relative_path) for stem in stems
                        }
                        analysis_output_dir = STEMS_DIR / str(song_id) / "analysis"
                        analysis_output_dir.mkdir(parents=True, exist_ok=True)
                        analysis_stem_result = build_bass_analysis_stem(
                            stems=stem_paths,
                            output_dir=analysis_output_dir,
                            analysis_config=_get_analysis_config_for_quality_mode(
                                tab_generation_quality
                            ),
                            source_audio_path=Path(audio_path),
                        )
                        jobs[job_id]["analysis_stem_path"] = str(
                            analysis_stem_result.path
                        )
                        jobs[job_id]["analysis_stem_diagnostics"] = (
                            analysis_stem_result.diagnostics
                        )
                        set_stage(
                            "transcribing_bass_midi",
                            message="Transcribing bass stem to MIDI...",
                            progress_pct=90,
                            stage_progress_pct=0,
                        )
                        tab_result = tab_pipeline.run(
                            analysis_stem_result.path,
                            Path(drums_stem.relative_path),
                            bpm_hint=float(result.tempo) if result.tempo else None,
                            time_signature=(4, 4),
                            subdivision=16,
                            max_fret=24,
                            sync_every_bars=8,
                            tab_generation_quality_mode=tab_generation_quality,
                            onset_recovery=jobs[job_id].get("tab_onset_recovery"),
                        )
                        midi_id = asyncio.run(
                            _persist_midi(
                                song_id,
                                source_stem_key="bass",
                                midi_blob=tab_result.midi_bytes,
                                engine="basic_pitch",
                            )
                        )
                        jobs[job_id]["midi_status"] = "complete"
                        jobs[job_id]["midi_error"] = None

                        set_stage(
                            "generating_tabs",
                            message="Generating bass tabs...",
                            progress_pct=93,
                            stage_progress_pct=0,
                        )
                        asyncio.run(
                            _persist_tab(
                                song_id,
                                source_midi_id=midi_id,
                                tab_blob=tab_result.alphatex.encode("utf-8"),
                                tab_format="alphatex",
                                generator_version="v2-rhythm-grid",
                            )
                        )
                        jobs[job_id]["tab_status"] = "complete"
                        jobs[job_id]["tab_error"] = None
                        jobs[job_id]["tab_debug_info"] = {
                            **tab_result.debug_info,
                            "analysis_stem_path": str(analysis_stem_result.path),
                            "analysis_stem_diagnostics": analysis_stem_result.diagnostics,
                        }
                    except FingeringCollapseError as exc:
                        logger.error(
                            "Job %s: phase2 tab pipeline fingering collapse: %s",
                            job_id,
                            exc,
                            exc_info=True,
                        )
                        jobs[job_id]["midi_status"] = "failed"
                        jobs[job_id]["midi_error"] = str(exc)
                        jobs[job_id]["tab_status"] = "failed"
                        jobs[job_id]["tab_error"] = str(exc)
                        jobs[job_id]["tab_debug_info"] = exc.debug_info
                    except Exception as exc:
                        logger.error(
                            "Job %s: phase2 tab pipeline failed: %s",
                            job_id,
                            exc,
                            exc_info=True,
                        )
                        jobs[job_id]["midi_status"] = "failed"
                        jobs[job_id]["midi_error"] = str(exc)
                        jobs[job_id]["tab_status"] = "not_requested"
                        jobs[job_id]["tab_error"] = None
                logger.info("Job %s: stem splitting complete", job_id)
            except Exception as exc:
                logger.error(
                    "Job %s: stem splitting failed: %s", job_id, exc, exc_info=True
                )
                jobs[job_id]["stems_status"] = "failed"
                jobs[job_id]["stems_error"] = str(exc)
                jobs[job_id]["midi_status"] = "not_requested"
                jobs[job_id]["midi_error"] = None
                jobs[job_id]["tab_status"] = "not_requested"
                jobs[job_id]["tab_error"] = None
        else:
            logger.info(
                "Job %s: stems not requested (mode=%s)",
                job_id,
                jobs[job_id].get("process_mode"),
            )
            jobs[job_id]["stems_status"] = "not_requested"
            jobs[job_id]["stems_error"] = None
            jobs[job_id]["midi_status"] = "not_requested"
            jobs[job_id]["midi_error"] = None
            jobs[job_id]["tab_status"] = "not_requested"
            jobs[job_id]["tab_error"] = None

        set_stage(
            "persisting",
            message="Saving analysis...",
            progress_pct=95,
            stage_progress_pct=100,
        )
        asyncio.run(_persist_analysis(song_id, result))
        jobs[job_id]["status"] = "complete"
        set_stage(
            "complete",
            message="Completed",
            progress_pct=100,
            stage_progress_pct=100,
        )
        jobs[job_id]["result"] = result
        jobs[job_id]["error"] = None
    except Exception as e:
        jobs[job_id]["status"] = "error"
        set_stage(
            "error",
            message="Failed",
            progress_pct=100,
            stage_progress_pct=100,
        )
        jobs[job_id]["error"] = str(e)


@app.on_event("startup")
async def startup_event():
    await init_db()


@app.on_event("shutdown")
async def shutdown_event():
    await close_db()


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.post("/api/identity/resolve")
async def resolve_identity(payload: IdentityResolveRequest):
    user = await resolve_identity_user(payload.fingerprint_token)
    return {"user": user}


@app.post("/api/identity/claim")
async def claim_identity(payload: IdentityClaimRequest):
    user = await get_user_by_id(payload.user_id)
    if user is None:
        raise HTTPException(404, "User not found")

    password_hash = hashlib.sha256(payload.password.encode("utf-8")).hexdigest()
    try:
        claimed = await claim_identity_user(
            user_id=payload.user_id,
            username=payload.username,
            password_hash=password_hash,
        )
    except Exception as exc:
        if "UNIQUE constraint failed: users.username" in str(exc):
            raise HTTPException(409, "Username already taken") from exc
        raise

    if claimed is None:
        raise HTTPException(404, "User not found")
    return {"user": claimed}


@app.post("/api/bands")
async def create_band(payload: BandCreateRequest):
    user = await get_default_user()
    created = await execute(
        """
        INSERT INTO bands (name, owner_user_id)
        VALUES (?, ?)
        RETURNING id, name, owner_user_id, created_at
        """,
        [payload.name.strip(), user["id"]],
    )
    row = created.rows[0]
    band_id = int(row[0])
    await execute(
        """
        INSERT INTO band_memberships (band_id, user_id, role)
        VALUES (?, ?, 'owner')
        ON CONFLICT(band_id, user_id) DO UPDATE SET
            role = 'owner',
            updated_at = CURRENT_TIMESTAMP
        """,
        [band_id, user["id"]],
    )
    return {
        "band": {
            "id": band_id,
            "name": row[1],
            "owner_user_id": int(row[2]),
            "created_at": row[3],
            "project_count": 0,
        }
    }


@app.post("/api/bands/{band_id}/projects")
async def create_project(band_id: int, payload: ProjectCreateRequest):
    band_rs = await execute("SELECT id FROM bands WHERE id = ? LIMIT 1", [band_id])
    if not band_rs.rows:
        raise HTTPException(404, "Band not found")
    created = await execute(
        """
        INSERT INTO projects (band_id, name, description)
        VALUES (?, ?, ?)
        RETURNING id, band_id, name, description, created_at
        """,
        [band_id, payload.name.strip(), payload.description],
    )
    row = created.rows[0]
    return {
        "project": {
            "id": int(row[0]),
            "band_id": int(row[1]),
            "name": row[2],
            "description": row[3],
            "created_at": row[4],
            "song_count": 0,
        }
    }


def _parse_time_signature(time_signature: str) -> tuple[int, int]:
    match = re.match(r"^\s*(\d+)\s*/\s*(\d+)\s*$", time_signature or "")
    if not match:
        raise HTTPException(
            400, "time_signature must use the form 'N/D' (for example '4/4')."
        )
    numerator = int(match.group(1))
    denominator = int(match.group(2))
    if numerator <= 0 or denominator <= 0:
        raise HTTPException(400, "time_signature values must be positive.")
    return numerator, denominator


@app.post("/api/tab/from-demucs-stems")
async def tab_from_demucs_stems(
    bass: UploadFile = File(...),
    drums: UploadFile = File(...),
    other: UploadFile | None = File(None),
    guitar: UploadFile | None = File(None),
    song_id: int | None = Form(None),
    bpm: float | None = Form(None),
    time_signature: str = Form("4/4"),
    subdivision: int = Form(16),
    max_fret: int = Form(24),
    sync_every_bars: int = Form(8),
    tabGenerationQuality: Literal[
        "standard", "high_accuracy", "high_accuracy_aggressive"
    ] = Form("standard"),
    onset_recovery: bool = Form(False),
):
    signature = _parse_time_signature(time_signature)
    bass_bytes = await bass.read()
    drums_bytes = await drums.read()
    other_bytes = await other.read() if other is not None else b""
    guitar_bytes = await guitar.read() if guitar is not None else b""
    if not bass_bytes:
        raise HTTPException(400, "bass file is empty")
    if not drums_bytes:
        raise HTTPException(400, "drums file is empty")

    resolved_song_id = song_id
    if resolved_song_id is None:
        resolved_song_id = await _create_song_record(
            bass.filename or "demucs-bass.wav",
            bass.content_type or "audio/wav",
            bass_bytes,
        )

    stem_tmp_dir = STEMS_DIR / "_tmp" / uuid.uuid4().hex[:12]
    stem_tmp_dir.mkdir(parents=True, exist_ok=True)
    bass_path = stem_tmp_dir / "bass.wav"
    drums_path = stem_tmp_dir / "drums.wav"
    bass_path.write_bytes(bass_bytes)
    drums_path.write_bytes(drums_bytes)
    uploaded_stems: dict[str, Path] = {
        "bass": bass_path,
        "drums": drums_path,
    }
    if other_bytes:
        other_path = stem_tmp_dir / "other.wav"
        other_path.write_bytes(other_bytes)
        uploaded_stems["other"] = other_path
    if guitar_bytes:
        guitar_path = stem_tmp_dir / "guitar.wav"
        guitar_path.write_bytes(guitar_bytes)
        uploaded_stems["guitar"] = guitar_path

    analysis_config = _get_uploaded_stems_analysis_config(tabGenerationQuality)
    analysis_stem_result: BassAnalysisStemResult
    try:
        try:
            analysis_stem_result = build_bass_analysis_stem(
                stems=uploaded_stems,
                output_dir=stem_tmp_dir / "analysis",
                analysis_config=analysis_config,
                source_audio_path=None,
            )
        except Exception as exc:
            logger.warning(
                "Uploaded stems analysis build failed; falling back to provided bass stem: %s",
                exc,
            )
            analysis_stem_result = BassAnalysisStemResult(
                path=bass_path,
                source_model="uploaded_bass_fallback",
                diagnostics={
                    "selected_model": "uploaded_bass_fallback",
                    "analysis_build_error": str(exc),
                },
            )
        result = tab_pipeline.run(
            analysis_stem_result.path,
            drums_path,
            bpm_hint=bpm,
            time_signature=signature,
            subdivision=subdivision,
            max_fret=max_fret,
            sync_every_bars=sync_every_bars,
            tab_generation_quality_mode=tabGenerationQuality,
            onset_recovery=onset_recovery,
        )
    except FingeringCollapseError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "fingering_collapse",
                "message": str(exc),
                "debug_info": exc.debug_info,
            },
        ) from exc
    except Exception as exc:
        raise HTTPException(422, f"tab generation failed: {exc}") from exc
    finally:
        shutil.rmtree(stem_tmp_dir, ignore_errors=True)

    midi_id = await _persist_midi(
        resolved_song_id,
        source_stem_key="bass",
        midi_blob=result.midi_bytes,
        engine="basic_pitch",
        provenance={
            "id": None,
            "source_type": "user",
            "display_name": bass.filename or "bass.wav",
            "version_label": _build_version_label("transient"),
            "uploaded_by_name": None,
        },
    )
    await _persist_tab(
        resolved_song_id,
        source_midi_id=midi_id,
        tab_blob=result.alphatex.encode("utf-8"),
        tab_format="alphatex",
        generator_version="v2-rhythm-grid",
    )

    return {
        "song_id": resolved_song_id,
        "alphatex": result.alphatex,
        "tempo_used": result.tempo_used,
        "bars": [
            {
                "index": bar.index,
                "start_sec": bar.start_sec,
                "end_sec": bar.end_sec,
                "beats_sec": bar.beats_sec,
            }
            for bar in result.bars
        ],
        "sync_points": [
            {
                "bar_index": point.bar_index,
                "millisecond_offset": point.millisecond_offset,
            }
            for point in result.sync_points
        ],
        "debug_info": {
            **result.debug_info,
            "analysis_stem_path": str(analysis_stem_result.path),
            "analysis_stem_diagnostics": analysis_stem_result.diagnostics,
        },
    }


@app.post("/api/analyze")
async def analyze(
    file: UploadFile,
    process_mode: ProcessMode = Form("analysis_only"),
    tabGenerationQuality: Literal[
        "standard", "high_accuracy", "high_accuracy_aggressive"
    ] = Form("standard"),
    onset_recovery: bool | None = Form(None),
    project_id: int | None = Form(None),
):
    job_id = uuid.uuid4().hex[:12]
    ext = Path(file.filename).suffix if file.filename else ".mp3"
    audio_path = UPLOAD_DIR / f"{job_id}{ext}"

    content = await file.read()
    with open(audio_path, "wb") as f:
        f.write(content)

    song_id = await _create_song_record(
        file.filename,
        file.content_type,
        content,
        project_id=project_id,
    )

    jobs[job_id] = {
        "status": "queued",
        "stage": "queued",
        "stage_history": ["queued"],
        "message": "Queued",
        "progress_pct": 0,
        "stage_progress_pct": 0,
        "process_mode": process_mode,
        "tab_generation_quality": tabGenerationQuality,
        "tab_onset_recovery": onset_recovery,
        "stems_status": "queued"
        if process_mode == "analysis_and_stems"
        else "not_requested",
        "stems_error": None,
        "midi_status": "queued"
        if process_mode == "analysis_and_stems"
        else "not_requested",
        "midi_error": None,
        "tab_status": "queued"
        if process_mode == "analysis_and_stems"
        else "not_requested",
        "tab_error": None,
        "audio_path": str(audio_path),
        "song_id": song_id,
        "error": None,
    }

    executor.submit(_run_analysis, job_id, str(audio_path), song_id)
    return {"job_id": job_id, "song_id": song_id}


@app.get("/api/status/{job_id}")
async def status(job_id: str):
    if job_id not in jobs:
        raise HTTPException(404, "Job not found")
    job = jobs[job_id]
    return {
        "status": job["status"],
        "stage": job.get("stage", job["status"]),
        "progress_pct": job.get("progress_pct", 0),
        "stage_progress_pct": job.get("stage_progress_pct", 0),
        "message": job.get("message", ""),
        "stage_history": job.get("stage_history", []),
        "stems_status": job.get("stems_status", "not_requested"),
        "stems_error": job.get("stems_error"),
        "midi_status": job.get("midi_status", "not_requested"),
        "midi_error": job.get("midi_error"),
        "tab_status": job.get("tab_status", "not_requested"),
        "tab_error": job.get("tab_error"),
        "progress": job.get("progress"),
        "error": job.get("error"),
    }


@app.get("/api/result/{job_id}")
async def result(job_id: str):
    if job_id not in jobs:
        raise HTTPException(404, "Job not found")
    job = jobs[job_id]
    if job["status"] != "complete":
        raise HTTPException(400, "Analysis not complete")

    song_id = int(job["song_id"])
    analysis = await _load_latest_analysis(song_id)
    if analysis is None:
        r: AnalysisResult = job["result"]
        return {
            "song_id": song_id,
            "key": r.key,
            "tempo": r.tempo,
            "duration": r.duration,
            "chords": [
                {"start": c.start, "end": c.end, "label": c.label} for c in r.chords
            ],
        }

    return {
        "song_id": song_id,
        **analysis,
    }


@app.get("/api/songs")
async def list_songs():
    rows = await execute(
        """
        SELECT
            s.id,
            s.title,
            s.original_filename,
            s.created_at,
            (SELECT song_key FROM analyses a WHERE a.song_id = s.id ORDER BY a.created_at DESC, a.id DESC LIMIT 1) AS song_key,
            (SELECT tempo FROM analyses a WHERE a.song_id = s.id ORDER BY a.created_at DESC, a.id DESC LIMIT 1) AS tempo,
            (SELECT duration FROM analyses a WHERE a.song_id = s.id ORDER BY a.created_at DESC, a.id DESC LIMIT 1) AS duration
        FROM songs s
        ORDER BY s.created_at DESC, s.id DESC
        """
    )

    songs = []
    for row in rows.rows:
        songs.append(
            {
                "id": row[0],
                "title": row[1],
                "original_filename": row[2],
                "created_at": row[3],
                "key": row[4],
                "tempo": row[5],
                "duration": row[6],
            }
        )
    return {"songs": songs}


@app.get("/api/bands")
async def list_bands():
    rows = await execute(
        """
        SELECT
            b.id,
            b.name,
            b.owner_user_id,
            b.created_at,
            (
                SELECT COUNT(*)
                FROM projects p
                WHERE p.band_id = b.id
            ) AS project_count
        FROM bands b
        ORDER BY b.created_at DESC, b.id DESC
        """
    )
    bands = [
        {
            "id": int(row[0]),
            "name": row[1],
            "owner_user_id": int(row[2]),
            "created_at": row[3],
            "project_count": int(row[4]),
        }
        for row in rows.rows
    ]
    return {"bands": bands}


@app.get("/api/bands/{band_id}/projects")
async def list_band_projects(band_id: int):
    rows = await execute(
        """
        SELECT
            p.id,
            p.band_id,
            p.name,
            p.description,
            p.created_at,
            (
                SELECT COUNT(*)
                FROM songs s
                WHERE s.project_id = p.id
            ) AS song_count
        FROM projects p
        WHERE p.band_id = ?
        ORDER BY p.created_at DESC, p.id DESC
        """,
        [band_id],
    )
    projects = [
        {
            "id": int(row[0]),
            "band_id": int(row[1]),
            "name": row[2],
            "description": row[3],
            "created_at": row[4],
            "song_count": int(row[5]),
        }
        for row in rows.rows
    ]
    return {"projects": projects}


@app.get("/api/projects/{project_id}/songs")
async def list_project_songs(project_id: int):
    rows = await execute(
        """
        SELECT
            s.id,
            s.project_id,
            s.title,
            s.original_filename,
            s.created_at,
            (SELECT song_key FROM analyses a WHERE a.song_id = s.id ORDER BY a.created_at DESC, a.id DESC LIMIT 1) AS song_key,
            (SELECT tempo FROM analyses a WHERE a.song_id = s.id ORDER BY a.created_at DESC, a.id DESC LIMIT 1) AS tempo,
            (SELECT duration FROM analyses a WHERE a.song_id = s.id ORDER BY a.created_at DESC, a.id DESC LIMIT 1) AS duration
        FROM songs s
        WHERE s.project_id = ?
        ORDER BY s.created_at DESC, s.id DESC
        """,
        [project_id],
    )
    songs = [
        {
            "id": int(row[0]),
            "project_id": int(row[1]),
            "title": row[2],
            "original_filename": row[3],
            "created_at": row[4],
            "key": row[5],
            "tempo": row[6],
            "duration": row[7],
        }
        for row in rows.rows
    ]
    return {"songs": songs}


@app.get("/api/songs/{song_id}")
async def get_song(song_id: int):
    song_rs = await execute(
        """
        SELECT id, title, original_filename, mime_type, created_at
        FROM songs
        WHERE id = ?
        """,
        [song_id],
    )
    if not song_rs.rows:
        raise HTTPException(404, "Song not found")

    song_row = song_rs.rows[0]
    analysis = await _load_latest_analysis(song_id)
    notes = await _load_song_notes(song_id)

    prefs_rs = await execute(
        """
        SELECT speed_percent, volume, loop_start_index, loop_end_index
        FROM playback_prefs
        WHERE song_id = ?
        """,
        [song_id],
    )
    prefs = {
        "speed_percent": 100,
        "volume": 1.0,
        "loop_start_index": None,
        "loop_end_index": None,
    }
    if prefs_rs.rows:
        row = prefs_rs.rows[0]
        prefs = {
            "speed_percent": row[0],
            "volume": row[1],
            "loop_start_index": row[2],
            "loop_end_index": row[3],
        }

    return {
        "song": {
            "id": song_row[0],
            "title": song_row[1],
            "original_filename": song_row[2],
            "mime_type": song_row[3],
            "created_at": song_row[4],
        },
        "analysis": analysis,
        "notes": notes,
        "playback_prefs": prefs,
    }


@app.get("/api/songs/{song_id}/stems")
async def get_song_stems(song_id: int):
    return {"stems": await _load_song_stems(song_id)}


@app.post("/api/songs/{song_id}/stems/upload")
async def upload_song_stem(
    song_id: int, stem_key: str = Form(...), file: UploadFile = File(...)
):
    song = await _load_song_row(song_id)
    if song is None:
        raise HTTPException(404, "Song not found")

    content = await file.read()
    if not content:
        raise HTTPException(400, "Stem file is empty")

    user = await get_default_user()
    safe_name = Path(file.filename or f"{stem_key}.wav").name or f"{stem_key}.wav"
    upload_dir = STEMS_DIR / str(song_id) / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    stored_path = upload_dir / f"{uuid.uuid4().hex[:8]}-{safe_name}"
    stored_path.write_bytes(content)

    await _replace_song_stem(
        song_id,
        stem_key=stem_key,
        relative_path=str(stored_path),
        mime_type=file.content_type,
        duration=None,
        source_type="user",
        display_name=safe_name,
        version_label=_build_version_label("upload"),
        uploaded_by_name=str(user["display_name"]),
    )
    return {"stems": await _load_song_stems(song_id)}


@app.post("/api/songs/{song_id}/stems/regenerate")
async def regenerate_song_stems(song_id: int):
    song = await _load_song_row(song_id)
    if song is None:
        raise HTTPException(404, "Song not found")

    audio_path = _write_song_audio_tempfile(
        song_id,
        song["original_filename"],
        song["audio_blob"],
    )
    try:
        stems = split_to_stems(
            audio_path=str(audio_path),
            output_dir=STEMS_DIR / str(song_id),
        )
        await _persist_stems(song_id, stems)
    finally:
        shutil.rmtree(audio_path.parent, ignore_errors=True)

    return {"stems": await _load_song_stems(song_id)}


@app.get("/api/songs/{song_id}/stems/{stem_key}/download")
async def download_song_stem(song_id: int, stem_key: str):
    rs = await execute(
        """
        SELECT s.title, ss.relative_path, ss.mime_type
        FROM song_stems ss
        JOIN songs s ON s.id = ss.song_id
        WHERE ss.song_id = ? AND ss.stem_key = ?
        LIMIT 1
        """,
        [song_id, stem_key],
    )
    if not rs.rows:
        raise HTTPException(404, "Stem not found")

    song_title, relative_path, mime_type = rs.rows[0][0], rs.rows[0][1], rs.rows[0][2]
    path = Path(relative_path)
    if not path.exists():
        raise HTTPException(404, "Stem file missing")

    safe_title = (
        re.sub(r"[^a-zA-Z0-9._-]+", "_", song_title or f"song-{song_id}").strip("._-")
        or f"song-{song_id}"
    )
    extension = path.suffix or ".wav"
    filename = f"{safe_title}-{stem_key}{extension}"
    stem_bytes = path.read_bytes()
    return Response(
        content=stem_bytes,
        media_type=mime_type or "audio/mpeg",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(stem_bytes)),
        },
    )


@app.get("/api/songs/{song_id}/stems/download")
async def download_song_stems_zip(song_id: int):
    song_rs = await execute("SELECT title FROM songs WHERE id = ?", [song_id])
    if not song_rs.rows:
        raise HTTPException(404, "Song not found")
    song_title = song_rs.rows[0][0]

    stems_rs = await execute(
        """
        SELECT stem_key, relative_path, mime_type, duration
        FROM song_stems
        WHERE song_id = ?
        ORDER BY stem_key ASC
        """,
        [song_id],
    )
    stems = [
        StemResult(
            stem_key=row[0],
            relative_path=row[1],
            mime_type=row[2] or "audio/mpeg",
            duration=row[3],
        )
        for row in stems_rs.rows
    ]
    if not stems:
        raise HTTPException(404, "No stems found")

    archive_bytes, archive_name = build_stems_zip(song_title=song_title, stems=stems)
    return Response(
        content=archive_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{archive_name}"',
            "Content-Length": str(len(archive_bytes)),
        },
    )


@app.get("/api/songs/{song_id}/tabs")
async def get_song_tabs(song_id: int):
    return {"tab": await _load_song_tab_meta(song_id)}


@app.post("/api/songs/{song_id}/tabs/regenerate")
async def regenerate_song_tabs(song_id: int, payload: SongTabRegenerateRequest):
    song = await _load_song_row(song_id)
    if song is None:
        raise HTTPException(404, "Song not found")
    tab_meta = await _regenerate_song_tabs(song_id, payload.source_stem_key)
    return {"tab": tab_meta}


@app.get("/api/songs/{song_id}/midi/file")
async def get_song_midi_file(song_id: int):
    rs = await execute(
        """
        SELECT midi_blob
        FROM song_midis
        WHERE song_id = ?
        ORDER BY updated_at DESC, id DESC
        LIMIT 1
        """,
        [song_id],
    )
    if not rs.rows:
        raise HTTPException(404, "MIDI not found")
    return Response(content=rs.rows[0][0], media_type="audio/midi")


@app.get("/api/songs/{song_id}/tabs/file")
async def get_song_tabs_file(song_id: int):
    rs = await execute(
        """
        SELECT tab_blob, tab_format
        FROM song_tabs
        WHERE song_id = ?
        ORDER BY updated_at DESC, id DESC
        LIMIT 1
        """,
        [song_id],
    )
    if not rs.rows:
        raise HTTPException(404, "Tabs not found")
    tab_blob, tab_format = rs.rows[0][0], (rs.rows[0][1] or "").lower()
    media_type = (
        "text/plain; charset=utf-8"
        if tab_format == "alphatex"
        else "application/octet-stream"
    )
    return Response(content=tab_blob, media_type=media_type)


@app.get("/api/songs/{song_id}/tabs/download")
async def download_song_tabs_file(song_id: int):
    rs = await execute(
        """
        SELECT s.title, t.tab_blob, t.tab_format
        FROM song_tabs t
        JOIN songs s ON s.id = t.song_id
        WHERE t.song_id = ?
        ORDER BY t.updated_at DESC, t.id DESC
        LIMIT 1
        """,
        [song_id],
    )
    if not rs.rows:
        raise HTTPException(404, "Tabs not found")

    title, tab_blob, tab_format = (
        rs.rows[0][0],
        rs.rows[0][1],
        (rs.rows[0][2] or "gp5").lower(),
    )
    safe_title = (
        re.sub(r"[^a-zA-Z0-9._-]+", "_", title or f"song-{song_id}").strip("._-")
        or f"song-{song_id}"
    )
    extension = (
        "alphatex"
        if tab_format == "alphatex"
        else ("gp5" if tab_format not in {"gp3", "gp4", "gp5", "gpx"} else tab_format)
    )
    filename = f"{safe_title}.{extension}"

    return Response(
        content=tab_blob,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(tab_blob)),
        },
    )


@app.get("/api/audio/{audio_id}")
async def audio(audio_id: str):
    # Backward compatible path: if this is an in-memory job id, serve uploaded file path.
    if audio_id in jobs:
        audio_path = jobs[audio_id]["audio_path"]
        return FileResponse(audio_path, media_type="audio/mpeg")

    try:
        song_id = int(audio_id)
    except ValueError as exc:
        raise HTTPException(404, "Song not found") from exc

    rs = await execute(
        "SELECT audio_blob, mime_type FROM songs WHERE id = ?",
        [song_id],
    )
    if not rs.rows:
        raise HTTPException(404, "Song not found")

    blob, mime_type = rs.rows[0][0], rs.rows[0][1] or "audio/mpeg"
    return Response(content=blob, media_type=mime_type)


@app.get("/api/audio/{song_id}/stems/{stem_key}")
async def stem_audio(song_id: int, stem_key: str):
    rs = await execute(
        """
        SELECT relative_path, mime_type
        FROM song_stems
        WHERE song_id = ? AND stem_key = ?
        LIMIT 1
        """,
        [song_id, stem_key],
    )
    if not rs.rows:
        raise HTTPException(404, "Stem not found")

    path = Path(rs.rows[0][0])
    if not path.exists():
        raise HTTPException(404, "Stem file missing")
    return FileResponse(path, media_type=rs.rows[0][1] or "audio/mpeg")


@app.post("/api/songs/{song_id}/notes")
async def create_note(song_id: int, payload: NoteCreate):
    if payload.type == "time" and payload.timestamp_sec is None:
        raise HTTPException(400, "timestamp_sec is required for time notes")
    if payload.type == "chord" and payload.chord_index is None:
        raise HTTPException(400, "chord_index is required for chord notes")
    author = await get_default_user()
    author_name = str(author["display_name"])
    author_avatar = _build_author_avatar(author_name)

    inserted = await execute(
        """
        INSERT INTO notes (
            song_id,
            author_user_id,
            author_name,
            author_avatar,
            type,
            timestamp_sec,
            chord_index,
            text,
            toast_duration_sec,
            resolved
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
        RETURNING id
        """,
        [
            song_id,
            author["id"],
            author_name,
            author_avatar,
            payload.type,
            payload.timestamp_sec,
            payload.chord_index,
            payload.text,
            payload.toast_duration_sec,
        ],
    )
    note_id = int(inserted.rows[0][0])
    return {
        "id": note_id,
        "song_id": song_id,
        "author_user_id": author["id"],
        "author_name": author_name,
        "author_avatar": author_avatar,
        "resolved": False,
        **payload.model_dump(),
    }


@app.patch("/api/notes/{note_id}")
async def update_note(note_id: int, payload: NoteUpdate):
    row_rs = await execute(
        "SELECT text, toast_duration_sec FROM notes WHERE id = ?", [note_id]
    )
    if not row_rs.rows:
        raise HTTPException(404, "Note not found")

    current = row_rs.rows[0]
    text = payload.text if payload.text is not None else current[0]
    toast_duration_sec = (
        payload.toast_duration_sec
        if payload.toast_duration_sec is not None
        else current[1]
    )

    await execute(
        """
        UPDATE notes
        SET text = ?, toast_duration_sec = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        [text, toast_duration_sec, note_id],
    )
    return {"id": note_id, "text": text, "toast_duration_sec": toast_duration_sec}


@app.patch("/api/notes/{note_id}/resolve")
async def resolve_note(note_id: int, payload: NoteResolveUpdate):
    note_rs = await execute("SELECT id, resolved FROM notes WHERE id = ?", [note_id])
    if not note_rs.rows:
        raise HTTPException(404, "Note not found")
    if bool(note_rs.rows[0][1]) == payload.resolved:
        return {"id": note_id, "resolved": payload.resolved}

    await execute(
        """
        UPDATE notes
        SET resolved = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        [1 if payload.resolved else 0, note_id],
    )
    return {"id": note_id, "resolved": payload.resolved}


@app.delete("/api/notes/{note_id}")
async def delete_note(note_id: int):
    await execute("DELETE FROM notes WHERE id = ?", [note_id])
    return {"status": "ok"}


@app.put("/api/songs/{song_id}/playback-prefs")
async def update_playback_prefs(song_id: int, payload: PlaybackPrefsUpdate):
    await execute(
        """
        INSERT INTO playback_prefs (song_id, speed_percent, volume, loop_start_index, loop_end_index)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(song_id) DO UPDATE SET
            speed_percent = excluded.speed_percent,
            volume = excluded.volume,
            loop_start_index = excluded.loop_start_index,
            loop_end_index = excluded.loop_end_index,
            updated_at = CURRENT_TIMESTAMP
        """,
        [
            song_id,
            payload.speed_percent,
            payload.volume,
            payload.loop_start_index,
            payload.loop_end_index,
        ],
    )
    return payload.model_dump()


# Serve frontend static files in production
if os.path.exists("static"):
    app.mount("/", StaticFiles(directory="static", html=True), name="static")
