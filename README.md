# DeChord

DeChord is a web application for analyzing uploaded audio and exploring the results in a browser. The project combines a FastAPI backend with a React frontend for chord and key detection, song library management, stem-aware playback, timestamped notes, and generated bass-tab artifacts.

## Stack

- Frontend: React 19, TypeScript, Vite, Tailwind CSS v4
- Backend: FastAPI, Python 3.13+
- Analysis: madmom-based chord, key, and tempo detection
- Storage: LibSQL for local song and analysis data
- Tab pipeline: Demucs-assisted stem processing, MIDI transcription, and AlphaTex export

## Web App Features

- Upload audio files for browser-based analysis
- Detect musical key, tempo, and timed chord changes
- Keep a local song library with persisted analysis results
- Play songs in the browser with saved playback preferences
- Add timestamp notes and chord-linked notes
- Switch between chord-only analysis and analysis with stem separation
- Use stem-aware playback when separated stems are available
- Generate bass transcription artifacts including MIDI and AlphaTex tab output

## Repository Layout

- `frontend/`: React web client
- `backend/`: FastAPI API and analysis pipeline
- `docs/plans/`: implementation plans and execution history
- `designs.gpt54/`: retained design variant workspace
- `designs.opus46/`: retained design variant workspace

## Prerequisites

- Python 3.13+
- Node.js 18+ or newer
- `uv`
- `bun`
- `tmux`
- `portless`
- `ffmpeg`

## Start Locally

Use the root `Makefile` for the standard local workflow:

```bash
make install
make up
make status
```

Open:

- Frontend: [http://dechord.localhost:1355](http://dechord.localhost:1355)
- Backend health: [http://api.dechord.localhost:1355/api/health](http://api.dechord.localhost:1355/api/health)

Stop services with:

```bash
make down
```

## Direct Development Commands

### Backend

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
bun install
bun run dev
```

## tmux And Portless Controls

```bash
make backend-up
make backend-attach
make backend-status
make backend-logs
make backend-down

make frontend-up
make frontend-attach
make frontend-status
make frontend-logs
make frontend-down

make up
make down
make status
make logs
make portless-routes
make portless-proxy-up
make portless-proxy-down
```

## Test Commands

```bash
cd backend && uv run pytest tests/ -v
cd frontend && bun run test
cd frontend && bun run build
```

## Upload Workflow

1. Upload an audio file from the browser.
2. Choose one processing mode:
   - `Analyze chords only`
   - `Analyze + split stems`
3. Track job progress through staged status updates.
4. Browse saved song analysis, playback preferences, notes, stems, and generated artifacts.
5. If bass and drums stems are available, the tab viewer can load generated AlphaTex tabs synced to playback.

## Web API Surface

Core endpoints currently exposed by `backend/app/main.py`:

- `GET /api/health`
- `POST /api/analyze`
- `GET /api/status/{job_id}`
- `GET /api/result/{job_id}`
- `GET /api/songs`
- `GET /api/songs/{song_id}`
- `GET /api/songs/{song_id}/stems`
- `GET /api/songs/{song_id}/tabs`
- `GET /api/songs/{song_id}/midi/file`
- `GET /api/songs/{song_id}/tabs/file`
- `GET /api/songs/{song_id}/tabs/download`
- `GET /api/audio/{audio_id}`
- `GET /api/audio/{song_id}/stems/{stem_key}`
- `POST /api/songs/{song_id}/notes`
- `DELETE /api/notes/{note_id}`
- `PUT /api/songs/{song_id}/playback-prefs`
- `POST /api/tab/from-demucs-stems`

## Stem Separation Configuration

The backend stem splitter loads `backend/.env` at runtime. Playback and downloads use the raw separated stems, while the tab pipeline builds a dedicated `bass_analysis.wav` artifact for transcription-focused processing.

| Variable | Default | Description |
| --- | --- | --- |
| `DECHORD_DEMUCS_MODEL` | `htdemucs_ft` | Primary Demucs model name. |
| `DECHORD_DEMUCS_FALLBACK_MODEL` | `htdemucs` | Fallback Demucs model when the primary model is unavailable. |
| `DECHORD_STEM_ENGINE` | `demucs` | Stem engine: `demucs` or `fallback`. |
| `DECHORD_STEM_FALLBACK_ON_ERROR` | `0` | If `1`, fallback splitter runs when the primary splitter fails. |
| `DECHORD_STEM_DEVICE` | `auto` | Compute device: `auto`, `cpu`, `mps`, `cuda`. |
| `DECHORD_STEM_SEGMENT` | `7.8` | Segment length in seconds. |
| `DECHORD_STEM_OVERLAP` | `0.25` | Segment overlap ratio. |
| `DECHORD_STEM_SHIFTS` | `0` | Number of random shifts. |
| `DECHORD_STEM_INPUT_GAIN_DB` | `0.0` | Gain applied before separation. |
| `DECHORD_STEM_OUTPUT_GAIN_DB` | `0.0` | Gain applied before writing output stems. |
| `DECHORD_STEM_JOBS` | unset | Optional CPU worker count. |
| `DECHORD_STEM_ANALYSIS_ENABLE` | `1` | Build a separate analysis-only bass stem for tab and MIDI generation. |
| `DECHORD_STEM_ANALYSIS_HIGHPASS_HZ` | `35` | Analysis stem high-pass filter cutoff. |
| `DECHORD_STEM_ANALYSIS_LOWPASS_HZ` | `300` | Analysis stem low-pass filter cutoff. |
| `DECHORD_STEM_ANALYSIS_SAMPLE_RATE` | `22050` | Analysis stem sample rate. |
| `DECHORD_STEM_ANALYSIS_CANDIDATE_MODELS` | primary model | Candidate Demucs models for analysis-only ensemble selection. |
| `DECHORD_STEM_ANALYSIS_ENSEMBLE` | `0` | Enable multi-candidate analysis-stem scoring. |
| `DECHORD_STEM_ANALYSIS_OTHER_SUBTRACT_WEIGHT` | `0.30` | Bleed subtraction weight for `other`. |
| `DECHORD_STEM_ANALYSIS_GUITAR_SUBTRACT_WEIGHT` | `0.55` | Bleed subtraction weight for `guitar`. |
| `DECHORD_STEM_ANALYSIS_NOISE_GATE_DB` | `-40` | Post-refinement noise gate threshold in dBFS. |
| `DECHORD_STEM_ANALYSIS_SELECTION_MODE` | `transcription` | Candidate selection mode for analysis-stem scoring. |
| `DECHORD_PIPELINE_PRESET` | unset | Optional operating preset. |

Example `backend/.env`:

```bash
DECHORD_DEMUCS_MODEL=htdemucs_ft
DECHORD_DEMUCS_FALLBACK_MODEL=htdemucs
DECHORD_STEM_DEVICE=auto
DECHORD_STEM_SEGMENT=7.8
DECHORD_STEM_OVERLAP=0.25
DECHORD_STEM_SHIFTS=0
DECHORD_STEM_INPUT_GAIN_DB=0.0
DECHORD_STEM_OUTPUT_GAIN_DB=0.0
DECHORD_STEM_ANALYSIS_ENABLE=1
DECHORD_STEM_ANALYSIS_ENSEMBLE=1
DECHORD_STEM_ANALYSIS_CANDIDATE_MODELS=htdemucs_ft,htdemucs_6s
DECHORD_STEM_ANALYSIS_OTHER_SUBTRACT_WEIGHT=0.30
DECHORD_STEM_ANALYSIS_GUITAR_SUBTRACT_WEIGHT=0.55
DECHORD_STEM_ANALYSIS_NOISE_GATE_DB=-40
DECHORD_STEM_ANALYSIS_HIGHPASS_HZ=35
DECHORD_STEM_ANALYSIS_LOWPASS_HZ=300
DECHORD_STEM_ANALYSIS_SELECTION_MODE=transcription
```

## Pipeline Presets

`DECHORD_PIPELINE_PRESET` currently supports:

- `stable_baseline`
- `balanced_benchmark`
- `distorted_bass_recall`

Current default preset implementation lives in `backend/app/pipeline_presets.py` and resolves to `balanced_benchmark` when a preset is requested but unspecified.

Preset intent:

- `stable_baseline`: bounded baseline with refinement enabled and recall-expansion features off
- `balanced_benchmark`: aggressive second-pass recovery without enabling dense-note generation by default
- `distorted_bass_recall`: recall-oriented profile for dense distorted bass passages

Recommended benchmark guardrails used by the preset layer:

- `DECHORD_BENCH_RESOURCE_MONITOR=1`
- `DECHORD_BENCH_MAX_MEMORY_MB=12000`
- `DECHORD_BENCH_MAX_CHILD_PROCS=4`

## Backend Tab Generation Pipeline

The tab-generation flow is orchestrated in `backend/app/main.py` and split across three reusable layers:

- `app.stems`: raw stem separation and transcription-focused `bass_analysis.wav` preparation
- `app.services.tab_pipeline`: rhythm extraction, transcription cleanup, quantization, fingering, and AlphaTex export
- `app.db`: persistence for stems, MIDI artifacts, tabs, and song metadata

There are two entrypoints into the pipeline:

| Entrypoint | Use case | Output |
| --- | --- | --- |
| `POST /api/analyze` | standard upload flow | async job with persisted artifacts |
| `POST /api/tab/from-demucs-stems` | direct stems-to-tab flow | immediate JSON response plus persisted MIDI and tabs |

### Pipeline Stages

1. Source audio is analyzed for key, chords, and tempo.
2. If stems are requested, `split_to_stems(...)` generates raw stems.
3. `build_bass_analysis_stem(...)` produces a refined `bass_analysis.wav`.
4. `TabPipeline.run(...)` combines the analysis bass stem and drums stem.
5. `app.services.rhythm_grid` builds a drum-derived bar grid.
6. `app.services.bass_transcriber` and `app.midi` generate MIDI and raw note events.
7. Cleanup, onset recovery, quantization, and fingering are applied.
8. `app.services.alphatex_exporter` emits AlphaTex plus sync points.
9. MIDI and tab artifacts are persisted and exposed through song endpoints.

### Active TabPipeline Contract

```python
TabPipeline.run(
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
) -> TabPipelineResult
```

`TabPipelineResult` contains:

- `alphatex`
- `tempo_used`
- `bars`
- `sync_points`
- `midi_bytes`
- `debug_info`
- `fingered_notes`

### Persisted Artifacts

| Stage | Artifact | Where |
| --- | --- | --- |
| Upload | source mix | `songs.audio_blob` |
| Stem split | `bass.wav`, `drums.wav`, and related stems | filesystem + `song_stems` |
| Analysis refinement | `bass_analysis.wav` | filesystem |
| Transcription | MIDI bytes | `song_midis` |
| Tab export | AlphaTex text | `song_tabs` |

### Runtime Controls That Affect Tab Output

- `tabGenerationQuality`
- `onset_recovery`
- `bpm` / `bpm_hint`
- `time_signature`
- `subdivision`
- `max_fret`
- `sync_every_bars`

Pitch and note generation behavior is additionally controlled through the `DECHORD_PITCH_*`, `DECHORD_NOTE_*`, `DECHORD_RAW_NOTE_*`, `DECHORD_DENSE_*`, and `DECHORD_ONSET_*` environment variables parsed by `backend/app/midi.py`.

## Development Notes

- Progress and task execution are tracked in `docs/plans/`.
- Project instructions for agents live in `AGENTS.md`.
- `CLAUDE.md` links to `AGENTS.md` to keep instructions in one place.

## License

This project is licensed under the MIT License. See `LICENSE`.
