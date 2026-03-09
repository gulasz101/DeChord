# DeChord

DeChord is a web application for analyzing uploaded audio and exploring the results in a browser. The project combines a FastAPI backend with a React frontend for chord and key detection, song library management, playback, notes, and generated bass-tab artifacts.

## Stack

- Frontend: React 19, TypeScript, Vite, Tailwind CSS v4
- Backend: FastAPI, Python 3.13+
- Analysis: madmom-based chord, key, and tempo detection
- Storage: LibSQL for local song and analysis data

## Web App Features

- Upload audio files for browser-based analysis
- Detect musical key, tempo, and timed chord changes
- Keep a local song library with persisted analysis results
- Play songs in the browser with saved playback preferences
- Add timestamp notes and chord-linked notes
- Generate bass transcription artifacts including MIDI and GP5 tab exports

## Repository Layout

- `frontend/`: React web client
- `backend/`: FastAPI API and analysis pipeline
- `docs/plans/`: implementation plans and execution history
- `designs.gpt54/`: retained design variant workspace
- `designs.opus46/`: retained design variant workspace

## Prerequisites

- Python 3.13+
- Node.js 18+ or newer

## Local Development

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
uvicorn app.main:app --reload
```

The API runs on `http://127.0.0.1:8000`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server runs on `http://127.0.0.1:5173`.

## Common Commands

### Backend

```bash
cd backend
python -m pytest tests -v
```

### Frontend

```bash
cd frontend
npm run test
npm run build
```

## Development Notes

- Progress and task execution are tracked in `docs/plans/`.
- Project instructions for agents live in `AGENTS.md`.
- `CLAUDE.md` links to `AGENTS.md` to keep instructions in one place.

## License

This project is licensed under the MIT License. See `LICENSE`.
