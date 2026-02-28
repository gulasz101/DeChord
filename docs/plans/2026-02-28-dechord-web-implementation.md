# DeChord Web App Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a browser-based chord analysis app with Guitar Pro-style timeline, bass fretboard visualization, and audio looping.

**Architecture:** FastAPI backend wrapping existing madmom CNN/RNN models, React/TypeScript SPA frontend with Tailwind CSS. Single repo monolith.

**Tech Stack:** Python 3.13+ / uv / FastAPI / madmom | Bun / Vite / React 19 / TypeScript / Tailwind v4

**Design doc:** `docs/plans/2026-02-28-dechord-web-design.md`

---

## Task 1: Backend Project Setup

- [x] Step 1: Create backend directory and pyproject.toml
- [x] Step 2: Install dependencies
- [x] Step 3: Create FastAPI skeleton
- [x] Step 4: Verify server starts
- [x] Step 5: Commit

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`

**Step 1: Create backend directory and pyproject.toml**

```toml
# backend/pyproject.toml
[project]
name = "dechord-api"
version = "0.1.0"
description = "DeChord web API - chord/key/tempo detection from audio"
requires-python = ">=3.13"
dependencies = [
    "fastapi[standard]",
    "python-multipart",
    "madmom",
]

[tool.uv.sources]
madmom = { git = "https://github.com/CPJKU/madmom" }
```

**Step 2: Install dependencies**

```bash
cd backend && uv sync
```

Expected: Dependencies installed, `uv.lock` created.

**Step 3: Create FastAPI skeleton**

```python
# backend/app/__init__.py
# (empty)
```

```python
# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="DeChord API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
```

**Step 4: Verify server starts**

```bash
cd backend && uv run fastapi dev app/main.py --port 8000
```

Then in another terminal:
```bash
curl http://localhost:8000/api/health
```

Expected: `{"status":"ok"}`

**Step 5: Commit**

```bash
git add backend/
git commit -m "Task 1: Backend project setup with FastAPI skeleton

refs: docs/plans/2026-02-28-dechord-web-implementation.md"
```

---

## Task 2: Backend Analysis Module

- [x] Step 1: Create analysis module with chord/key/tempo detection
- [x] Step 2: Create tests for cache logic
- [x] Step 3: Run tests
- [x] Step 4: Commit

**Files:**
- Create: `backend/app/analysis.py`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/test_analysis.py`

**Step 1: Create analysis module**

Port the existing madmom processing from `chords.py`, `key.py`, `tempo.py` into a single module. Remove PyQt5 dependencies, use plain functions.

```python
# backend/app/analysis.py
import hashlib
import os
from pathlib import Path
from dataclasses import dataclass

CACHE_DIR = Path("cache")


@dataclass
class Chord:
    start: float
    end: float
    label: str


@dataclass
class AnalysisResult:
    key: str
    tempo: int
    chords: list[Chord]
    duration: float


def _cache_path(audio_path: str, category: str) -> Path:
    hash_hex = hashlib.md5(audio_path.encode()).hexdigest()
    return CACHE_DIR / category / f"{hash_hex}.txt"


def detect_chords(audio_path: str) -> list[Chord]:
    cache_file = _cache_path(audio_path, "chord")
    cache_file.parent.mkdir(parents=True, exist_ok=True)

    if cache_file.exists():
        chords = []
        for line in cache_file.read_text().strip().split("\n"):
            if not line:
                continue
            start, end, label = line.split(",", 2)
            chords.append(Chord(float(start), float(end), label))
        return chords

    import madmom

    feat_processor = madmom.features.chords.CNNChordFeatureProcessor()
    recog_processor = madmom.features.chords.CRFChordRecognitionProcessor()
    feats = feat_processor(audio_path)
    raw_chords = recog_processor(feats)

    chords = []
    lines = []
    for start_time, end_time, chord_label in raw_chords:
        if ":maj" in chord_label:
            chord_label = chord_label.replace(":maj", "")
        elif ":min" in chord_label:
            chord_label = chord_label.replace(":min", "m")
        chords.append(Chord(start_time, end_time, chord_label))
        lines.append(f"{start_time},{end_time},{chord_label}")

    cache_file.write_text("\n".join(lines) + "\n")
    return chords


def detect_key(audio_path: str) -> str:
    cache_file = _cache_path(audio_path, "key")
    cache_file.parent.mkdir(parents=True, exist_ok=True)

    if cache_file.exists():
        return cache_file.read_text().strip()

    try:
        import madmom

        key_processor = madmom.features.key.CNNKeyRecognitionProcessor()
        key_prediction = key_processor(audio_path)
        key = madmom.features.key.key_prediction_to_label(key_prediction)
        cache_file.write_text(key)
        return key
    except Exception:
        return "Error"


def _adjust_tempo(tempo: float) -> float:
    while tempo < 70:
        tempo *= 2
    while tempo > 190:
        tempo /= 2
    return tempo


def detect_tempo(audio_path: str) -> int:
    cache_file = _cache_path(audio_path, "tempo")
    cache_file.parent.mkdir(parents=True, exist_ok=True)

    if cache_file.exists():
        return int(cache_file.read_text().strip())

    from madmom.features.beats import RNNBeatProcessor
    from madmom.features.tempo import TempoEstimationProcessor

    beat_processor = RNNBeatProcessor()
    beats = beat_processor(audio_path)
    tempo_processor = TempoEstimationProcessor(fps=200)
    tempos = tempo_processor(beats)

    if len(tempos):
        top_tempo = tempos[0][0]
        adjusted = _adjust_tempo(top_tempo)
        result = round(adjusted)
        cache_file.write_text(str(result))
        return result
    return 0


def get_audio_duration(audio_path: str) -> float:
    """Get audio duration in seconds using madmom's Signal."""
    import madmom

    sig = madmom.audio.signal.Signal(audio_path)
    return len(sig) / sig.sample_rate


def analyze_audio(audio_path: str) -> AnalysisResult:
    """Run all three analyses and return combined result."""
    chords = detect_chords(audio_path)
    key = detect_key(audio_path)
    tempo = detect_tempo(audio_path)
    duration = chords[-1].end if chords else get_audio_duration(audio_path)

    return AnalysisResult(
        key=key,
        tempo=tempo,
        chords=chords,
        duration=duration,
    )
```

**Step 2: Create tests for cache and tempo adjustment logic**

```python
# backend/tests/__init__.py
# (empty)
```

```python
# backend/tests/test_analysis.py
import tempfile
from pathlib import Path
from app.analysis import _adjust_tempo, _cache_path, Chord

def test_adjust_tempo_normal():
    assert _adjust_tempo(120) == 120

def test_adjust_tempo_too_slow():
    assert _adjust_tempo(35) == 140  # 35 * 2 = 70, * 2 = 140

def test_adjust_tempo_too_fast():
    assert _adjust_tempo(240) == 120  # 240 / 2 = 120

def test_cache_path_deterministic():
    p1 = _cache_path("/some/file.mp3", "chord")
    p2 = _cache_path("/some/file.mp3", "chord")
    assert p1 == p2

def test_cache_path_different_categories():
    p1 = _cache_path("/some/file.mp3", "chord")
    p2 = _cache_path("/some/file.mp3", "key")
    assert p1 != p2
    assert "chord" in str(p1)
    assert "key" in str(p2)
```

**Step 3: Run tests**

```bash
cd backend && uv run pytest tests/ -v
```

Expected: All tests pass.

**Step 4: Commit**

```bash
git add backend/app/analysis.py backend/tests/
git commit -m "Task 2: Backend analysis module porting madmom processing

refs: docs/plans/2026-02-28-dechord-web-implementation.md"
```

---

## Task 3: Backend API Endpoints

- [x] Step 1: Create API routes for analyze, status, result, audio
- [x] Step 2: Create tests for API endpoints
- [x] Step 3: Run tests
- [x] Step 4: Commit

**Files:**
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_api.py`

**Step 1: Create API routes**

```python
# backend/app/main.py
import uuid
import shutil
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.analysis import analyze_audio, AnalysisResult

app = FastAPI(title="DeChord API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# In-memory job store (sufficient for single-user local tool)
jobs: dict[str, dict] = {}
executor = ThreadPoolExecutor(max_workers=2)


def _run_analysis(job_id: str, audio_path: str):
    try:
        jobs[job_id]["status"] = "processing"
        jobs[job_id]["progress"] = "Analyzing audio..."
        result = analyze_audio(audio_path)
        jobs[job_id]["status"] = "complete"
        jobs[job_id]["result"] = result
    except Exception as e:
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = str(e)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.post("/api/analyze")
async def analyze(file: UploadFile):
    job_id = uuid.uuid4().hex[:12]
    ext = Path(file.filename).suffix if file.filename else ".mp3"
    audio_path = UPLOAD_DIR / f"{job_id}{ext}"

    with open(audio_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    jobs[job_id] = {
        "status": "queued",
        "audio_path": str(audio_path),
    }

    executor.submit(_run_analysis, job_id, str(audio_path))
    return {"job_id": job_id}


@app.get("/api/status/{job_id}")
async def status(job_id: str):
    if job_id not in jobs:
        raise HTTPException(404, "Job not found")
    job = jobs[job_id]
    return {
        "status": job["status"],
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

    r: AnalysisResult = job["result"]
    return {
        "key": r.key,
        "tempo": r.tempo,
        "duration": r.duration,
        "chords": [
            {"start": c.start, "end": c.end, "label": c.label}
            for c in r.chords
        ],
    }


@app.get("/api/audio/{job_id}")
async def audio(job_id: str):
    if job_id not in jobs:
        raise HTTPException(404, "Job not found")
    audio_path = jobs[job_id]["audio_path"]
    return FileResponse(audio_path, media_type="audio/mpeg")
```

**Step 2: Create API tests**

```python
# backend/tests/test_api.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_status_not_found():
    response = client.get("/api/status/nonexistent")
    assert response.status_code == 404


def test_result_not_found():
    response = client.get("/api/result/nonexistent")
    assert response.status_code == 404
```

**Step 3: Run tests**

```bash
cd backend && uv run pytest tests/ -v
```

Expected: All tests pass.

**Step 4: Commit**

```bash
git add backend/app/main.py backend/tests/test_api.py
git commit -m "Task 3: Backend API endpoints for analyze, status, result, audio

refs: docs/plans/2026-02-28-dechord-web-implementation.md"
```

---

## Task 4: Frontend Project Setup

- [x] Step 1: Scaffold Vite + React + TypeScript project with Bun
- [x] Step 2: Install Tailwind CSS v4
- [x] Step 3: Configure Vite proxy to backend
- [x] Step 4: Verify dev server starts
- [x] Step 5: Commit

**Files:**
- Create: `frontend/` (scaffolded by Vite)
- Modify: `frontend/vite.config.ts`
- Modify: `frontend/src/index.css`

**Step 1: Scaffold project**

```bash
cd /Users/wojciechgula/Projects/DeChord
bun create vite frontend --template react-ts
cd frontend && bun install
```

**Step 2: Install Tailwind CSS v4**

```bash
cd frontend && bun add -d tailwindcss @tailwindcss/vite
```

Update `vite.config.ts`:
```typescript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
```

Replace `frontend/src/index.css` with:
```css
@import "tailwindcss";
```

**Step 3: Clean up scaffolded files**

Remove `App.css`, update `App.tsx` to a minimal shell:

```tsx
// frontend/src/App.tsx
function App() {
  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      <h1 className="text-2xl p-4">DeChord</h1>
    </div>
  );
}

export default App;
```

**Step 4: Verify dev server starts**

```bash
cd frontend && bun dev
```

Expected: Vite dev server on http://localhost:5173, shows "DeChord" heading with dark background.

**Step 5: Commit**

```bash
git add frontend/
git commit -m "Task 4: Frontend project setup with Vite, React, TypeScript, Tailwind

refs: docs/plans/2026-02-28-dechord-web-implementation.md"
```

---

## Task 5: Frontend API Client & Types

- [x] Step 1: Create TypeScript types for API responses
- [x] Step 2: Create API client module
- [x] Step 3: Commit

**Files:**
- Create: `frontend/src/lib/types.ts`
- Create: `frontend/src/lib/api.ts`

**Step 1: Create types**

```typescript
// frontend/src/lib/types.ts
export interface Chord {
  start: number;
  end: number;
  label: string;
}

export interface AnalysisResult {
  key: string;
  tempo: number;
  duration: number;
  chords: Chord[];
}

export interface JobStatus {
  status: "queued" | "processing" | "complete" | "error";
  progress?: string;
  error?: string;
}
```

**Step 2: Create API client**

```typescript
// frontend/src/lib/api.ts
import type { JobStatus, AnalysisResult } from "./types";

const BASE = "";

export async function uploadAudio(file: File): Promise<string> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${BASE}/api/analyze`, { method: "POST", body: form });
  if (!res.ok) throw new Error("Upload failed");
  const data = await res.json();
  return data.job_id;
}

export async function getJobStatus(jobId: string): Promise<JobStatus> {
  const res = await fetch(`${BASE}/api/status/${jobId}`);
  if (!res.ok) throw new Error("Status check failed");
  return res.json();
}

export async function getResult(jobId: string): Promise<AnalysisResult> {
  const res = await fetch(`${BASE}/api/result/${jobId}`);
  if (!res.ok) throw new Error("Result fetch failed");
  return res.json();
}

export function getAudioUrl(jobId: string): string {
  return `${BASE}/api/audio/${jobId}`;
}

export async function pollUntilComplete(
  jobId: string,
  onProgress?: (status: JobStatus) => void,
  intervalMs = 1000,
): Promise<AnalysisResult> {
  while (true) {
    const status = await getJobStatus(jobId);
    onProgress?.(status);
    if (status.status === "complete") {
      return getResult(jobId);
    }
    if (status.status === "error") {
      throw new Error(status.error || "Analysis failed");
    }
    await new Promise((r) => setTimeout(r, intervalMs));
  }
}
```

**Step 3: Commit**

```bash
git add frontend/src/lib/
git commit -m "Task 5: Frontend API client and TypeScript types

refs: docs/plans/2026-02-28-dechord-web-implementation.md"
```

---

## Task 6: Music Theory Utility (Chord-to-Notes Mapping)

- [x] Step 1: Create music utility with chord parsing and fretboard mapping
- [x] Step 2: Create tests
- [x] Step 3: Run tests
- [x] Step 4: Commit

**Files:**
- Create: `frontend/src/lib/music.ts`
- Create: `frontend/src/lib/__tests__/music.test.ts`

**Step 1: Create music utility**

```typescript
// frontend/src/lib/music.ts
const NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];

// Semitone intervals from root for each chord quality
const CHORD_INTERVALS: Record<string, number[]> = {
  "": [0, 4, 7],            // major
  m: [0, 3, 7],             // minor
  "7": [0, 4, 7, 10],       // dominant 7th
  maj7: [0, 4, 7, 11],      // major 7th
  m7: [0, 3, 7, 10],        // minor 7th
  dim: [0, 3, 6],           // diminished
  aug: [0, 4, 8],           // augmented
  sus2: [0, 2, 7],          // suspended 2nd
  sus4: [0, 5, 7],          // suspended 4th
};

/** Bass string open notes (low to high): E1, A1, D2, G2 */
const BASS_STRINGS = [
  { name: "E", midi: 28 },  // E1
  { name: "A", midi: 33 },  // A1
  { name: "D", midi: 38 },  // D2
  { name: "G", midi: 43 },  // G2
];

const NUM_FRETS = 12;

export function noteNameToIndex(name: string): number {
  // Handle flats by converting to sharps
  const normalized = name
    .replace("Db", "C#")
    .replace("Eb", "D#")
    .replace("Gb", "F#")
    .replace("Ab", "G#")
    .replace("Bb", "A#");
  const idx = NOTE_NAMES.indexOf(normalized);
  if (idx === -1) throw new Error(`Unknown note: ${name}`);
  return idx;
}

export function parseChordLabel(label: string): { root: number; quality: string } | null {
  if (label === "N" || label === "X" || !label) return null;

  // Match root note (with optional # or b) and quality
  const match = label.match(/^([A-G][#b]?)(.*)$/);
  if (!match) return null;

  const root = noteNameToIndex(match[1]);
  const quality = match[2];
  return { root, quality };
}

export function getChordNotes(label: string): number[] {
  const parsed = parseChordLabel(label);
  if (!parsed) return [];

  const intervals = CHORD_INTERVALS[parsed.quality] ?? CHORD_INTERVALS[""];
  return intervals.map((i) => (parsed.root + i) % 12);
}

export interface FretPosition {
  string: number; // 0=E, 1=A, 2=D, 3=G
  fret: number;   // 0-12
  note: string;   // note name
}

export function getFretboardPositions(label: string): FretPosition[] {
  const chordNotes = getChordNotes(label);
  if (chordNotes.length === 0) return [];

  const positions: FretPosition[] = [];

  for (let s = 0; s < BASS_STRINGS.length; s++) {
    const openMidi = BASS_STRINGS[s].midi;
    for (let fret = 0; fret <= NUM_FRETS; fret++) {
      const midi = openMidi + fret;
      const noteIndex = midi % 12;
      if (chordNotes.includes(noteIndex)) {
        positions.push({
          string: s,
          fret,
          note: NOTE_NAMES[noteIndex],
        });
      }
    }
  }

  return positions;
}

export { NOTE_NAMES, BASS_STRINGS, NUM_FRETS };
```

**Step 2: Create tests**

First install vitest:
```bash
cd frontend && bun add -d vitest
```

Add to `frontend/package.json` scripts:
```json
"test": "vitest run",
"test:watch": "vitest"
```

```typescript
// frontend/src/lib/__tests__/music.test.ts
import { describe, it, expect } from "vitest";
import {
  noteNameToIndex,
  parseChordLabel,
  getChordNotes,
  getFretboardPositions,
} from "../music";

describe("noteNameToIndex", () => {
  it("returns correct index for C", () => {
    expect(noteNameToIndex("C")).toBe(0);
  });
  it("returns correct index for A", () => {
    expect(noteNameToIndex("A")).toBe(9);
  });
  it("handles sharps", () => {
    expect(noteNameToIndex("F#")).toBe(6);
  });
  it("handles flats by converting to sharps", () => {
    expect(noteNameToIndex("Bb")).toBe(10);
  });
});

describe("parseChordLabel", () => {
  it("parses major chord", () => {
    expect(parseChordLabel("C")).toEqual({ root: 0, quality: "" });
  });
  it("parses minor chord", () => {
    expect(parseChordLabel("Am")).toEqual({ root: 9, quality: "m" });
  });
  it("returns null for N (no chord)", () => {
    expect(parseChordLabel("N")).toBeNull();
  });
  it("parses seventh chord", () => {
    expect(parseChordLabel("G7")).toEqual({ root: 7, quality: "7" });
  });
});

describe("getChordNotes", () => {
  it("returns correct notes for C major", () => {
    // C=0, E=4, G=7
    expect(getChordNotes("C")).toEqual([0, 4, 7]);
  });
  it("returns correct notes for Am", () => {
    // A=9, C=0, E=4
    expect(getChordNotes("Am")).toEqual([9, 0, 4]);
  });
  it("returns empty for N", () => {
    expect(getChordNotes("N")).toEqual([]);
  });
});

describe("getFretboardPositions", () => {
  it("returns positions for Am chord", () => {
    const positions = getFretboardPositions("Am");
    expect(positions.length).toBeGreaterThan(0);
    // All positions should be A, C, or E notes
    for (const pos of positions) {
      expect(["A", "C", "E"]).toContain(pos.note);
    }
  });
  it("includes open E string for E chord", () => {
    const positions = getFretboardPositions("E");
    const openE = positions.find((p) => p.string === 0 && p.fret === 0);
    expect(openE).toBeDefined();
    expect(openE!.note).toBe("E");
  });
});
```

**Step 3: Run tests**

```bash
cd frontend && bun test
```

Expected: All tests pass.

**Step 4: Commit**

```bash
git add frontend/src/lib/music.ts frontend/src/lib/__tests__/ frontend/package.json
git commit -m "Task 6: Music theory utility with chord-to-fretboard mapping

refs: docs/plans/2026-02-28-dechord-web-implementation.md"
```

---

## Task 7: Audio Player Hook

- [x] Step 1: Create useAudioPlayer hook
- [x] Step 2: Commit

**Files:**
- Create: `frontend/src/hooks/useAudioPlayer.ts`

**Step 1: Create the hook**

```typescript
// frontend/src/hooks/useAudioPlayer.ts
import { useRef, useState, useCallback, useEffect } from "react";

export interface LoopPoints {
  start: number; // seconds
  end: number;   // seconds
}

export function useAudioPlayer(src: string | null) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const rafRef = useRef<number>(0);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [volume, setVolumeState] = useState(1);
  const [loop, setLoop] = useState<LoopPoints | null>(null);

  // Create audio element when src changes
  useEffect(() => {
    if (!src) return;
    const audio = new Audio(src);
    audioRef.current = audio;

    audio.addEventListener("loadedmetadata", () => {
      setDuration(audio.duration);
    });
    audio.addEventListener("ended", () => {
      setPlaying(false);
    });

    return () => {
      audio.pause();
      audio.src = "";
      audioRef.current = null;
      cancelAnimationFrame(rafRef.current);
    };
  }, [src]);

  // Animation frame loop for time tracking
  useEffect(() => {
    if (!playing) {
      cancelAnimationFrame(rafRef.current);
      return;
    }

    const tick = () => {
      const audio = audioRef.current;
      if (!audio) return;
      setCurrentTime(audio.currentTime);

      // Handle loop
      if (loop && audio.currentTime >= loop.end) {
        audio.currentTime = loop.start;
      }

      rafRef.current = requestAnimationFrame(tick);
    };
    rafRef.current = requestAnimationFrame(tick);

    return () => cancelAnimationFrame(rafRef.current);
  }, [playing, loop]);

  const play = useCallback(() => {
    const audio = audioRef.current;
    if (!audio) return;
    audio.play();
    setPlaying(true);
  }, []);

  const pause = useCallback(() => {
    const audio = audioRef.current;
    if (!audio) return;
    audio.pause();
    setPlaying(false);
  }, []);

  const togglePlay = useCallback(() => {
    if (playing) pause();
    else play();
  }, [playing, play, pause]);

  const seek = useCallback((time: number) => {
    const audio = audioRef.current;
    if (!audio) return;
    audio.currentTime = time;
    setCurrentTime(time);
  }, []);

  const seekRelative = useCallback(
    (delta: number) => {
      const audio = audioRef.current;
      if (!audio) return;
      const newTime = Math.max(0, Math.min(audio.duration, audio.currentTime + delta));
      audio.currentTime = newTime;
      setCurrentTime(newTime);
    },
    [],
  );

  const setVolume = useCallback((v: number) => {
    const audio = audioRef.current;
    if (audio) audio.volume = v;
    setVolumeState(v);
  }, []);

  return {
    currentTime,
    duration,
    playing,
    volume,
    loop,
    play,
    pause,
    togglePlay,
    seek,
    seekRelative,
    setVolume,
    setLoop,
  };
}
```

**Step 2: Commit**

```bash
git add frontend/src/hooks/useAudioPlayer.ts
git commit -m "Task 7: Audio player hook with seeking, looping, and volume control

refs: docs/plans/2026-02-28-dechord-web-implementation.md"
```

---

## Task 8: Chord Sync Hook

- [x] Step 1: Create useChordSync hook
- [x] Step 2: Commit

**Files:**
- Create: `frontend/src/hooks/useChordSync.ts`

**Step 1: Create the hook**

```typescript
// frontend/src/hooks/useChordSync.ts
import { useMemo } from "react";
import type { Chord } from "../lib/types";

export function useChordSync(chords: Chord[], currentTime: number) {
  const currentIndex = useMemo(() => {
    // Binary search for current chord
    let lo = 0;
    let hi = chords.length - 1;
    while (lo <= hi) {
      const mid = Math.floor((lo + hi) / 2);
      if (currentTime < chords[mid].start) {
        hi = mid - 1;
      } else if (currentTime >= chords[mid].end) {
        lo = mid + 1;
      } else {
        return mid;
      }
    }
    return -1;
  }, [chords, currentTime]);

  const currentChord = currentIndex >= 0 ? chords[currentIndex] : null;

  const progress = currentChord
    ? (currentTime - currentChord.start) / (currentChord.end - currentChord.start)
    : 0;

  return { currentIndex, currentChord, progress };
}
```

**Step 2: Commit**

```bash
git add frontend/src/hooks/useChordSync.ts
git commit -m "Task 8: Chord sync hook with binary search for current chord

refs: docs/plans/2026-02-28-dechord-web-implementation.md"
```

---

## Task 9: DropZone Component

- [x] Step 1: Create DropZone component
- [x] Step 2: Commit

**Files:**
- Create: `frontend/src/components/DropZone.tsx`

**Step 1: Create component**

```tsx
// frontend/src/components/DropZone.tsx
import { useCallback, useState, useRef } from "react";

interface DropZoneProps {
  onFile: (file: File) => void;
  loading?: boolean;
  progress?: string;
}

const ACCEPTED = [".mp3", ".wav", ".m4a", ".aac", ".mp4"];

export function DropZone({ onFile, loading, progress }: DropZoneProps) {
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const file = e.dataTransfer.files[0];
      if (file) onFile(file);
    },
    [onFile],
  );

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) onFile(file);
    },
    [onFile],
  );

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-4">
        <div className="w-8 h-8 border-2 border-gray-400 border-t-white rounded-full animate-spin" />
        <p className="text-gray-400 text-sm">{progress || "Analyzing..."}</p>
      </div>
    );
  }

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setDragOver(true);
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={handleDrop}
      onClick={() => inputRef.current?.click()}
      className={`flex flex-col items-center justify-center h-64 border-2 border-dashed rounded-lg cursor-pointer transition-colors ${
        dragOver
          ? "border-blue-400 bg-blue-400/10"
          : "border-gray-600 hover:border-gray-400"
      }`}
    >
      <p className="text-gray-400 mb-2">Drop audio file here or click to browse</p>
      <p className="text-gray-600 text-sm">MP3, WAV, M4A, AAC</p>
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED.join(",")}
        onChange={handleChange}
        className="hidden"
      />
    </div>
  );
}
```

**Step 2: Commit**

```bash
git add frontend/src/components/DropZone.tsx
git commit -m "Task 9: DropZone component with drag-and-drop and file picker

refs: docs/plans/2026-02-28-dechord-web-implementation.md"
```

---

## Task 10: ChordTimeline Component

- [x] Step 1: Create ChordTimeline component with wrapping lines and playhead
- [x] Step 2: Commit

**Files:**
- Create: `frontend/src/components/ChordTimeline.tsx`

**Step 1: Create component**

This is the core UI component. It renders chord blocks with widths proportional to duration, wrapping like text. Uses CSS flexbox with `flex-wrap` for natural line breaking.

```tsx
// frontend/src/components/ChordTimeline.tsx
import { useRef, useEffect, useCallback } from "react";
import type { Chord } from "../lib/types";

interface ChordTimelineProps {
  chords: Chord[];
  currentIndex: number;
  currentTime: number;
  duration: number;
  loopStart: number | null;
  loopEnd: number | null;
  onChordClick: (index: number) => void;
  onSeek: (time: number) => void;
}

const PIXELS_PER_SECOND = 40;
const MIN_BLOCK_WIDTH = 48;

export function ChordTimeline({
  chords,
  currentIndex,
  currentTime,
  duration,
  loopStart,
  loopEnd,
  onChordClick,
  onSeek,
}: ChordTimelineProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const activeRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to keep current chord visible
  useEffect(() => {
    if (activeRef.current) {
      activeRef.current.scrollIntoView({
        behavior: "smooth",
        block: "center",
      });
    }
  }, [currentIndex]);

  const getBlockWidth = useCallback((chord: Chord) => {
    const w = (chord.end - chord.start) * PIXELS_PER_SECOND;
    return Math.max(w, MIN_BLOCK_WIDTH);
  }, []);

  const isInLoop = useCallback(
    (index: number) => {
      if (loopStart === null || loopEnd === null) return false;
      return index >= loopStart && index <= loopEnd;
    },
    [loopStart, loopEnd],
  );

  return (
    <div ref={containerRef} className="flex flex-wrap gap-1 p-4 overflow-y-auto">
      {chords.map((chord, i) => {
        const isCurrent = i === currentIndex;
        const inLoop = isInLoop(i);
        const progress =
          isCurrent && chord.end > chord.start
            ? ((currentTime - chord.start) / (chord.end - chord.start)) * 100
            : 0;

        return (
          <div
            key={i}
            ref={isCurrent ? activeRef : undefined}
            onClick={() => onChordClick(i)}
            style={{ width: getBlockWidth(chord) }}
            className={`relative h-10 flex items-center justify-center rounded text-sm font-mono cursor-pointer select-none overflow-hidden transition-colors ${
              isCurrent
                ? "bg-blue-600 text-white"
                : inLoop
                  ? "bg-indigo-800 text-indigo-200"
                  : "bg-gray-800 text-gray-300 hover:bg-gray-700"
            }`}
          >
            {/* Progress fill for current chord */}
            {isCurrent && (
              <div
                className="absolute inset-y-0 left-0 bg-blue-400/30"
                style={{ width: `${progress}%` }}
              />
            )}
            <span className="relative z-10">{chord.label}</span>
            {/* Loop boundary markers */}
            {loopStart === i && (
              <div className="absolute left-0 top-0 bottom-0 w-1 bg-green-400" />
            )}
            {loopEnd === i && (
              <div className="absolute right-0 top-0 bottom-0 w-1 bg-red-400" />
            )}
          </div>
        );
      })}
    </div>
  );
}
```

**Step 2: Commit**

```bash
git add frontend/src/components/ChordTimeline.tsx
git commit -m "Task 10: ChordTimeline component with wrapping, playhead, and loop markers

refs: docs/plans/2026-02-28-dechord-web-implementation.md"
```

---

## Task 11: Fretboard Component

- [x] Step 1: Create Fretboard component
- [x] Step 2: Commit

**Files:**
- Create: `frontend/src/components/Fretboard.tsx`

**Step 1: Create component**

```tsx
// frontend/src/components/Fretboard.tsx
import { useMemo } from "react";
import { getFretboardPositions, BASS_STRINGS, NUM_FRETS } from "../lib/music";

interface FretboardProps {
  chordLabel: string | null;
}

export function Fretboard({ chordLabel }: FretboardProps) {
  const positions = useMemo(
    () => (chordLabel ? getFretboardPositions(chordLabel) : []),
    [chordLabel],
  );

  const isActive = (string: number, fret: number) =>
    positions.some((p) => p.string === string && p.fret === fret);

  return (
    <div className="px-4 py-3 bg-gray-900 border-t border-gray-800">
      {/* Fret numbers */}
      <div className="flex ml-8">
        {Array.from({ length: NUM_FRETS + 1 }, (_, i) => (
          <div
            key={i}
            className="flex-1 text-center text-xs text-gray-600"
          >
            {i}
          </div>
        ))}
      </div>
      {/* Strings (G at top, E at bottom — visual convention) */}
      {[...BASS_STRINGS].reverse().map((str, displayIdx) => {
        const stringIdx = BASS_STRINGS.length - 1 - displayIdx;
        return (
          <div key={str.name} className="flex items-center h-8">
            <div className="w-8 text-right pr-2 text-xs text-gray-500 font-mono">
              {str.name}
            </div>
            <div className="flex-1 flex relative">
              {/* String line */}
              <div className="absolute inset-y-1/2 left-0 right-0 h-px bg-gray-600" />
              {Array.from({ length: NUM_FRETS + 1 }, (_, fret) => (
                <div key={fret} className="flex-1 flex items-center justify-center relative">
                  {/* Fret line */}
                  {fret > 0 && (
                    <div className="absolute left-0 top-0 bottom-0 w-px bg-gray-700" />
                  )}
                  {/* Note dot */}
                  {isActive(stringIdx, fret) && (
                    <div className="w-5 h-5 rounded-full bg-blue-500 text-[10px] flex items-center justify-center text-white font-bold z-10">
                      {positions.find(
                        (p) => p.string === stringIdx && p.fret === fret,
                      )?.note}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        );
      })}
      {/* Current chord label */}
      <div className="text-center mt-2 text-lg font-bold text-blue-400">
        {chordLabel || "—"}
      </div>
    </div>
  );
}
```

**Step 2: Commit**

```bash
git add frontend/src/components/Fretboard.tsx
git commit -m "Task 11: Bass fretboard component with note highlighting

refs: docs/plans/2026-02-28-dechord-web-implementation.md"
```

---

## Task 12: TransportBar Component

- [x] Step 1: Create TransportBar component
- [x] Step 2: Commit

**Files:**
- Create: `frontend/src/components/TransportBar.tsx`

**Step 1: Create component**

```tsx
// frontend/src/components/TransportBar.tsx
interface TransportBarProps {
  currentTime: number;
  duration: number;
  playing: boolean;
  volume: number;
  loopActive: boolean;
  loopLabel?: string;
  onTogglePlay: () => void;
  onSeek: (time: number) => void;
  onSeekRelative: (delta: number) => void;
  onVolumeChange: (v: number) => void;
  onClearLoop: () => void;
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export function TransportBar({
  currentTime,
  duration,
  playing,
  volume,
  loopActive,
  loopLabel,
  onTogglePlay,
  onSeek,
  onSeekRelative,
  onVolumeChange,
  onClearLoop,
}: TransportBarProps) {
  return (
    <div className="flex items-center gap-3 px-4 py-2 bg-gray-900 border-t border-gray-800">
      {/* Playback controls */}
      <button
        onClick={() => onSeekRelative(-10)}
        className="text-gray-400 hover:text-white text-sm px-1"
        title="Back 10s"
      >
        &#x23EA;
      </button>
      <button
        onClick={onTogglePlay}
        className="w-8 h-8 flex items-center justify-center rounded-full bg-blue-600 hover:bg-blue-500 text-white"
      >
        {playing ? "⏸" : "▶"}
      </button>
      <button
        onClick={() => onSeekRelative(10)}
        className="text-gray-400 hover:text-white text-sm px-1"
        title="Forward 10s"
      >
        &#x23E9;
      </button>

      {/* Time & progress */}
      <span className="text-xs text-gray-400 font-mono w-12 text-right">
        {formatTime(currentTime)}
      </span>
      <input
        type="range"
        min={0}
        max={duration || 1}
        step={0.1}
        value={currentTime}
        onChange={(e) => onSeek(parseFloat(e.target.value))}
        className="flex-1 h-1 accent-blue-500"
      />
      <span className="text-xs text-gray-400 font-mono w-12">
        {formatTime(duration)}
      </span>

      {/* Loop indicator */}
      {loopActive && (
        <button
          onClick={onClearLoop}
          className="text-xs px-2 py-1 rounded bg-indigo-800 text-indigo-200 hover:bg-indigo-700"
          title="Click to clear loop"
        >
          🔁 {loopLabel}
        </button>
      )}

      {/* Volume */}
      <input
        type="range"
        min={0}
        max={1}
        step={0.05}
        value={volume}
        onChange={(e) => onVolumeChange(parseFloat(e.target.value))}
        className="w-20 h-1 accent-blue-500"
      />
    </div>
  );
}
```

**Step 2: Commit**

```bash
git add frontend/src/components/TransportBar.tsx
git commit -m "Task 12: TransportBar with play, seek, volume, and loop controls

refs: docs/plans/2026-02-28-dechord-web-implementation.md"
```

---

## Task 13: Header Component

- [x] Step 1: Create Header component
- [x] Step 2: Commit

**Files:**
- Create: `frontend/src/components/Header.tsx`

**Step 1: Create component**

```tsx
// frontend/src/components/Header.tsx
interface HeaderProps {
  songKey?: string;
  tempo?: number;
  fileName?: string;
}

export function Header({ songKey, tempo, fileName }: HeaderProps) {
  return (
    <header className="flex items-center justify-between px-4 py-2 bg-gray-900 border-b border-gray-800">
      <div className="flex items-center gap-3">
        <h1 className="text-lg font-bold text-white">DeChord</h1>
        {fileName && (
          <span className="text-sm text-gray-400 truncate max-w-64">
            {fileName}
          </span>
        )}
      </div>
      <div className="flex items-center gap-3">
        {songKey && (
          <span className="text-sm text-gray-300">
            {songKey}
            {tempo ? ` | ${tempo} BPM` : ""}
          </span>
        )}
      </div>
    </header>
  );
}
```

**Step 2: Commit**

```bash
git add frontend/src/components/Header.tsx
git commit -m "Task 13: Header component with key, tempo, and filename display

refs: docs/plans/2026-02-28-dechord-web-implementation.md"
```

---

## Task 14: App Integration — Wire Everything Together

- [x] Step 1: Update App.tsx to integrate all components
- [x] Step 2: Test end-to-end manually
- [x] Step 3: Commit

**Files:**
- Modify: `frontend/src/App.tsx`

**Step 1: Update App.tsx**

```tsx
// frontend/src/App.tsx
import { useState, useCallback } from "react";
import { Header } from "./components/Header";
import { DropZone } from "./components/DropZone";
import { ChordTimeline } from "./components/ChordTimeline";
import { Fretboard } from "./components/Fretboard";
import { TransportBar } from "./components/TransportBar";
import { useAudioPlayer } from "./hooks/useAudioPlayer";
import { useChordSync } from "./hooks/useChordSync";
import { uploadAudio, pollUntilComplete, getAudioUrl } from "./lib/api";
import type { AnalysisResult } from "./lib/types";

function App() {
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState("");
  const [fileName, setFileName] = useState("");
  const [error, setError] = useState<string | null>(null);

  // Loop state: indices into chords array
  const [loopStartIdx, setLoopStartIdx] = useState<number | null>(null);
  const [loopEndIdx, setLoopEndIdx] = useState<number | null>(null);

  const audioSrc = jobId ? getAudioUrl(jobId) : null;
  const player = useAudioPlayer(audioSrc);
  const { currentIndex, currentChord } = useChordSync(
    result?.chords ?? [],
    player.currentTime,
  );

  // Compute loop points in seconds from chord indices
  const loopPoints =
    result && loopStartIdx !== null && loopEndIdx !== null
      ? {
          start: result.chords[loopStartIdx].start,
          end: result.chords[loopEndIdx].end,
        }
      : null;

  // Sync loop points to audio player
  if (loopPoints && player.loop?.start !== loopPoints.start) {
    player.setLoop(loopPoints);
  }
  if (!loopPoints && player.loop) {
    player.setLoop(null);
  }

  const handleFile = useCallback(async (file: File) => {
    setLoading(true);
    setError(null);
    setFileName(file.name.replace(/\.[^.]+$/, ""));
    setLoopStartIdx(null);
    setLoopEndIdx(null);

    try {
      const id = await uploadAudio(file);
      setJobId(id);
      const analysisResult = await pollUntilComplete(id, (s) => {
        setProgress(s.progress || "Processing...");
      });
      setResult(analysisResult);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Analysis failed");
    } finally {
      setLoading(false);
    }
  }, []);

  const handleChordClick = useCallback(
    (index: number) => {
      if (loopStartIdx === null) {
        setLoopStartIdx(index);
      } else if (loopEndIdx === null) {
        if (index > loopStartIdx) {
          setLoopEndIdx(index);
        } else if (index < loopStartIdx) {
          // Clicked before start — make this the new start
          setLoopEndIdx(loopStartIdx);
          setLoopStartIdx(index);
        } else {
          // Clicked same chord — seek to it
          if (result) player.seek(result.chords[index].start);
        }
      } else {
        // Loop already set — clear and start new
        setLoopStartIdx(index);
        setLoopEndIdx(null);
      }
    },
    [loopStartIdx, loopEndIdx, result, player],
  );

  const clearLoop = useCallback(() => {
    setLoopStartIdx(null);
    setLoopEndIdx(null);
  }, []);

  const loopLabel =
    result && loopStartIdx !== null && loopEndIdx !== null
      ? `${result.chords[loopStartIdx].label} → ${result.chords[loopEndIdx].label}`
      : undefined;

  return (
    <div className="flex flex-col h-screen bg-gray-950 text-gray-100">
      <Header
        songKey={result?.key}
        tempo={result?.tempo}
        fileName={fileName || undefined}
      />

      <main className="flex-1 overflow-y-auto">
        {!result && !loading && (
          <div className="flex items-center justify-center h-full p-4">
            <DropZone onFile={handleFile} />
          </div>
        )}

        {loading && (
          <div className="flex items-center justify-center h-full">
            <DropZone onFile={() => {}} loading progress={progress} />
          </div>
        )}

        {error && (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <p className="text-red-400 mb-4">{error}</p>
              <button
                onClick={() => {
                  setError(null);
                  setResult(null);
                  setJobId(null);
                }}
                className="px-4 py-2 bg-gray-800 rounded hover:bg-gray-700"
              >
                Try again
              </button>
            </div>
          </div>
        )}

        {result && !loading && (
          <ChordTimeline
            chords={result.chords}
            currentIndex={currentIndex}
            currentTime={player.currentTime}
            duration={result.duration}
            loopStart={loopStartIdx}
            loopEnd={loopEndIdx}
            onChordClick={handleChordClick}
            onSeek={player.seek}
          />
        )}
      </main>

      {result && (
        <>
          <Fretboard chordLabel={currentChord?.label ?? null} />
          <TransportBar
            currentTime={player.currentTime}
            duration={player.duration}
            playing={player.playing}
            volume={player.volume}
            loopActive={loopStartIdx !== null && loopEndIdx !== null}
            loopLabel={loopLabel}
            onTogglePlay={player.togglePlay}
            onSeek={player.seek}
            onSeekRelative={player.seekRelative}
            onVolumeChange={player.setVolume}
            onClearLoop={clearLoop}
          />
        </>
      )}
    </div>
  );
}

export default App;
```

**Step 2: Test end-to-end manually**

Start both servers:
```bash
# Terminal 1
cd backend && uv run fastapi dev app/main.py --port 8000

# Terminal 2
cd frontend && bun dev
```

Open http://localhost:5173, drop an audio file, verify:
1. File uploads and analysis runs
2. Chord timeline appears with wrapped lines
3. Audio plays with playhead tracking
4. Fretboard highlights notes for current chord
5. Clicking chords sets loop points
6. Transport bar controls work (play/pause, seek, volume)

**Step 3: Commit**

```bash
git add frontend/src/App.tsx
git commit -m "Task 14: App integration wiring all components together

refs: docs/plans/2026-02-28-dechord-web-implementation.md"
```

---

## Task 15: Makefile for Dev Workflow

- [x] Step 1: Create Makefile
- [x] Step 2: Commit

**Files:**
- Create: `Makefile`

**Step 1: Create Makefile**

```makefile
# Makefile
.PHONY: dev backend frontend install test

install:
	cd backend && uv sync
	cd frontend && bun install

dev:
	@echo "Starting backend and frontend..."
	@make backend & make frontend & wait

backend:
	cd backend && uv run fastapi dev app/main.py --port 8000

frontend:
	cd frontend && bun dev

test:
	cd backend && uv run pytest tests/ -v
	cd frontend && bun test
```

**Step 2: Commit**

```bash
git add Makefile
git commit -m "Task 15: Makefile for dev workflow

refs: docs/plans/2026-02-28-dechord-web-implementation.md"
```

---

## Task 16: Dockerfile for Future Deployment

- [ ] Step 1: Create Dockerfile (multi-stage)
- [ ] Step 2: Test build
- [ ] Step 3: Commit

**Files:**
- Create: `Dockerfile`

**Step 1: Create Dockerfile**

```dockerfile
# Dockerfile
# Stage 1: Build frontend
FROM oven/bun:1 AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/bun.lock* ./
RUN bun install --frozen-lockfile
COPY frontend/ .
RUN bun run build

# Stage 2: Python backend + static frontend
FROM python:3.13-slim AS runtime
WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install Python dependencies
COPY backend/pyproject.toml backend/uv.lock* ./backend/
RUN cd backend && uv sync --no-dev

# Copy backend code
COPY backend/ ./backend/

# Copy built frontend
COPY --from=frontend-build /app/frontend/dist ./backend/static/

EXPOSE 8000

CMD ["uv", "run", "--directory", "backend", "fastapi", "run", "app/main.py", "--port", "8000", "--host", "0.0.0.0"]
```

Add static file serving to FastAPI (update `backend/app/main.py`):

Add after the existing routes:
```python
from fastapi.staticfiles import StaticFiles
import os

# Serve frontend static files in production
if os.path.exists("static"):
    app.mount("/", StaticFiles(directory="static", html=True), name="static")
```

**Step 2: Test build**

```bash
docker build -t dechord .
```

Expected: Build completes successfully.

**Step 3: Commit**

```bash
git add Dockerfile backend/app/main.py
git commit -m "Task 16: Dockerfile for production deployment

refs: docs/plans/2026-02-28-dechord-web-implementation.md"
```

---

## Summary

| Task | Description | Est. |
|------|-------------|------|
| 1 | Backend project setup | 5 min |
| 2 | Analysis module (port madmom) | 10 min |
| 3 | API endpoints | 10 min |
| 4 | Frontend project setup | 5 min |
| 5 | API client & types | 5 min |
| 6 | Music theory utility | 15 min |
| 7 | Audio player hook | 10 min |
| 8 | Chord sync hook | 5 min |
| 9 | DropZone component | 5 min |
| 10 | ChordTimeline component | 15 min |
| 11 | Fretboard component | 15 min |
| 12 | TransportBar component | 10 min |
| 13 | Header component | 5 min |
| 14 | App integration | 15 min |
| 15 | Makefile | 5 min |
| 16 | Dockerfile | 10 min |
