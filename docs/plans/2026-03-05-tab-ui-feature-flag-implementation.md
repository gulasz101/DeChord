# Tab UI Feature Flag Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Hide all tab-generation related UI behind a default-off frontend feature flag while preserving existing code.

**Architecture:** Introduce centralized frontend feature flag helper (`VITE_ENABLE_TABS_UI`, default off) and gate tab UI rendering plus tab metadata loading. Keep upload behavior functional with default tab quality when UI is disabled.

**Tech Stack:** React 19, TypeScript, Vite, Vitest.

---

- [x] Task 1: Add/adjust ignore rules so local noise files are not tracked while keeping `AGENTS.md` tracked.
- [x] Task 2: Add failing tests for default-hidden tab UI behavior.
- [x] Task 3: Implement feature-flag gating across app/upload UI.
- [x] Task 4: Run frontend verification + `make reset`, update plan statuses, and commit final verification changes.
- [x] Task 5: Ignore local `test songs/` assets so working tree stays clean for merge operations.

## Verification Evidence
- `make reset` (from repo root) completed successfully and reset local runtime/db state.
- `cd frontend && npm test` passed: `16` files, `49` tests, `0` failures.
