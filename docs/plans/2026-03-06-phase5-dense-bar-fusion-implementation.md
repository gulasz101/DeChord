# Phase 5 Dense-Bar Fusion Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Preserve Phase 4 onset gains while recovering pitch stability by confidence-gating dense-bar second-pass rescue note fusion.

**Architecture:** Add candidate-level fusion diagnostics in `TabPipeline`, implement a confidence gate that prefers rescue timing with stable contextual pitch, and add repeated-note dense-bar mode with bar-local guardrails. Validate using deterministic Hysteria/Trooper evaluations and produce required debug/report artifacts.

**Tech Stack:** Python 3.14, pytest, uv, existing DeChord tab pipeline/evaluation scripts, make.

---

- [x] Task 1: Instrument dense-bar fusion candidate diagnostics and export Phase 5 fusion debug artifacts for Hysteria/Trooper plus summary report.
- [ ] Task 2: Implement confidence-gated dense-bar rescue fusion (including repeated-note mode and timing-preserving pitch normalization) with TDD coverage.
- [ ] Task 3: Run reset + targeted/full verification, execute deterministic Phase 5 evaluations for both songs, generate final comparison report, and mark plan complete.
