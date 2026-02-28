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
