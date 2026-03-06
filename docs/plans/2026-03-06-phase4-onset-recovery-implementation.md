# Phase 4 Onset Recovery Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Recover Hysteria onset recall with minimal, evidence-driven intervention while preserving Phase 3 pitch gains.

**Architecture:** Extend deterministic evaluation tooling to produce stage-wise attribution across pipeline stages, then implement one narrow dense-bar-aware fix at the measured bottleneck (if downstream), and finally run canonical benchmark comparisons with explicit path arguments.

**Tech Stack:** Python 3.14, existing tab pipeline services, pytest, uv, make.

---

- [x] Task 1: Add deterministic Phase 4 stage-attribution reporting (JSON/Markdown artifacts + Hysteria worst-bars analysis) and phase-aware output naming in the evaluation harness.
- [ ] Task 2: Implement one narrow fix at the measured bottleneck stage (with TDD and dense-bar/repeated-note protection if justified by attribution evidence).
- [ ] Task 3: Run reset + targeted/full verification, execute canonical Hysteria/Trooper evaluations, generate Phase 4 report artifacts, and finalize plan checkboxes.
