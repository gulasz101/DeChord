# Upload Progress Accuracy — Design Spec

**Date:** 2026-03-13
**Status:** Approved
**Scope:** Backend job progress reporting for chord analysis and stem splitting

---

## Problem

Two distinct progress reporting bugs affect the upload processing flow:

1. **Chord analysis freezes at 40%** — progress sits frozen then jumps to 100% when analysis completes.
2. **Stem splitting oscillates 90–95%** — progress flickers backward and forward near the end of splitting.

---

## Root Cause Analysis

### Bug 1 — Chord analysis frozen at 40%

In `_run_analysis` (`backend/app/main.py`), the code sets `progress_pct=40` and immediately calls `analyze_audio(audio_path)` — a synchronous black-box that runs three sequential madmom operations (chords → key → tempo) with zero intermediate callbacks. Progress stays frozen for the full duration (typically 30–90 seconds), then jumps straight to the next stage.

### Bug 2 — Stems oscillating 90–95%

Two stacked causes:

1. **Demucs shift passes reset the segment offset.** Demucs processes audio in overlapping segments. With `shifts ≥ 1`, it runs multiple passes; `segment_offset` resets to 0 at the start of each pass. The progress callback computes `stage_progress = segment_offset / audio_length`, so progress cycles from 0 → 1 repeatedly — once per shift pass.

2. **"Saving stems" callback regresses progress.** After Demucs completes (reaching ~100% = overall 95%), `progress_callback(0.9, "Saving stems...")` is explicitly called, which maps to overall **90%** — a visible backward jump. This creates a 95% → 90% → 95% bounce on every upload.

---

## Design

### Fix 1 — Granular chord analysis progress

Replace the single `analyze_audio()` call with three individual function calls, inserting `set_stage()` between each:

```
10%  → "Detecting chords..."  → detect_chords()
25%  → "Detecting key..."     → detect_key()
35%  → "Detecting tempo..."   → detect_tempo()
40%+ → continue to stems or persist
```

`detect_chords`, `detect_key`, `detect_tempo`, `get_audio_duration` are already exported from `app.analysis`; only the import line in `main.py` needs updating.

**Result:** Progress advances three times visibly through the analysis phase instead of freezing.

### Fix 2 — Monotonically non-decreasing stem progress

Introduce a closure `_on_stem_progress` that wraps the existing lambda and maintains a `_stem_max_pct` high-water mark. The overall progress passed to `set_stage` is `max(current, _stem_max_pct[0])` — it can only move forward.

This is intentionally robust: it absorbs any source of regression (Demucs shift-pass resets, the "Saving stems" 0.9 callback, any future additions) without requiring changes to `stems.py` or knowledge of Demucs internals.

**Result:** Progress climbs monotonically from 45% → 95% during stem splitting with no visible backward movement.

---

## Files Changed

| File | Change |
|---|---|
| `backend/app/main.py` | Updated `app.analysis` import; replaced `analyze_audio()` with 3 individual calls + `set_stage()`; replaced stem `on_progress` lambda with `_on_stem_progress` closure |
| `backend/app/analysis.py` | No changes — individual functions already exist and are exported |

---

## Out of Scope

- Frontend progress bar smoothing / animation
- Actual progress feedback inside madmom (not feasible without patching madmom)
- Demucs callback math improvements (the monotonic clamp is sufficient and more robust)

---

## Testing

- Upload an audio file with `analysis_only` mode → verify progress advances at 10%, 25%, 35%, not frozen at 40%
- Upload with `analysis_and_stems` mode → verify stem progress bar climbs smoothly from 45% → 95% without any backward movement
- Confirm final completion at 100% in both modes
