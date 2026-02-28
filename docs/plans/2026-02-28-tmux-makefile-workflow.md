# Tmux Makefile Workflow Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Provide tmux-based single-session process management for backend/frontend via Makefile targets such as `backend-up` and `backend-attach`.

**Architecture:** Extend the root Makefile with idempotent tmux session lifecycle targets per service (backend/frontend), plus aggregate targets for full stack management. Preserve existing install/test workflow while routing runtime commands through tmux.

**Tech Stack:** GNU Make, tmux, FastAPI/uv, Bun/Vite

---

## Task 1: Define tmux target surface and conventions

- [x] Step 1: Create plan file and document requested target naming
- [x] Step 2: Commit

## Task 2: Add tmux-backed Makefile targets

- [ ] Step 1: Red phase - verify missing targets fail
- [ ] Step 2: Green phase - implement `backend-up/backend-attach/backend-down/backend-status/backend-logs`
- [ ] Step 3: Green phase - implement `frontend-up/frontend-attach/frontend-down/frontend-status/frontend-logs`
- [ ] Step 4: Green phase - implement aggregate targets (`up`, `down`, `status`, `logs`) and keep `dev/backend/frontend` compatible
- [ ] Step 5: Verify with `make -n` and targeted runtime status checks
- [ ] Step 6: Commit

## Task 3: Final verification and progress reflection

- [ ] Step 1: Validate no duplicate session creation behavior
- [ ] Step 2: Mark plan tasks complete
- [ ] Step 3: Commit

## Notes

- True subagent dispatch is not available in this runtime; execution follows subagent-style phases with explicit TDD red/green checkpoints.
