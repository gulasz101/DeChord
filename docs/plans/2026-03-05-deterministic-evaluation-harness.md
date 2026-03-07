# Deterministic Evaluation Harness Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make evaluation deterministic by resolving explicit MP3/GP5 pairs and writing stable benchmark artifacts.

**Architecture:** Refactor `backend/scripts/evaluate_tab_quality.py` into explicit argument parsing + path resolution + validation helpers, while preserving full `TabPipeline.run()` usage. Add deterministic naming/context logging and expand unit tests around CLI/path validation via mocks.

**Tech Stack:** Python 3.13, argparse, pathlib, pytest, monkeypatch/mocks.

---

- [ ] Task 1: Add explicit `--mp3` + `--gp5` CLI mode (paired/validated) in `backend/scripts/evaluate_tab_quality.py`.
- [x] Task 2: Add convenience `--song-dir` + `--song` mode with hard-fail resolution in `backend/scripts/evaluate_tab_quality.py`.
- [x] Task 3: Add deterministic report filename prefixing (`artist__song`) and remove ambiguous naming in `backend/scripts/evaluate_tab_quality.py`.
- [x] Task 4: Print evaluation context at startup and include the same context in debug JSON.
- [x] Task 5: Verify evaluation still uses full `TabPipeline.run()` path and keep integration behavior unchanged.
- [x] Task 6: Ensure required onset/pitch/octave/density metrics are present in output JSON schema.
- [x] Task 7: Add hard validation failures for missing files, short MP3 duration, and zero-note GP5.
- [x] Task 8: Add unit tests for CLI parsing/path resolution/invalid combinations in `backend/tests/test_evaluate_tab_quality.py`.
