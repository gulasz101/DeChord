# Toast, Note Lane, and Timeline Color Tweaks

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Refine playback UX by improving toast visibility, separating timed-note creation from seek interaction, and aligning timeline chord color semantics with fretboard current/next highlighting.

---

## Task 1: Reposition and resize toasts

- [x] Step 1: Move toasts to top center
- [x] Step 2: Increase width and visual emphasis
- [x] Step 3: Verify rendering
- [x] Step 4: Commit

## Task 2: Add dedicated note lane above seek bar

- [x] Step 1: Add clickable lane for timed-note creation
- [x] Step 2: Keep seek bar dedicated to seeking only
- [x] Step 3: Add note markers on lane
- [x] Step 4: Add marker click-to-edit flow
- [x] Step 5: Default timed-note duration to end of current active chord
- [x] Step 6: Verify with frontend tests/build
- [x] Step 7: Commit

## Task 3: Align timeline current/next chord coloring

- [x] Step 1: Color current chord as blue
- [x] Step 2: Color next chord as orange/amber
- [x] Step 3: Verify progression behavior while playback advances
- [x] Step 4: Commit

## Verification

```bash
cd frontend && bun test
cd frontend && bun run build
```
