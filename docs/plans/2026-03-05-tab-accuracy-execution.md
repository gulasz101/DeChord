# Tab Accuracy Execution Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Improve tab extraction reliability with measurable, non-regressing changes and artifacted evaluations.

**Architecture:** Keep `TabPipeline` as the production path, extend instrumentation and comparator metrics, then fix correctness issues in cleanup/onset interplay. Preserve API compatibility and AlphaTex output format.

**Tech Stack:** FastAPI backend, Python service modules, pytest, existing evaluation scripts.

---

- [x] Task 1: Establish canonical harness baseline artifacts (Phase 0)
- [x] Task 2: Add onset-only and octave-confusion metrics to comparator/harness (Phase 1A, 1B)
- [ ] Task 3: Add stage-attribution counters and debug JSON wiring (Phase 1C)
- [ ] Task 4: Fix second-pass cleanup kwargs reuse and add cleanup counters (Phase 2A)
- [ ] Task 5: Expose/enable onset recovery in production paths with tempo-adaptive params (Phase 2B)
- [ ] Task 6: Make repeated-note merge onset-aware and onset-tag aware (Phase 2C)
- [ ] Task 7: Run phased evaluations and write per-phase report artifacts/changelog
- [ ] Task 8: Run reset + verification test suite and final benchmark comparison
