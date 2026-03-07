# Phase 6 Upstream Hybrid Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a targeted dense-note generator and pre-cleanup hybrid fusion path that improves dense bass transcription hypotheses while preserving the existing downstream pipeline.

**Architecture:** Introduce a lightweight audio-derived dense-note candidate generator, fuse it with BasicPitch raw notes before cleanup using confidence-aware heuristics and repeated-note anchoring, then extend diagnostics/evaluation artifacts to attribute retained raw notes by source and benchmark the impact on Hysteria and Trooper.

**Tech Stack:** Python 3.14, pytest, uv, librosa, wave, existing DeChord transcription and evaluation pipeline, make.

---

- [x] Task 1: Add dense-note candidate generation primitives and TDD coverage for targeted windows and repeated-note anchoring.
- [x] Task 2: Implement pre-cleanup hybrid fusion plus raw-note source attribution in `TabPipeline` with TDD coverage.
- [x] Task 3: Extend evaluation/report generation for Phase 6 source diagnostics, run reset plus verification and canonical benchmarks, write required reports/artifacts, mark tasks complete, and commit.
