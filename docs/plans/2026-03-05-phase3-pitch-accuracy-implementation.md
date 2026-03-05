# Phase 3 Pitch Accuracy Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Improve pitch accuracy and octave stability in transcription while keeping pipeline structure unchanged.

**Architecture:** Implement aggressive fallback improvements in `app/midi.py`, conservative BasicPitch post-parse correction in `bass_transcriber.py`, and deterministic transcription audit/reporting in `evaluate_tab_quality.py`. Validate with deterministic song-pair benchmarks.

**Tech Stack:** Python 3.14, librosa/scipy/numpy, pytest, existing evaluation harness.

---

- [x] Task 1: Add MIDI transcription result metadata plumbing (`engine`, diagnostics) without breaking existing API.
- [x] Task 2: Implement fallback framewise pitch smoothing + spectral octave verification + sequence stabilization.
- [x] Task 3: Add conservative BasicPitch post-parse octave stabilization with strict guardrails.
- [ ] Task 4: Add transcription audit output and pitch error counters in evaluation script.
- [ ] Task 5: Add/extend unit tests for fallback logic, BasicPitch correction, and evaluation diagnostics.
- [ ] Task 6: Produce baseline/final benchmark artifacts for Muse and Trooper and phase summary report.
- [ ] Task 7: Run `make reset`, run pytest, and finalize verification outputs.
