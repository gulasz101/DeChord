# Portless Local Dev Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make local DeChord web app development use Portless stable hostnames so frontend/backend startup avoids port collisions.

**Architecture:** Route both frontend and backend dev servers through Portless names (`dechord`, `api.dechord`), update Vite proxy target to the backend Portless host, and switch Makefile local startup commands to Portless wrappers while preserving tmux lifecycle controls.

**Tech Stack:** Vite 7, React 19, FastAPI dev server, Makefile/tmux, Portless CLI

---

### Task 1: Lock Vite proxy to Portless backend [x]

**Files:**
- Create: `frontend/vite.config.test.ts`
- Modify: `frontend/vite.config.ts`

- [x] Step 1: Write a failing test in `frontend/vite.config.test.ts` asserting `/api` proxy target is `http://api.dechord.localhost:1355`.
- [x] Step 2: Run `cd frontend && bun run test -- vite.config.test.ts` and confirm failure.
- [x] Step 3: Update `frontend/vite.config.ts` proxy target from localhost backend port to Portless backend hostname.
- [x] Step 4: Re-run `cd frontend && bun run test -- vite.config.test.ts` and confirm pass.
- [x] Step 5: Commit with message referencing this plan path and task number.

### Task 2: Switch Makefile dev commands to Portless wrappers [x]

**Files:**
- Modify: `Makefile`

- [x] Step 1: Add a failing Makefile validation check via `make -n up | rg portless` expectation script (recorded command evidence in execution notes).
- [x] Step 2: Update backend/frontend command variables to run under `portless api.dechord` and `portless dechord`.
- [x] Step 3: Ensure backend command consumes `PORT` and `HOST` env vars if injected by Portless.
- [x] Step 4: Add `portless-proxy-up`, `portless-proxy-down`, and `portless-routes` targets for explicit proxy lifecycle/inspection.
- [x] Step 5: Re-run `make -n up` and `make -n portless-routes` to confirm commands are wired.
- [x] Step 6: Commit with message referencing this plan path and task number.

### Task 3: Update docs and run full verification [x]

**Files:**
- Modify: `README.md`
- Modify: `docs/plans/2026-03-03-portless-dev-implementation.md`

- [x] Step 1: Update local-start README section with Portless prerequisite and stable URLs.
- [x] Step 2: Replace outdated localhost links in web app startup documentation block.
- [x] Step 3: Run required reset workflow: `make reset`.
- [x] Step 4: Run verification commands:
  - `cd backend && uv run pytest tests/ -v`
  - `cd frontend && bun run test`
  - `cd frontend && bun run build`
- [x] Step 5: Mark all completed tasks in this plan file as `[x]`.
- [x] Step 6: Commit with message referencing this plan path and task number.
