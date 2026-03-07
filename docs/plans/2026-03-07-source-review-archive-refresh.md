# Source Review Archive Refresh Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create a fresh lean source-only zip archive for external review with the latest backend pipeline work and markdown documentation, excluding generated and binary artifacts.

**Architecture:** Build a temporary filtered copy rooted at `DeChord-source-review-latest/`, copy only the allowed top-level files and directories, prune excluded artifacts, then zip that filtered tree and validate the resulting contents. This is an operational packaging task, so TDD is not applicable; validation is performed with explicit archive-content checks instead.

**Tech Stack:** zsh, rsync, find, zip, unzip

---

- [x] Create a filtered source-only staging tree rooted at `DeChord-source-review-latest/`
- [x] Build `DeChord-source-review-latest.zip` from the staging tree
- [x] Validate required contents and excluded artifacts
- [x] Mark plan complete and commit with plan-path traceability
