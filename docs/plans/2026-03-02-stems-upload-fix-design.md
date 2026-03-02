# Fix Stems Upload & Quality — Design

**Date:** 2026-03-02
**Status:** Approved

## Problem Statement

1. **Upload button click broken** — clicking the upload area/button does nothing; only drag-and-drop works
2. **Stems silently ignored** — selecting "Analyze + split stems" mode runs only chord analysis; stem splitting never executes or fails silently
3. **Stem quality below DemucsGUI** — current simple `demucs.api.Separator("htdemucs")` call doesn't use optimal parameters

## Design

### Fix 1: Upload Button Click (Frontend)

**SongLibraryPanel.tsx** — `<label>` wraps a hidden `<input>` without proper `htmlFor`/`id` pairing. Replace with ref-based click handler matching DropZone pattern.

**DropZone.tsx** — Verify click handler works; the `select` dropdown's `stopPropagation` might be interfering in some cases. Ensure the file input ref click is reliable.

### Fix 2: Stems Silently Ignored (Backend)

The data flow (`process_mode` from FormData → job dict → `_run_analysis` conditional) is correct at code level. The root cause is likely:
- Demucs import/runtime failure that's caught and swallowed
- Missing model files or dependencies at runtime
- The stem splitting `try/except` block silently setting `stems_status = "failed"` without user-visible feedback

**Fix approach:**
- Add structured logging to stem splitting path
- Ensure `stems_error` is always populated on failure and surfaced in job status
- Add startup diagnostic check for demucs availability
- Make stem failures loud, not silent

### Fix 3: Stem Quality (Backend — stems.py)

Upgrade `split_to_stems()` to match DemucsGUI's separation quality:

- **Model**: Use `htdemucs_ft` (fine-tuned) for best quality, fall back to `htdemucs`
- **Device detection**: Auto-detect MPS (Apple Silicon) → CUDA → CPU
- **Segment processing**: Use model-appropriate segment length
- **Overlap**: 0.25 (DemucsGUI default)
- **Shifts**: 1-2 random time shifts for improved SDR (~0.2 points improvement)
- **Output**: WAV float32 (matching DemucsGUI)
- **Add `make download-models`** Makefile target for pre-downloading model checkpoints

### Fix 4: Verification

- `make reset` for fresh state
- Upload test with `/Users/wojciechgula/Downloads/Clara Luciani - La grenade (Clip officiel) [85m-Qgo9_nE].mp3`
- Verify stems are created, playable, and selectable in UI
