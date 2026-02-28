# DeChord Web App - Design Document

**Date:** 2026-02-28
**Status:** Approved

## Overview

Transform the existing DeChord Python/PyQt5 desktop application into a browser-based web app. The web app provides a "Guitar Pro"-style scrolling chord timeline for bass players, with fretboard visualization showing which notes fit the current chord.

## Problem Statement

The current DeChord app shows chords in a real-time carousel (5 chords at a time). This is "momentary" — the user can't see the full chord progression or look ahead. Bass players need to see the full song structure, like opening guitar tabs in Guitar Pro, to practice effectively.

## Goals

1. Drag-and-drop audio file analysis (MP3, WAV, M4A, AAC)
2. Guitar Pro-style chord timeline that wraps horizontally and scrolls vertically
3. Time-proportional chord widths (longer chords = wider blocks)
4. Bass fretboard visualization showing notes fitting the current chord
5. Full audio playback with seeking
6. Loop between two chord points (click to set start, click to set end)
7. Auto-scroll to keep current position visible
8. Key and tempo display

## Architecture

### Approach: FastAPI + React SPA Monolith

Single repository with a Python backend (FastAPI + madmom) and a React/TypeScript frontend. In production, FastAPI serves the built React assets from a single process/container.

```
Browser (React SPA)
    │
    │ REST API
    ▼
FastAPI Backend
    │
    ├── madmom chord detection (CNN)
    ├── madmom key detection (CNN)
    ├── madmom tempo detection (RNN)
    └── file-based cache (MD5 hashes)
```

### Data Flow

1. User drags audio file onto the web app
2. Frontend uploads file to FastAPI (`POST /api/analyze`)
3. Backend returns a `job_id`, starts processing in background thread
4. Frontend polls `GET /api/status/{job_id}` until complete
5. Frontend fetches results (`GET /api/result/{job_id}`) — JSON with chords, key, tempo
6. Audio plays via `<audio>` element (served from `GET /api/audio/{job_id}`)
7. Frontend syncs chord timeline highlighting with audio playback position via `requestAnimationFrame`

## API Contract

```
POST /api/analyze
  Body: multipart/form-data (audio file)
  Response: { "job_id": "abc123" }

GET /api/status/{job_id}
  Response: {
    "status": "processing" | "complete" | "error",
    "progress": "Detecting chords..." (optional)
  }

GET /api/result/{job_id}
  Response: {
    "key": "C major",
    "tempo": 120,
    "chords": [
      { "start": 0.0, "end": 2.34, "label": "Am" },
      { "start": 2.34, "end": 4.68, "label": "C" },
      ...
    ],
    "duration": 201.5
  }

GET /api/audio/{job_id}
  Response: audio file stream
```

## UI Layout

```
┌─────────────────────────────────────────────────────────┐
│  Header: [DeChord]        [Key: C major | 120 BPM] [🌙] │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Chord Timeline (scrollable, wraps lines like text)      │
│  |Am ════════|C ════|F ═══════════|G ════|               │
│  |Am ════════|Em ═══|F ═══════════|C ════|               │
│  |Dm ════════════════|G ══════════════════|              │
│  |C  ▶═══════|F ════|Am ══════════|G ════|              │
│                                                          │
├─────────────────────────────────────────────────────────┤
│  Bass Fretboard (sticky bottom)                          │
│  4-string standard tuning (E-A-D-G), 12 frets           │
│  Highlighted dots = notes in current chord               │
├─────────────────────────────────────────────────────────┤
│  Transport: [◀◀][▶/⏸][▶▶]  0:42 ══●══ 3:21            │
│  [Loop: Am → G]  [Vol ══●══]                             │
└─────────────────────────────────────────────────────────┘
```

### Key UI Behaviors

- **Chord timeline**: Full-width, wraps at container edge, scrolls vertically
- **Time-proportional**: Chord block width proportional to duration
- **Playhead**: Visual marker on current position, auto-scrolls view
- **Loop**: Click a chord to set loop start, click another for loop end
- **Fretboard**: Sticky at bottom, updates in real-time with current chord
- **Dark/light theme**: Toggle in header

## Fretboard Logic

4-string bass, standard tuning (E-A-D-G), 12 frets.

Given a chord label, compute constituent notes and map to fretboard positions. Supports chord types output by madmom: major, minor, 7th, maj7, min7, dim, aug.

Example: "Am" = notes A, C, E → highlight all positions on the 4 strings where these notes occur within 12 frets.

## Tech Stack

### Backend
- **Python 3.13+** with **uv** for package management
- **FastAPI** — async API framework
- **madmom** — CNN/RNN-based chord, key, tempo detection
- Background processing via thread pool executor
- File-based cache (MD5 hash of file content)

### Frontend
- **Bun** — runtime and package manager
- **Vite** — build tool
- **React 19** — UI framework (TypeScript)
- **Tailwind CSS v4** — styling
- **HTML `<audio>` element** — playback
- **`requestAnimationFrame`** — chord sync

### Project Structure

```
DeChord/
├── backend/
│   ├── pyproject.toml
│   ├── main.py          (FastAPI app)
│   ├── analysis.py      (madmom processing)
│   └── cache/
├── frontend/
│   ├── package.json
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   ├── DropZone.tsx
│   │   │   ├── ChordTimeline.tsx
│   │   │   ├── Fretboard.tsx
│   │   │   ├── TransportBar.tsx
│   │   │   └── Header.tsx
│   │   ├── hooks/
│   │   │   ├── useAudioPlayer.ts
│   │   │   └── useChordSync.ts
│   │   └── lib/
│   │       ├── api.ts
│   │       └── music.ts
│   └── tailwind.config.ts
├── Dockerfile
├── Makefile
└── docs/plans/
```

### Dev Workflow

```bash
# Backend
cd backend && uv run fastapi dev main.py  # port 8000

# Frontend
cd frontend && bun dev                     # port 5173, proxies to 8000

# Or together
make dev
```

## Decisions Log

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Architecture | FastAPI + React monolith | Simplest for personal tool, single container deploy |
| Chord detection | Reuse madmom (Python) | CNN models produce better results than JS alternatives |
| Bass config | 4-string E-A-D-G, 12 frets | Standard, clean, covers most playing |
| Timeline style | Time-proportional widths | Most intuitive for reading timing |
| Loop UX | Click chord blocks | Musical — loop by section, not arbitrary time |
| Package mgmt | uv (Python), Bun (JS) | Modern, fast tooling |
| Scroll direction | Vertical (lines wrap) | Guitar Pro style, see full progression |
