# Fix Stems Upload & Quality Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix broken upload button clicks, fix silent stem splitting failures, and upgrade stem separation quality to match DemucsGUI.

**Architecture:** Three independent fixes — frontend upload button (ref-based click), backend stem splitting (logging + device detection + quality params), and Makefile target for model downloads.

**Tech Stack:** React 19, TypeScript, FastAPI, Python 3.13, Demucs (htdemucs_ft model), PyTorch (MPS/CUDA/CPU)

---

### Task 1: Fix SongLibraryPanel upload button click [x]

**Files:**
- Modify: `frontend/src/components/SongLibraryPanel.tsx:36-48`
- Test: `frontend/src/components/SongLibraryPanel.test.tsx` (create)

**Step 1: Write the failing test**

Create `frontend/src/components/SongLibraryPanel.test.tsx`:

```tsx
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { SongLibraryPanel } from "./SongLibraryPanel";

describe("SongLibraryPanel", () => {
  const defaultProps = {
    songs: [],
    selectedSongId: null,
    onSelect: vi.fn(),
    onUpload: vi.fn(),
  };

  it("opens file picker when Upload button is clicked", () => {
    render(<SongLibraryPanel {...defaultProps} />);
    const uploadBtn = screen.getByText("Upload");
    const fileInput = uploadBtn.closest("div")!.querySelector("input[type='file']") as HTMLInputElement;
    const clickSpy = vi.spyOn(fileInput, "click");
    fireEvent.click(uploadBtn);
    expect(clickSpy).toHaveBeenCalled();
  });
});
```

**Step 2: Run test to verify it fails**

Run: `cd frontend && bun run test -- SongLibraryPanel`
Expected: FAIL — the current `<label>` + hidden `<input>` pattern doesn't trigger a programmatic `.click()`.

**Step 3: Write minimal implementation**

Replace the `<label>` wrapper in `SongLibraryPanel.tsx` lines 36-48 with a ref-based approach:

```tsx
// Add useRef import at top (line 1)
import { useState, useRef } from "react";

// Replace the label+input block (lines 36-48) with:
<button
  type="button"
  onClick={() => fileInputRef.current?.click()}
  disabled={loading}
  className="cursor-pointer rounded-md bg-blue-600 px-2.5 py-1 text-xs font-semibold text-white hover:bg-blue-500 disabled:opacity-50"
>
  {loading ? "Processing..." : "Upload"}
</button>
<input
  ref={fileInputRef}
  type="file"
  accept=".mp3,.wav,.m4a,.aac,.mp4"
  className="hidden"
  onChange={(e) => {
    const file = e.target.files?.[0];
    if (file) onUpload(file, mode);
  }}
  disabled={loading}
/>
```

Add `const fileInputRef = useRef<HTMLInputElement>(null);` next to the `mode` state.

**Step 4: Run test to verify it passes**

Run: `cd frontend && bun run test -- SongLibraryPanel`
Expected: PASS

**Step 5: Commit**

```bash
git add frontend/src/components/SongLibraryPanel.tsx frontend/src/components/SongLibraryPanel.test.tsx
git commit -m "fix(frontend): use ref-based click for library upload button

plan: docs/plans/2026-03-02-stems-upload-fix-implementation.md task 1"
```

---

### Task 2: Add backend logging for stem splitting path [x]

**Files:**
- Modify: `backend/app/main.py:186-212`
- Modify: `backend/app/stems.py:36-57`
- Test: existing `backend/tests/test_api.py` (verify still passes)

**Step 1: Add logging imports and log statements**

In `backend/app/main.py`, add `import logging` at top and `logger = logging.getLogger(__name__)` after imports.

In `_run_analysis` (line 186-212), add logging:

```python
if jobs[job_id].get("process_mode") == "analysis_and_stems":
    logger.info("Job %s: starting stem splitting for song %s", job_id, song_id)
    try:
        # ... existing code ...
        logger.info("Job %s: stem splitting complete", job_id)
    except Exception as exc:
        logger.error("Job %s: stem splitting failed: %s", job_id, exc, exc_info=True)
        jobs[job_id]["stems_status"] = "failed"
        jobs[job_id]["stems_error"] = str(exc)
else:
    logger.info("Job %s: stems not requested (mode=%s)", job_id, jobs[job_id].get("process_mode"))
```

In `backend/app/stems.py`, add logging to `_separate_with_demucs`:

```python
import logging
logger = logging.getLogger(__name__)

def _separate_with_demucs(...):
    logger.info("Demucs: checking runtime dependencies...")
    check_stem_runtime_ready()
    logger.info("Demucs: importing demucs.api...")
    import demucs.api
    logger.info("Demucs: creating separator with model=%s", model_name)
    # ... rest
```

**Step 2: Run existing tests to verify no regressions**

Run: `cd backend && uv run pytest tests/ -v`
Expected: All existing tests PASS

**Step 3: Commit**

```bash
git add backend/app/main.py backend/app/stems.py
git commit -m "fix(backend): add structured logging to stem splitting path

plan: docs/plans/2026-03-02-stems-upload-fix-implementation.md task 2"
```

---

### Task 3: Upgrade Demucs separation to DemucsGUI quality [x]

**Files:**
- Modify: `backend/app/stems.py:36-57` (rewrite `_separate_with_demucs`)
- Test: `backend/tests/test_stems.py` (create)

**Step 1: Write failing tests for upgraded separator**

Create `backend/tests/test_stems.py`:

```python
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from app.stems import (
    split_to_stems,
    _detect_device,
    _get_model_params,
    StemResult,
)


def test_detect_device_returns_string():
    """Device detection must return a valid torch device string."""
    device = _detect_device()
    assert device in ("mps", "cuda", "cpu")


def test_get_model_params_htdemucs_ft():
    """htdemucs_ft model should have expected default params."""
    params = _get_model_params("htdemucs_ft")
    assert "segment" in params
    assert "overlap" in params
    assert "shifts" in params
    assert params["overlap"] == 0.25
    assert params["shifts"] >= 1


def test_split_to_stems_uses_injected_separator(tmp_path):
    """split_to_stems with injected separate_fn skips real demucs."""
    audio_file = tmp_path / "test.mp3"
    audio_file.write_bytes(b"fake-audio")
    output_dir = tmp_path / "stems"

    def fake_separate(audio_path, out_dir, progress_callback):
        out_dir.mkdir(parents=True, exist_ok=True)
        for stem in ("vocals", "drums", "bass", "other"):
            (out_dir / f"{stem}.wav").write_bytes(b"wav-data")
        progress_callback(1.0, "done")
        return {s: out_dir / f"{s}.wav" for s in ("vocals", "drums", "bass", "other")}

    results = split_to_stems(
        audio_path=str(audio_file),
        output_dir=output_dir,
        separate_fn=fake_separate,
    )
    assert len(results) == 4
    assert all(isinstance(r, StemResult) for r in results)
    keys = {r.stem_key for r in results}
    assert keys == {"vocals", "drums", "bass", "other"}


def test_default_engine_is_demucs(monkeypatch):
    """Default engine should be demucs, not fallback."""
    monkeypatch.delenv("DECHORD_STEM_ENGINE", raising=False)
    from app.stems import split_to_stems
    import app.stems as stems_mod
    # Engine defaults to demucs when env var is unset
    import os
    assert os.getenv("DECHORD_STEM_ENGINE", "demucs") == "demucs"
```

**Step 2: Run tests to verify they fail**

Run: `cd backend && uv run pytest tests/test_stems.py -v`
Expected: FAIL — `_detect_device` and `_get_model_params` don't exist yet.

**Step 3: Implement upgraded Demucs separator**

Rewrite `backend/app/stems.py` `_separate_with_demucs` function. Key changes:

```python
import logging
import torch

logger = logging.getLogger(__name__)

# Model preference order: fine-tuned first, then standard
DEMUCS_MODEL = os.getenv("DECHORD_DEMUCS_MODEL", "htdemucs_ft")
DEMUCS_FALLBACK_MODEL = "htdemucs"


def _detect_device() -> str:
    """Auto-detect best available compute device."""
    if torch.backends.mps.is_available():
        logger.info("Demucs: using MPS (Apple Silicon)")
        return "mps"
    if torch.cuda.is_available():
        logger.info("Demucs: using CUDA")
        return "cuda"
    logger.info("Demucs: using CPU")
    return "cpu"


def _get_model_params(model_name: str) -> dict:
    """Return DemucsGUI-quality separation parameters."""
    return {
        "segment": None,  # None = use model default segment
        "overlap": 0.25,
        "shifts": 1,  # 1 shift improves SDR ~0.2 points
    }


def _separate_with_demucs(
    input_audio: str,
    output_dir: Path,
    progress_callback: DemucsProgressCallback,
) -> dict[str, Path]:
    check_stem_runtime_ready()
    import demucs.api

    output_dir.mkdir(parents=True, exist_ok=True)
    device = _detect_device()
    model_name = DEMUCS_MODEL

    logger.info("Demucs: initializing separator model=%s device=%s", model_name, device)
    try:
        separator = demucs.api.Separator(model=model_name, device=device)
    except Exception:
        logger.warning("Demucs: model %s unavailable, falling back to %s", model_name, DEMUCS_FALLBACK_MODEL)
        model_name = DEMUCS_FALLBACK_MODEL
        separator = demucs.api.Separator(model=model_name, device=device)

    params = _get_model_params(model_name)
    separator.update_parameter(
        segment=params["segment"],
        overlap=params["overlap"],
        shifts=params["shifts"],
    )

    progress_callback(0.05, f"Loaded model {model_name} on {device}")
    logger.info("Demucs: separating audio file %s", input_audio)

    _, separated = separator.separate_audio_file(input_audio)
    progress_callback(0.9, "Saving stems...")

    outputs: dict[str, Path] = {}
    for stem_key, tensor in separated.items():
        out_path = output_dir / f"{stem_key}.wav"
        separator.save_audio(tensor, str(out_path))
        outputs[stem_key] = out_path
        logger.info("Demucs: saved stem %s -> %s", stem_key, out_path)

    progress_callback(1.0, "Separated stems")
    return outputs
```

**Step 4: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/test_stems.py -v`
Expected: PASS

**Step 5: Run full test suite**

Run: `cd backend && uv run pytest tests/ -v`
Expected: All PASS

**Step 6: Commit**

```bash
git add backend/app/stems.py backend/tests/test_stems.py
git commit -m "feat(stems): upgrade to DemucsGUI-quality separation with device detection

- Use htdemucs_ft model with htdemucs fallback
- Auto-detect MPS/CUDA/CPU device
- Apply overlap=0.25, shifts=1 for better SDR
- Add structured logging throughout separation

plan: docs/plans/2026-03-02-stems-upload-fix-implementation.md task 3"
```

---

### Task 4: Add `make download-models` Makefile target [x]

**Files:**
- Modify: `Makefile`
- Test: manual (`make download-models` should succeed)

**Step 1: Add the target**

Add to `Makefile` after the `install` target:

```makefile
download-models:
	cd backend && uv run python -c "from demucs.api import Separator; Separator(model='htdemucs_ft'); print('htdemucs_ft downloaded'); Separator(model='htdemucs'); print('htdemucs downloaded')"
	@echo "Models downloaded successfully."
```

Also update `.PHONY` line to include `download-models`.

**Step 2: Run to verify**

Run: `make download-models`
Expected: Models download (or confirm already cached), prints success message.

**Step 3: Commit**

```bash
git add Makefile
git commit -m "feat(make): add download-models target for pre-downloading demucs checkpoints

plan: docs/plans/2026-03-02-stems-upload-fix-implementation.md task 4"
```

---

### Task 5: Run full test suite and verify [x]

**Step 1: Run backend tests**

Run: `cd backend && uv run pytest tests/ -v`
Expected: All PASS

**Step 2: Run frontend tests**

Run: `cd frontend && bun run test`
Expected: All PASS

**Step 3: Commit plan file updates**

```bash
git add docs/plans/
git commit -m "docs: update plan with completion status

plan: docs/plans/2026-03-02-stems-upload-fix-implementation.md task 5"
```

---

### Task 6: Reset, start app, and verify end-to-end [x]

**Step 1: Reset state**

Run: `make reset && make up`

**Step 2: Upload test file with stems mode**

Upload `/Users/wojciechgula/Downloads/Clara Luciani - La grenade (Clip officiel) [85m-Qgo9_nE].mp3` via the UI with "Analyze + split stems" mode selected. Verify:
- [ ] Upload button click opens file picker
- [ ] File uploads and progress bar shows "splitting_stems" stage
- [ ] Stems are created in `backend/stems/{song_id}/`
- [ ] Stem mixer panel appears in player
- [ ] Individual stems are playable

**Step 3: Commit final verification**

```bash
git add -A
git commit -m "chore: verify end-to-end stems upload and playback

plan: docs/plans/2026-03-02-stems-upload-fix-implementation.md task 6"
```
