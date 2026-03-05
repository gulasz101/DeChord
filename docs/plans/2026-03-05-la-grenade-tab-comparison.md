# La grenade Tab Comparison Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Compare DeChord generated bass tab for "La grenade" against the official transcription PDF and produce a bar-level alignment report.

**Architecture:** Build a reproducible comparison workflow: fetch/load official PDF, run backend TabPipeline with `high_accuracy_aggressive`, parse both official and generated representations into bar-level note counts/pitches when feasible, compute metrics, and write a Markdown report with diagnostics.

**Tech Stack:** Python (`pdfplumber`, `PyPDF2`, backend services), Markdown reporting, shell tooling.

---

- [x] Task 1: Acquire official PDF in workspace and validate that it is readable for extraction.
- [ ] Task 2: Run DeChord pipeline on `backend/stems/la_grenade_e2e` with `high_accuracy_aggressive` and capture diagnostics + AlphaTex output.
- [ ] Task 3: Normalize official and generated bar-level representations and compute comparison metrics.
- [ ] Task 4: Write `la_grenade_tab_comparison.md` with overview, metrics table, highlights, observations, and conclusion.
- [ ] Task 5: Run required reset and final verification from a fresh local state.
