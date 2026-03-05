# AlphaTab Cursor + Current Note Highlight Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make DeChord tab playback visibly follow the current musical position with beat cursor, bar highlight, and current-note highlighting.

**Architecture:** Keep DeChord's existing external-media time sync (`timePosition` + `scrollToCursor`) and enable alphaTab's built-in cursor/highlight capabilities in viewer settings. Add global alphaTab cursor/highlight CSS so those elements are visibly rendered in the app theme.

**Tech Stack:** React 19, TypeScript, alphaTab, Vite, Vitest, global CSS.

---

## Tasks

- [x] Task 1: Add a failing unit test asserting alphaTab cursor/highlight settings (`enableAnimatedBeatCursor`, `enableElementHighlighting`) in `createTabViewerSettings`.
- [ ] Task 2: Implement the minimal `TabViewerPanel` player settings change to satisfy the new test while preserving existing external sync behavior.
- [ ] Task 3: Add global alphaTab cursor/highlight CSS styles (`.at-cursor-bar`, `.at-cursor-beat`, `.at-highlight`) and verify existing TabViewer tests still pass.
- [ ] Task 4: Run required reset and final verification (`make reset`, focused frontend tests) and mark all plan tasks complete.
