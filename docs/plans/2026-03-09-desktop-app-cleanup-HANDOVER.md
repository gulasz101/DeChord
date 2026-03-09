# Desktop App Cleanup - Comprehensive Handover for Fresh Agent

## Executive Summary

You are receiving a **complete, pre-planned cleanup task** for the DeChord music analysis application. The task is to remove all desktop application code, build artifacts, and dependencies to establish a clean, web-only codebase. This is a prerequisite for future design implementation work.

**Status:** Planning complete, design approved. Ready for execution.
**Complexity:** Medium (10 discrete tasks, no coding required, mostly file/config removal)
**Estimated Duration:** 2-3 hours for careful, methodical execution
**Success Criteria:** All 10 tasks completed, all verifications pass, codebase in clean state

---

## Project Context: DeChord

### What Is DeChord?

DeChord is a web-based music analysis application that detects the musical key and chords in audio files in real-time. It's being rebuilt as a modern web application after being a desktop application.

### Current Architecture (What You're Cleaning)

**BEFORE cleanup (messy state):**
- Desktop app code: PyQt5-based GUI (Python)
- Backend: FastAPI + madmom (CNN/RNN music analysis)
- Frontend: React 19 + Vite (modern web UI)
- Build artifacts: Export zips, old designs, desktop shortcuts
- Submodules: Demucs-Gui (external stem separation, desktop reference)
- Dependencies: Mixed desktop + web requirements

**AFTER cleanup (target state):**
- Backend: FastAPI only (Python 3.13+)
- Frontend: React 19 + Vite + Tailwind CSS v4
- Designs: Isolated in `designs/` directory (for future implementation)
- No desktop code, no build artifacts, no unused dependencies
- Clean git history with discrete cleanup commits

### Why This Cleanup Matters

1. **Confusion Prevention:** New agents won't wonder why PyQt5 code exists in a web project
2. **Dependency Clarity:** No ambiguity about what's actually needed for the web app
3. **Clean Foundation:** Ready to implement one of the design prototypes without baggage
4. **Maintainability:** Smaller, focused codebase is easier to understand and modify

### Tech Stack (Post-Cleanup)

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | React 19 | User interface |
| **Build** | Vite | Frontend bundling |
| **Styling** | Tailwind CSS v4 | UI styling |
| **Language (Frontend)** | TypeScript | Type-safe JavaScript |
| **Backend** | FastAPI | REST API server |
| **Analysis** | madmom (CNN/RNN) | Music key/chord detection |
| **Language (Backend)** | Python 3.13+ | Backend logic |
| **Deployment** | Docker | Containerization |

---

## The Cleanup Task: 10 Discrete Steps

### Overview of Tasks

Your job is to execute the **pre-written plan** in: `/docs/plans/2026-03-09-desktop-app-cleanup.md`

That document contains:
- **Task 0:** Inventory & planning (understanding scope)
- **Task 1:** Remove PyQt5 desktop UI code (5 Python files)
- **Task 2:** Remove desktop build scripts (3 shell/batch files)
- **Task 3:** Remove desktop icon assets
- **Task 4:** Remove old design directories
- **Task 5:** Remove source export artifacts (zip files)
- **Task 6:** Remove Demucs-Gui submodule & git config
- **Task 7:** Audit & cleanup backend dependencies
- **Task 8:** Update README.md
- **Task 9:** Update documentation references
- **Task 10:** Final verification & summary

Each task includes:
- **Files:** Exact paths (create, modify, delete)
- **Steps:** Numbered sub-steps with exact bash commands
- **Verification:** Expected outputs to confirm success
- **Commit:** Exact commit message with plan reference

---

## Before You Start: Critical Preparation

### 1. Understand the Current State

Run these commands to see what you're working with:

```bash
# See the desktop files that will be removed
ls -la main.py interface.py chords.py key.py theme.py 2>/dev/null

# See the desktop build scripts
ls -la createLinuxShortcut.sh createWindowsShortcut.bat hideWindowsTerminal.vbs 2>/dev/null

# See the old design directories
ls -la designs.* 2>/dev/null

# See the Demucs-Gui submodule/directory
ls -la Demucs-Gui/ 2>/dev/null | head -10

# See git submodules
cat .gitmodules 2>/dev/null || echo "No .gitmodules file"

# See source export artifacts
ls -la *.zip 2>/dev/null
```

**What you should see:**
- 5 Python files (main.py, interface.py, etc.)
- 3 shell/batch scripts
- icon/ directory
- designs.gpt54/ and designs.opus46/ directories
- Demucs-Gui/ directory
- 5 zip files
- Possibly a .gitmodules file with Demucs-Gui submodule

If files are missing, that's OK—they may have already been removed. Proceed with tasks and skip removal steps for files that don't exist.

### 2. Verify You Have the Right Branch

```bash
git branch
git status
```

**Expected:**
- On `main` branch (or working branch)
- Working tree clean (no uncommitted changes)
- All local changes committed

If not clean, ask before proceeding. This task should start from a clean state.

### 3. Read the Full Plan Document

Open: `/docs/plans/2026-03-09-desktop-app-cleanup.md`

Read **carefully**:
- Understand the overall flow (Tasks 0-10)
- Note the verification steps in Task 10
- Understand what files are being removed and why
- See the commit messages you'll be writing

### 4. Understand the Safety Model

**Before executing each task:**
1. Read the task fully (don't skip steps)
2. Run verification commands FIRST (see what exists)
3. Execute removal/modification commands
4. Run post-verification commands (confirm success)
5. Commit with exact message from plan
6. Do NOT proceed to next task until current task is committed

**Why this matters:**
- Verification prevents accidents (e.g., deleting wrong files)
- Commits create checkpoints (can revert if needed)
- Discrete commits = clean git history = easy to trace what happened

---

## How to Execute the Plan

### Execution Method 1: Step-by-Step (Safest)

For each task in the plan (starting with Task 1):

1. **Read the task section** in `/docs/plans/2026-03-09-desktop-app-cleanup.md`
2. **Run all "Step 1" sub-steps** (usually verification):
   - Copy the exact command from the plan
   - Paste into terminal
   - Note the expected output
   - Compare actual vs. expected
   - If unexpected, STOP and investigate
3. **Run Step 2, Step 3, etc.** in order
4. **Run the commit** at the end of the task
5. **Move to next task** only after commit succeeds

### Execution Method 2: Using executing-plans Skill

In your new session, you can invoke:

```
Use superpowers:executing-plans to implement this plan task-by-task with checkpoints.
```

This will:
- Load the plan document
- Dispatch subagents per task
- Get code review between tasks
- Ensure nothing is missed

**If using this method:** Still read this handover document first for context.

---

## Key Decisions & Rationale

### Why Remove These Files?

| File(s) | Why Remove | Impact |
|---------|-----------|--------|
| `main.py`, `interface.py`, `chords.py`, `key.py`, `theme.py` | PyQt5 desktop UI code not used by web app | None; web app doesn't use these |
| `createLinuxShortcut.sh`, etc. | Desktop-only distribution scripts | Web app doesn't need desktop shortcuts |
| `icon/` | Desktop app icon assets | Web app uses `frontend/src/assets/` for icons |
| `designs.gpt54/`, `designs.opus46/` | Old design iterations; `designs/` is active | `designs/` will be used for implementation |
| `DeChord-source-*.zip` | Export artifacts, not part of codebase | These are backups, not needed in repo |
| `Demucs-Gui/` submodule | External stem separation reference (desktop-only) | Backend has stem separation built-in |
| Unused backend deps | Dependencies only for Demucs desktop app | Not needed for web backend |

### Why Keep These Files?

| Directory/File | Why Keep | Usage |
|---|---|---|
| `frontend/` | React/Vite web application | User-facing web UI |
| `backend/` | FastAPI REST API + madmom analysis | Core music analysis engine |
| `designs/` | Active design prototypes | Next phase: implement one design |
| `docs/plans/` | Planning & architecture documents | Development tracking |
| `Dockerfile` | Container configuration | Production deployment |
| `.github/` | GitHub workflows (if present) | CI/CD pipeline |

---

## Detailed Task Walkthrough: First 3 Tasks (Examples)

To show you what execution looks like, here's the detail for the first few tasks:

### Task 1: Remove PyQt5 Desktop UI Code

**What you're removing:** 5 Python files that were generated from Qt Designer (old PyQt5 desktop UI)

**Files to delete:**
```
main.py
interface.py
chords.py
key.py
theme.py
```

**Execution:**

```bash
# Step 1: Verify these files exist and are not imported by web app
grep -r "import main\|from main\|import interface\|from interface\|import chords\|from chords\|import key\|from key\|import theme\|from theme" frontend/ backend/ --include="*.py" --include="*.ts" --include="*.tsx"
```

**Expected output:** No matches (these files are not used by frontend or backend)

If you get matches, STOP. Something unexpected. Investigate before deleting.

```bash
# Step 2: Delete the files
rm main.py interface.py chords.py key.py theme.py

# Step 3: Verify they're gone
ls -la *.py | grep -E "main|interface|chords|key|theme"
```

**Expected output:** No output (files successfully deleted)

```bash
# Step 4: Commit
git add -A
git commit -m "chore: remove PyQt5 desktop UI code (main.py, interface.py, chords.py, key.py, theme.py)

refs: docs/plans/2026-03-09-desktop-app-cleanup.md"
```

**Expected output:** Commit message showing 5 files deleted

---

### Task 2: Remove Desktop Build Scripts

**What you're removing:** Shell scripts and batch files for creating desktop shortcuts

**Files to delete:**
```
createLinuxShortcut.sh
createWindowsShortcut.bat
hideWindowsTerminal.vbs
```

**Execution:**

```bash
# Step 1: Verify these files are not referenced elsewhere
grep -r "createLinuxShortcut\|createWindowsShortcut\|hideWindowsTerminal" . --include="*.md" --include="*.json" --include="*.py" 2>/dev/null | grep -v ".git"
```

**Expected output:** No matches (these files are not referenced)

If you get matches, update those docs first before deleting.

```bash
# Step 2: Delete
rm createLinuxShortcut.sh createWindowsShortcut.bat hideWindowsTerminal.vbs

# Step 3: Verify
ls -la | grep -E "Shortcut|Terminal"
```

**Expected output:** No output (files gone)

```bash
# Step 4: Commit
git add -A
git commit -m "chore: remove desktop build scripts (Linux/Windows shortcuts, Terminal hider)

refs: docs/plans/2026-03-09-desktop-app-cleanup.md"
```

---

### Task 6: Remove Demucs-Gui Submodule (Most Complex)

**What you're removing:** An external git submodule for stem separation (used as reference in old desktop app)

**Why it's complex:** Git submodules require special handling to avoid leaving dangling references

**Execution:**

```bash
# Step 1: Check if Demucs-Gui is actually a submodule
git config --file=.gitmodules --name-only --get-regexp path
```

**Expected output:** May show `submodule.Demucs-Gui.path = Demucs-Gui` or no output if not a submodule

**Case A: It IS a submodule**

```bash
# Remove from .gitmodules
git config --file=.gitmodules --remove-section submodule.Demucs-Gui

# Remove from .git/config
git config --file=.git/config --remove-section submodule.Demucs-Gui

# Remove cached submodule
rm -rf .git/modules/Demucs-Gui

# Remove the directory itself
rm -rf Demucs-Gui/

# Stage the .gitmodules change
git add .gitmodules
```

**Case B: It's just a regular directory**

```bash
# Just delete it
rm -rf Demucs-Gui/
```

**Verify:**
```bash
cat .gitmodules  # Should not contain Demucs-Gui or be empty
ls -la | grep -i demucs  # Should show nothing
```

**Commit:**
```bash
git add -A
git commit -m "chore: remove Demucs-Gui submodule (desktop stem separation reference)

refs: docs/plans/2026-03-09-desktop-app-cleanup.md"
```

---

## Task 7 Deep Dive: Backend Dependency Audit

This is the most analytical task. You need to determine which dependencies to keep.

### Strategy

1. **List all current dependencies:**
   ```bash
   cat backend/pyproject.toml | grep -A 50 "dependencies ="
   ```

2. **For EACH dependency, ask:**
   - Is it imported in `backend/src/` code?
   - Is it only for Demucs stem separation (desktop feature)?
   - Is it actually used, or a leftover?

3. **Search for usage:**
   ```bash
   grep -r "import librosa\|from librosa" backend/src/ --include="*.py"
   grep -r "import scipy\|from scipy" backend/src/ --include="*.py"
   # ... etc for each library
   ```

4. **Common candidates to remove:**
   - `pyaudio` - audio device enumeration (desktop only)
   - `demucs` - if it's in requirements (stem separation, internal to backend)
   - `pydub` - if not used by backend
   - `pygame` - definitely desktop-only

5. **Edit `backend/pyproject.toml`:**
   Remove lines for unused dependencies (keep others)

6. **Test:**
   ```bash
   cd backend && python -m pytest tests/ -v
   ```
   Make sure tests still pass

---

## Task 8 Deep Dive: Update README.md

The current README has screenshots of the old PyQt5 desktop UI and desktop-only features. You'll rewrite it to describe the web application.

### What to Remove from Current README

Look for and delete:
- Screenshots of desktop UI
- References to "PyQt5", "Qt", "Desktop"
- Windows/Linux shortcut installation instructions
- Demucs GUI references
- Desktop-specific system requirements
- PyQt5 library documentation

### What to Add to New README

The plan includes a template. You'll write:
1. What DeChord is (web music analysis)
2. Features (chord detection, real-time display, web UI)
3. Tech stack (FastAPI, React, Tailwind)
4. Quick start (backend setup, frontend setup, local development)
5. Production deployment
6. Design prototypes reference
7. Development workflow reference

See the **exact template** in `/docs/plans/2026-03-09-desktop-app-cleanup.md` under Task 8, Step 3.

---

## Task 10: Final Verification Checklist

Before you're done, run these verifications:

```bash
# 1. Check git status is clean
git status --short
# Expected: Clean working tree

# 2. Verify no desktop code remains
grep -r "PyQt5\|interface\.py\|main\.py" . --include="*.py" --include="*.ts" --include="*.tsx" --include="*.md" 2>/dev/null | grep -v ".git" | grep -v ".venv" | grep -v "node_modules" | grep -v "__pycache__"
# Expected: No matches

# 3. Verify backend imports still work
cd backend && python -c "import sys; [__import__(f'src.{m}') for m in ['types', 'main']]" && echo "✓ Imports OK"
# Expected: ✓ Imports OK (no errors)

# 4. Verify frontend builds
cd frontend && bun run build 2>&1 | tail -20
# Expected: Build succeeds

# 5. Check cleanup commits
git log --oneline | head -15
# Expected: See all your cleanup commits
```

If all checks pass: ✓ **Task complete, cleanup successful**

---

## Commit Message Conventions

All commits in this task follow a pattern:

```
chore: [what was removed/changed]

[optional: details about why or what changed]

refs: docs/plans/2026-03-09-desktop-app-cleanup.md
```

**Examples:**

```
chore: remove PyQt5 desktop UI code (main.py, interface.py, chords.py, key.py, theme.py)

refs: docs/plans/2026-03-09-desktop-app-cleanup.md
```

```
docs: rewrite README for web-only focus

- Remove all PyQt5 and desktop app references
- Update tech stack to focus on FastAPI + React
- Simplify installation and usage instructions
- Point to design prototypes in designs/ directory

refs: docs/plans/2026-03-09-desktop-app-cleanup.md
```

**Key point:** Every commit must reference the plan file: `refs: docs/plans/2026-03-09-desktop-app-cleanup.md`

---

## Safety Guardrails

### What NOT to Do

❌ **Don't skip verification steps** - Always run "Step 1" verification before deleting anything

❌ **Don't delete multiple files without confirming each** - Even if the script says delete 5 files, verify each one first

❌ **Don't commit multiple tasks together** - Each task = one commit. No combining tasks.

❌ **Don't modify the plan document** - Refer to it, don't edit it. If something is wrong, note it and ask.

❌ **Don't skip git commands** - Use exact commit messages from the plan. This creates traceable history.

❌ **Don't assume files exist** - If a file isn't there, skip that deletion step. Proceed with next task.

### What TO Do

✅ **Read every step before executing** - Plan is detailed. Don't skim.

✅ **Run verifications first** - See what exists before touching anything

✅ **Test as you go** - After each task, verify it worked

✅ **Commit frequently** - Each task = one commit, 10 tasks = 10 commits

✅ **Document unusual findings** - If something is different than expected, make a note and continue

✅ **Ask questions** - If something doesn't make sense, ask before proceeding

---

## If Something Goes Wrong

### Scenario: File doesn't exist, but plan says to delete it

**Response:** Skip that deletion step. Proceed to next step. It may have already been deleted.

### Scenario: Verification output doesn't match expected

**Response:** STOP. Don't proceed to next step. Review:
1. Did you run the exact command from the plan?
2. Did you copy-paste correctly?
3. Is the output actually unexpected, or just formatted differently?

If still unclear, ask before proceeding.

### Scenario: Git commit fails

**Response:** Read the error message carefully. Common issues:
- Pre-commit hook failure: Fix the issue, re-stage files, create new commit
- No changes to commit: Files may have already been removed
- Merge conflict: Shouldn't happen, but if it does, resolve and commit

### Scenario: Backend tests fail after Task 7

**Response:** You may have removed a dependency that's actually needed. Review what you removed:
1. Check git diff to see which dependencies were removed
2. Re-add them to `backend/pyproject.toml`
3. Re-run tests
4. Update commit message with the change

---

## File Reference Map

To help you navigate, here's what's in each directory:

```
DeChord/
├── main.py                          ← REMOVE (Task 1)
├── interface.py                     ← REMOVE (Task 1)
├── chords.py                        ← REMOVE (Task 1)
├── key.py                           ← REMOVE (Task 1)
├── theme.py                         ← REMOVE (Task 1)
├── createLinuxShortcut.sh           ← REMOVE (Task 2)
├── createWindowsShortcut.bat        ← REMOVE (Task 2)
├── hideWindowsTerminal.vbs          ← REMOVE (Task 2)
├── icon/                            ← REMOVE (Task 3)
├── designs.gpt54/                   ← REMOVE (Task 4)
├── designs.opus46/                  ← REMOVE (Task 4)
├── designs/                         ← KEEP (for future implementation)
├── Demucs-Gui/                      ← REMOVE (Task 6)
├── DeChord-source-*.zip             ← REMOVE (Task 5)
├── README.md                        ← UPDATE (Task 8)
├── AGENTS.md / CLAUDE.md            ← Reference these for rules
├── .gitmodules                      ← UPDATE (Task 6)
├── backend/                         ← KEEP, UPDATE deps (Task 7)
│   ├── pyproject.toml              ← AUDIT & CLEANUP deps (Task 7)
│   ├── src/
│   │   └── main.py                 ← Keep (FastAPI app)
│   └── tests/
├── frontend/                        ← KEEP (React web app)
│   ├── package.json
│   ├── vite.config.ts
│   ├── src/
│   │   ├── App.tsx
│   │   └── assets/                 ← Web icons (keep these)
├── docs/
│   ├── plans/
│   │   ├── 2026-03-09-desktop-app-cleanup.md          ← THE PLAN
│   │   ├── 2026-03-09-desktop-app-cleanup-HANDOVER.md ← THIS FILE
│   │   └── [other planning docs]                       ← Update if needed
└── Dockerfile                       ← KEEP (deployment)
```

---

## Success Criteria & Verification

### Task Complete When:

1. ✅ All 10 tasks executed (or skipped if files don't exist)
2. ✅ 9+ commits created (one per task)
3. ✅ All commits reference the plan document
4. ✅ `git status --short` shows clean working tree
5. ✅ No PyQt5/desktop references in codebase
6. ✅ Backend imports work
7. ✅ Frontend builds successfully
8. ✅ README.md updated with web-only content
9. ✅ All documentation references cleaned

### Post-Cleanup State:

**Removed (confirmed gone):**
- 5 Python desktop UI files
- 3 desktop build scripts
- icon/ directory
- 2 old design directories
- 5 source export zips
- Demucs-Gui submodule/directory
- Unused backend dependencies (if any)

**Updated:**
- README.md (web-focused)
- Documentation references
- Git configuration

**Preserved:**
- frontend/, backend/, designs/ directories
- All source code for web app
- All planning documents
- Dockerfile, deployment config

---

## How to Reach Out If Stuck

If you encounter issues:

1. **Re-read the relevant task section** in the plan document
2. **Check this handover** for common scenarios (see "If Something Goes Wrong")
3. **Ask specific questions** with:
   - Exact command you ran
   - Exact error/output you got
   - What step in the plan you're on

Example:
> "I'm on Task 7, Step 2. When I ran `grep -r "import librosa"...` it returned matches. What should I do? Remove librosa or keep it?"

---

## Next Steps After Cleanup

Once you finish this cleanup task:

1. **Handoff:** Summarize what was removed and point to clean codebase
2. **Next Phase:** Next agent will implement one of the designs from `designs/` directory
3. **Planning:** That agent will use `docs/plans/` to track implementation work

The cleanup creates the **foundation** for the implementation phase.

---

## Document References

**You'll need these while working:**

1. **Plan:** `/docs/plans/2026-03-09-desktop-app-cleanup.md` (10 tasks with exact commands)
2. **This file:** `/docs/plans/2026-03-09-desktop-app-cleanup-HANDOVER.md` (context & safety)
3. **Project rules:** `/CLAUDE.md` (development method, commit rules)
4. **Project memory:** `.claude/projects/-Users-wojciechgula-Projects-DeChord/memory/MEMORY.md` (preferences & conventions)

**Read them in this order:**
1. This handover (what you're doing now)
2. The plan document (exact steps)
3. CLAUDE.md (how to work here)
4. Reference MEMORY.md if unsure about conventions

---

## Final Words

This is a **straightforward cleanup task** with a **detailed, pre-written plan**. You have everything you need:

- ✅ Clear goal: Remove desktop app artifacts
- ✅ Detailed plan: 10 tasks with exact commands
- ✅ Safety checks: Verification steps before/after each action
- ✅ Commit discipline: One commit per task
- ✅ This handover: Context and guardrails

**Execute methodically, verify frequently, commit discretely.**

The cleanup removes confusion and establishes a clean foundation for the next phase of development.

Good luck! 🎵
