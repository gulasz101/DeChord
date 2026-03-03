# Stem Separation Demucs Env Configuration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make Demucs stem separation parameters configurable via environment variables (including `.env`) using defaults matching the provided Demucs GUI screenshot, with CPU-friendly host control and documented configuration.

**Architecture:** Introduce a typed config layer in `backend/app/stems.py` that loads env values (including `.env`), applies parameter validation/defaults, and routes those values into Demucs separator runtime (`device`, `segment`, `overlap`, `shifts`) plus gain processing (`input_gain_db`, `output_gain_db`). Keep backend API contract unchanged.

**Tech Stack:** Python 3.13+, FastAPI, Demucs, PyTorch, Pytest

---

### Task 1: Add and commit this plan file

**Files:**
- Create: `docs/plans/2026-03-03-stems-demucs-env-config-implementation.md`

- [x] Step 1: Create plan file with all tasks initially unchecked.
- [x] Step 2: Commit with message referencing this plan path.

### Task 2: Document stem env configuration in README

**Files:**
- Modify: `README.md`

- [x] Step 1: Add `Stem Separation Configuration (Environment)` section listing all supported backend env variables and defaults.
- [x] Step 2: Include `.env` usage example for local laptop tinkering and Linux host CPU deployment example.
- [x] Step 3: Commit with message referencing this plan path.

### Task 3: Add RED tests for configurable Demucs params and defaults (TDD)

**Files:**
- Modify: `backend/tests/test_stems.py`

- [ ] Step 1: Add failing tests asserting screenshot defaults (`segment=7.8`, `overlap=0.25`, `shifts=0`, gains `0.0`, device auto).
- [ ] Step 2: Add failing tests for env overrides, including forced CPU and `.env` loading behavior.
- [ ] Step 3: Run `cd backend && uv run pytest tests/test_stems.py -q` and confirm RED.
- [ ] Step 4: Commit RED tests with plan reference.

### Task 4: Implement env/.env-driven stem parameter logic (GREEN)

**Files:**
- Modify: `backend/app/stems.py`
- Modify: `backend/pyproject.toml`

- [ ] Step 1: Add `.env` loading support and typed env parsing helpers.
- [ ] Step 2: Apply configurable `device`, `segment`, `overlap`, `shifts`, `input_gain_db`, `output_gain_db` in Demucs path.
- [ ] Step 3: Preserve existing engine/fallback behavior and update logs for effective runtime config.
- [ ] Step 4: Run `cd backend && uv run pytest tests/test_stems.py -q` and confirm GREEN.
- [ ] Step 5: Commit implementation with plan reference.

### Task 5: Verify end-to-end backend test gate and reset workflow

**Files:**
- Modify: `docs/plans/2026-03-03-stems-demucs-env-config-implementation.md`

- [ ] Step 1: Run `cd backend && uv run pytest tests/ -q`.
- [ ] Step 2: Run `make reset` before final handoff.
- [ ] Step 3: Mark all plan steps complete and commit with plan reference.

---

## Notes

- Subagent-driven development was requested. Dedicated subagent tool dispatch is unavailable in this execution environment, so this plan uses strict per-task isolation, TDD sequencing, and explicit review checkpoints in a single agent flow.
