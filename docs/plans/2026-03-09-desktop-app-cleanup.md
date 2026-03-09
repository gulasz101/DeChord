# Desktop App Cleanup - Web-Only Codebase Refocus

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans or superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** Remove all PyQt5 desktop application code, build artifacts, and dependencies to establish a clean, web-only codebase.

**Architecture:** Comprehensive single-pass cleanup removing three categories: (1) desktop UI code, (2) build/distribution scripts and assets, (3) redundant dependencies. Preserve web stack (frontend/, backend/) and the retained design variant directories (`designs.gpt54/`, `designs.opus46/`). Update documentation and git configuration to reflect web-only focus.

**Tech Stack:** FastAPI (backend), React 19 + Vite (frontend), Python 3.13+ (backend only)

## Execution Checklist

- [x] Task 0: Document current state, user overrides, and removal scope
- [x] Task 1: Remove PyQt5 desktop UI code
- [x] Task 2: Remove desktop build and distribution scripts
- [ ] Task 3: Remove desktop icon assets
- [ ] Task 4: Remove the tracked `designs/` directory and retain `designs.gpt54/` + `designs.opus46/`
- [ ] Task 5: Remove source export artifacts
- [ ] Task 6: Remove generated `docs/reports/` artifacts
- [ ] Task 7: Remove Demucs-Gui submodule and related git config
- [ ] Task 8: Audit backend dependencies in `backend/pyproject.toml`
- [ ] Task 9: Update `README.md`, `CLAUDE.md`, and any cleanup documentation references
- [ ] Task 10: Final verification, `make reset`, summary, and notification

## User Overrides Recorded On 2026-03-09

- [x] Execute directly on `main` with atomic commits; do not create a worktree for this cleanup.
- [x] Keep `designs.gpt54/` and `designs.opus46/`.
- [x] Remove the tracked `designs/` directory from the repository.
- [x] Remove generated files under `docs/reports/`.
- [x] Align `CLAUDE.md` with `AGENTS.md` via a link instead of duplicated content.

---

## Pre-Work: Inventory & Planning

### Task 0: Document Current State & Removal Scope

**Files:**
- Analyze: `main.py`, `interface.py`, `chords.py`, `key.py`, `theme.py` (PyQt5 desktop)
- Analyze: `Demucs-Gui/` (submodule + directory)
- Analyze: `backend/pyproject.toml` (dependency audit)
- Analyze: `README.md` (desktop references)
- Reference: `.gitmodules` (git submodule config)

**Step 1: Create inventory document (locally, not committed)**

Examine each file to confirm it's desktop-only:
- `main.py` - PyQt5 main window, audio playback, file dialogs → REMOVE
- `interface.py` - Qt UI components, drag-drop → REMOVE
- `chords.py` - utility for desktop app → REMOVE
- `key.py` - utility for desktop app → REMOVE
- `theme.py` - Qt theme styling → REMOVE
- `Demucs-Gui/` - external stem separation GUI → REMOVE + git submodule
- `createLinuxShortcut.sh`, `createWindowsShortcut.bat`, `hideWindowsTerminal.vbs` → REMOVE (desktop shortcuts)
- `icon/` - desktop app icon assets → REMOVE

**Step 2: Check backend dependencies**

Run: `cat backend/pyproject.toml`

Look for dependencies added only for Demucs integration or desktop audio handling:
- `librosa` - audio feature extraction (check if used by web backend)
- `numpy` - numeric operations (likely used, keep)
- `scipy` - signal processing (check if used by web backend)
- `PyQt5` - should not be in backend, but check
- `pyaudio` - audio input device handling (desktop only, remove from requirements if present)
- `soundfile` - audio file I/O (check if backend uses it)

Create a text file locally documenting findings (do NOT commit):
```
Files to Remove:
- main.py (PyQt5 main window)
- interface.py (Qt UI compiler output)
- chords.py (desktop utility)
- key.py (desktop utility)
- theme.py (Qt theme)
- Demucs-Gui/ (external stem GUI)
- createLinuxShortcut.sh
- createWindowsShortcut.bat
- hideWindowsTerminal.vbs
- icon/ (desktop assets)
- designs.gpt54/ (old design iteration)
- designs.opus46/ (old design iteration)
- DeChord-source-*.zip (export artifacts)

Dependencies to Review:
[After checking pyproject.toml]
```

**Step 3: Record user-approved scope changes in this plan**

- Keep `designs.gpt54/` and `designs.opus46/`
- Remove the tracked `designs/` directory instead of those variants
- Remove generated `docs/reports/` artifacts
- Replace duplicated `CLAUDE.md` contents with a link to `AGENTS.md`

---

## File & Directory Removal

### Task 1: Remove PyQt5 Desktop UI Code

**Files:**
- Delete: `main.py`
- Delete: `interface.py`
- Delete: `chords.py`
- Delete: `key.py`
- Delete: `theme.py`

**Step 1: Verify these files are not imported by frontend or backend**

Run: `grep -r "import main\|from main\|import interface\|from interface\|import chords\|from chords\|import key\|from key\|import theme\|from theme" frontend/ backend/ --include="*.py" --include="*.ts" --include="*.tsx"`

Expected: No matches (these are desktop-only)

**Step 2: Delete the files**

```bash
rm main.py interface.py chords.py key.py theme.py
```

**Step 3: Verify deletion**

Run: `ls -la *.py | grep -E "main|interface|chords|key|theme"`

Expected: No output (files gone)

**Step 4: Commit**

```bash
git add -A
git commit -m "chore: remove PyQt5 desktop UI code (main.py, interface.py, chords.py, key.py, theme.py)

refs: docs/plans/2026-03-09-desktop-app-cleanup.md"
```

---

### Task 2: Remove Desktop Build & Distribution Scripts

**Files:**
- Delete: `createLinuxShortcut.sh`
- Delete: `createWindowsShortcut.bat`
- Delete: `hideWindowsTerminal.vbs`

**Step 1: Verify these files are not referenced elsewhere**

Run: `grep -r "createLinuxShortcut\|createWindowsShortcut\|hideWindowsTerminal" . --include="*.md" --include="*.json" --include="*.py" 2>/dev/null | grep -v ".git"`

Expected: No matches outside docs (if any docs reference them, update them in next task)

**Step 2: Delete the files**

```bash
rm createLinuxShortcut.sh createWindowsShortcut.bat hideWindowsTerminal.vbs
```

**Step 3: Verify deletion**

Run: `ls -la | grep -E "Shortcut|Terminal"`

Expected: No output

**Step 4: Commit**

```bash
git add -A
git commit -m "chore: remove desktop build scripts (Linux/Windows shortcuts, Terminal hider)

refs: docs/plans/2026-03-09-desktop-app-cleanup.md"
```

---

### Task 3: Remove Desktop Icon Assets

**Files:**
- Delete: `icon` file

**Step 1: Verify `icon` is not referenced by web frontend**

Run: `grep -r "icon" frontend/ --include="*.tsx" --include="*.ts" --include="*.css" | head -20`

Expected: May have results (web icons), but NOT references to the top-level `icon` file. If found, confirm they point to `frontend/src/assets/` instead.

**Step 2: Check if `icon` is used by web backend**

Run: `grep -r "icon" backend/ --include="*.py"`

Expected: No matches, or matches that don't reference the top-level `icon` file

**Step 3: Delete icon file**

```bash
rm -f icon
```

**Step 4: Verify deletion**

Run: `ls -la | grep icon`

Expected: No output

**Step 5: Commit**

```bash
git add -A
git commit -m "chore: remove desktop icon assets

refs: docs/plans/2026-03-09-desktop-app-cleanup.md"
```

---

### Task 4: Remove Tracked `designs/` Directory And Keep Variant Design Directories

**Files:**
- Delete: `designs/` directory (entire)
- Keep: `designs.gpt54/` directory
- Keep: `designs.opus46/` directory

**Step 1: Verify retained design variant directories exist and `designs/` is already removed or ready to remove**

Run: `ls -ld designs designs.gpt54 designs.opus46 2>/dev/null`

Expected: `designs.gpt54/` and `designs.opus46/` exist. `designs/` may already be absent and appear in git status as tracked deletions.

**Step 2: Remove the tracked `designs/` directory**

```bash
rm -rf designs/
```

**Step 3: Verify retained directories remain**

Run: `ls -la designs* 2>/dev/null`

Expected: `designs.gpt54/` and `designs.opus46/` exist; `designs/` does not

**Step 4: Commit**

```bash
git add -A
git commit -m "chore: remove tracked designs directory and retain variant prototypes

refs: docs/plans/2026-03-09-desktop-app-cleanup.md"
```

---

### Task 5: Remove Source Export Artifacts

**Files:**
- Delete: `DeChord-source-code-chatgpt-2026-03-06.zip`
- Delete: `DeChord-source-code-only-2026-03-06.zip`
- Delete: `DeChord-source-no-deps-2026-03-06.zip`
- Delete: `DeChord-source-review.zip`
- Delete: `DeChord-source-review-latest.zip`

**Step 1: Verify these are not needed**

Run: `ls -lh DeChord-source*.zip`

Expected: List of zip files with dates

**Step 2: Delete all source export zips**

```bash
rm DeChord-source*.zip
```

**Step 3: Verify deletion**

Run: `ls -la *.zip 2>/dev/null`

Expected: No output (files gone)

**Step 4: Commit**

```bash
git add -A
git commit -m "chore: remove source code export artifacts

refs: docs/plans/2026-03-09-desktop-app-cleanup.md"
```

---

### Task 6: Remove Generated Report Artifacts

**Files:**
- Delete: `docs/reports/` generated files

**Step 1: Verify generated report artifacts exist**

Run: `find docs/reports -maxdepth 1 -type f | wc -l`

Expected: One or more generated report files

**Step 2: Remove generated report artifacts**

```bash
find docs/reports -maxdepth 1 -type f -delete
```

**Step 3: Verify cleanup**

Run: `find docs/reports -maxdepth 1 -type f`

Expected: No output

**Step 4: Commit**

```bash
git add -A
git commit -m "chore: remove generated report artifacts

refs: docs/plans/2026-03-09-desktop-app-cleanup.md"
```

---

## Git Configuration & Submodule Cleanup

### Task 7: Remove Demucs-Gui Submodule

**Files:**
- Delete: `Demucs-Gui/` directory
- Modify: `.gitmodules`
- Modify: `.git/config`

**Step 1: List current submodules**

Run: `git config --file=.gitmodules --name-only --get-regexp path`

Expected: Should list `Demucs-Gui` if it's a submodule

**Step 2: Check if Demucs-Gui is a submodule or regular directory**

Run: `git config --file=.gitmodules --get-regexp path | grep -i demucs`

If output shows `Demucs-Gui`, proceed with submodule removal. If no output, it's a regular directory; just delete it.

**Step 3a: Remove submodule (if it is one)**

```bash
git config --file=.gitmodules --remove-section submodule.Demucs-Gui
git config --file=.git/config --remove-section submodule.Demucs-Gui
rm -rf .git/modules/Demucs-Gui
rm -rf Demucs-Gui/
git add .gitmodules
```

**Step 3b: Remove regular directory (if not a submodule)**

```bash
rm -rf Demucs-Gui/
```

**Step 4: Verify removal**

Run: `cat .gitmodules`

Expected: Should not contain any `Demucs-Gui` references (file may be empty or removed)

**Step 5: Verify Demucs-Gui directory is gone**

Run: `ls -la | grep -i demucs`

Expected: No output

**Step 6: Commit**

```bash
git add -A
git commit -m "chore: remove Demucs-Gui submodule (desktop stem separation reference)

refs: docs/plans/2026-03-09-desktop-app-cleanup.md"
```

---

## Backend Dependency Audit & Cleanup

### Task 8: Audit Backend Dependencies in pyproject.toml

**Files:**
- Analyze: `backend/pyproject.toml`
- Modify: `backend/pyproject.toml` (if necessary)

**Step 1: Review current backend dependencies**

Run: `cat backend/pyproject.toml | grep -A 50 "dependencies = \[""`

Expected: List of dependencies with versions

**Step 2: Identify desktop/Demucs-only dependencies**

For each dependency, determine:
- Is it used by FastAPI backend? (Check `backend/` source code)
- Is it only for Demucs stem separation? (Desktop-only feature)
- Is it redundant or unused?

Common candidates to check:
- `librosa` - audio feature extraction (check if backend audio pipeline uses it)
- `scipy` - signal processing (likely used for DSP, keep)
- `soundfile` - audio file I/O (check backend usage)
- `pyaudio` - audio device enumeration (desktop-only, remove if present)
- `demucs` - stem separation library (likely desktop-only, check if backend uses it)

Run: `grep -r "import librosa\|from librosa\|import scipy\|from scipy\|import soundfile\|from soundfile\|import pyaudio\|import demucs" backend/src/ --include="*.py" | head -20`

Expected: See which dependencies are actually used

**Step 3: Document findings**

Create a comment in the plan:
```
Dependencies checked:
- librosa: [used/not used in backend]
- scipy: [used/not used in backend]
- soundfile: [used/not used in backend]
- pyaudio: [not present in pyproject.toml OR present but not used]
- demucs: [not present OR not used]
```

**Step 4: Remove unused dependencies (if any)**

If you identified unused dependencies, remove them from `backend/pyproject.toml`:

```python
# Remove lines like:
# "soundfile>=0.12.1",
# "pyaudio>=0.2.11",
```

**Step 5: Verify backend tests still pass**

Run: `cd backend && python -m pytest tests/ -v 2>&1 | head -50`

Expected: All tests pass (or same failures as before, if any)

**Step 6: Commit**

```bash
git add backend/pyproject.toml
git commit -m "chore: remove unused backend dependencies (desktop/Demucs-only packages)

Removed: [list of dependencies removed, or 'none' if none removed]

refs: docs/plans/2026-03-09-desktop-app-cleanup.md"
```

---

## Documentation Updates

### Task 9: Update README.md And Project Instructions

**Files:**
- Modify: `README.md`

**Step 1: Identify desktop-specific sections**

Run: `grep -n "PyQt5\|Desktop\|Demucs\|Windows\|Linux Shortcut\|Icon\|GUI" README.md | head -30`

Expected: Lines that reference desktop-only features

**Step 2: Review full README context**

Read the entire README to understand structure:

Run: `wc -l README.md`

Expected: Line count (likely 100-300 lines)

**Step 3: Rewrite README for web-only focus**

The README should now cover:
1. **What DeChord is:** Real-time music key/chord detection web application
2. **Features:** Key recognition, chord recognition, real-time display (web UI features only)
3. **Tech Stack:** FastAPI backend, React 19 + Vite frontend (NOT PyQt5)
4. **Installation:** Backend setup, frontend setup, Docker deployment
5. **Usage:** How to run web app locally, deploy to production
6. **Development:** Design iteration workflow (point to `designs/` directory)

Remove all references to:
- PyQt5
- Desktop GUI screenshots
- Windows/Linux shortcut creation
- Demucs stem separation (it's internal to backend, not user-facing)
- Desktop-specific installation instructions

Create new README structure:

```markdown
# DeChord - Real-Time Music Key and Chord Recognition

DeChord is a web-based music analysis tool that detects the musical key and chords in audio files in real-time. Built with FastAPI backend and React frontend for modern, responsive music analysis.

## Features

### Music Recognition
- **Key Detection:** Identifies the musical key using advanced CNN models
- **Chord Recognition:** Detects chords with precise timing
- **Real-Time Display:** Shows current, previous, and next chords as audio plays

### Audio Playback & Control
- Play/pause and seek controls
- Volume adjustment and mute
- Precise progress tracking

### User Interface
- Responsive web design
- Drag-and-drop audio file support
- Dark/light theme toggle
- Keyboard shortcuts for quick access

## Technology Stack

### Backend
- **Framework:** FastAPI (Python 3.13+)
- **Music Analysis:** madmom (CNN for chords/key, RNN for tempo/beats)
- **Audio Processing:** librosa, scipy

### Frontend
- **Framework:** React 19
- **Build Tool:** Vite
- **Styling:** Tailwind CSS v4
- **Language:** TypeScript

## Quick Start

### Prerequisites
- Python 3.13+
- Node.js 18+ / Bun
- FFmpeg (for audio file handling)

### Development Setup

**Backend:**
```bash
cd backend
pip install -r requirements.txt
python -m uvicorn main:app --reload
```

**Frontend:**
```bash
cd frontend
bun install
bun run dev
```

Visit `http://localhost:5173` in your browser.

### Production Deployment

See `Dockerfile` and `ops/` directory for deployment configurations.

## Design Prototypes

Design iterations are available in `designs/` directory. See `designs/README.md` for information about available prototypes.

## Development

All development is tracked in `docs/plans/`. See planning documents for current work and architecture decisions.

## License

[License info]
```

**Step 4: Replace README content**

Read existing README to preserve any important sections (license, acknowledgments, etc.), then write new version.

**Step 5: Verify README looks good**

Run: `cat README.md | head -80`

Expected: New web-focused content, no PyQt5/desktop references

**Step 6: Commit**

```bash
git add README.md
git commit -m "docs: rewrite README for web-only focus

- Remove all PyQt5 and desktop app references
- Update tech stack to focus on FastAPI + React
- Simplify installation and usage instructions
- Point to design prototypes in designs/ directory

refs: docs/plans/2026-03-09-desktop-app-cleanup.md"
```

---

### Task 9: Update docs/ Plans & Documentation Files

**Files:**
- Analyze: `docs/plans/` (all .md files)
- Modify: Any files mentioning desktop/PyQt5/Demucs GUI

**Step 1: Search for desktop references in docs**

Run: `grep -r "PyQt5\|desktop\|Demucs-Gui\|Electron\|shortcut" docs/ --include="*.md" 2>/dev/null`

Expected: List of files with desktop references

**Step 2: For each file found, update or remove references**

Review the context and:
- If mentioning old architecture, update to current web stack
- If referencing Demucs GUI, remove (it's internal to backend now)
- If referencing PyQt5 screenshots, remove

Common updates:
- Change "Desktop application built with PyQt5" → "Web application built with React"
- Remove screenshots of desktop UI
- Update architecture diagrams if they mention PyQt5

**Step 3: Commit**

```bash
git add docs/
git commit -m "docs: remove desktop app references from planning documents

- Update architecture descriptions to reflect web-only stack
- Remove references to Demucs-Gui and PyQt5
- Clarify that stem separation is internal backend feature

refs: docs/plans/2026-03-09-desktop-app-cleanup.md"
```

---

## Verification & Final Cleanup

### Task 10: Verify Complete Cleanup

**Step 1: Verify all desktop files are removed**

Run: `git status --short`

Expected: Clean working tree (no changes)

**Step 2: Search for any remaining desktop references in codebase**

Run: `grep -r "PyQt5\|interface\.py\|main\.py" . --include="*.py" --include="*.ts" --include="*.tsx" --include="*.md" 2>/dev/null | grep -v ".git" | grep -v ".venv" | grep -v "node_modules"`

Expected: No matches (clean codebase)

**Step 3: Verify no broken imports in backend**

Run: `cd backend && python -c "import sys; [__import__(f'src.{m}') for m in ['types', 'main']]" && echo "Imports OK"`

Expected: No import errors

**Step 4: Verify frontend builds**

Run: `cd frontend && bun run build 2>&1 | tail -20`

Expected: Build succeeds with no errors

**Step 5: Check git log for cleanup commits**

Run: `git log --oneline -10`

Expected: See 9 commits from this cleanup task

**Step 6: Final verification commit**

If all checks pass:

```bash
git log --oneline --all | head -20
```

Expected: See all cleanup commits listed

---

## Post-Cleanup Summary

After all tasks complete, the codebase will have:

✅ **Removed:**
- PyQt5 desktop UI code (5 files)
- Desktop build scripts (3 files)
- Desktop icon assets
- Old design iterations (2 directories)
- Source export artifacts (5 zip files)
- Demucs-Gui submodule
- Unused backend dependencies

✅ **Updated:**
- README.md (web-only focus)
- All documentation references
- Git configuration (no submodules)

✅ **Preserved:**
- `frontend/` (React/Vite web app)
- `backend/` (FastAPI API with madmom analysis)
- `designs/` (active design prototypes for implementation)
- `docs/plans/` (planning and architecture)
- `Dockerfile` and deployment config

**Result:** Clean, focused web-only codebase ready for design implementation.

---

## Handover Notes for Next Agent

- **Context:** This cleanup removes 15+ years of desktop app cruft to focus exclusively on web stack
- **Architecture:** FastAPI backend + React frontend + design system in `designs/`
- **Next Steps:** Implement one of the design prototypes from `designs/` directory
- **Key Files:**
  - Backend: `backend/src/main.py` (FastAPI app)
  - Frontend: `frontend/src/App.tsx` (React entry point)
  - Design system: `designs/README.md` (prototype descriptions)
  - Planning: `docs/plans/` (all development tracked here)
