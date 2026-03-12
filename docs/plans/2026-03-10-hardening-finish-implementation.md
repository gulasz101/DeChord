# Hardening and Finish Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make DeChord finish the product-completion program with reset-safe runtime bootstrap, honest reset-loss behavior, repeatable focused verification, and active-plan cleanup for misleading leftovers.

**Architecture:** Keep the slice narrow. Add one backend-owned runtime bootstrap path for local artifacts and lifecycle wiring, tighten `frontend/src/App.tsx` so reset-loss journeys end in truthful copy, and clean only the active documentation references that still mislead execution. Final verification must run before reset and again after `make reset` / `make up`, with explicit warning-only allowances.

**Tech Stack:** FastAPI, Python 3.13+, LibSQL, pytest, React 19, TypeScript, Vite, Vitest, Testing Library, GNU Make.

---

## XML Tracking

<phase id="hardening-finish-plan-execution" status="planned">
  <task>[ ] Task 1: Lock reset-safe backend runtime bootstrap with failing tests.</task>
  <task>[ ] Task 2: Lock truthful reset-loss journey behavior in the frontend.</task>
  <task>[ ] Task 3: Normalize misleading active verification references.</task>
  <task>[ ] Task 4: Run the hardening quality gate and record slice status.</task>
</phase>

### Task 1: Lock reset-safe backend runtime bootstrap with failing tests

**Files:**
- Create: `backend/app/runtime.py`
- Modify: `backend/app/main.py`
- Modify: `backend/tests/test_db_bootstrap.py`
- Test: `backend/tests/test_db_bootstrap.py`

**Step 1: Write the failing test**

```python
def test_runtime_paths_create_missing_dirs(tmp_path: Path):
    from app.runtime import RuntimePaths

    paths = RuntimePaths(root=tmp_path / "backend-runtime")
    paths.ensure_dirs()

    assert paths.uploads_dir.is_dir()
    assert paths.stems_dir.is_dir()
    assert paths.cache_dir.is_dir()


def test_app_uses_lifespan_instead_of_event_hooks(tmp_path: Path, monkeypatch):
    client = _build_client(tmp_path, monkeypatch)
    import app.main as main

    assert main.app.router.on_startup == []
    assert main.app.router.on_shutdown == []
    assert client.get("/api/health").status_code == 200
```

**Step 2: Run test to verify it fails**

Run: `uv run --project backend pytest backend/tests/test_db_bootstrap.py -k "runtime_paths_create_missing_dirs or app_uses_lifespan_instead_of_event_hooks" -q`
Expected: FAIL because `backend/app/runtime.py` does not exist yet and `backend/app/main.py` still registers startup/shutdown work with `@app.on_event(...)`.

**Step 3: Write minimal implementation**

```python
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RuntimePaths:
    root: Path

    @property
    def uploads_dir(self) -> Path:
        return self.root / "uploads"

    @property
    def stems_dir(self) -> Path:
        return self.root / "stems"

    @property
    def cache_dir(self) -> Path:
        return self.root / "cache"

    def ensure_dirs(self) -> None:
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self.stems_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
```

```python
@asynccontextmanager
async def lifespan(_app: FastAPI):
    runtime_paths.ensure_dirs()
    await init_db()
    try:
        yield
    finally:
        await close_db()


app = FastAPI(lifespan=lifespan)
```

Implementation details to keep:
- keep portability-minded defaults relative to the backend workspace; do not introduce new services or mandatory env configuration
- treat `uploads`, `stems`, and `cache` as the runtime directories this slice owns explicitly
- remove startup/shutdown event-hook registration once lifespan is in place
- keep health-check behavior unchanged apart from cleaner startup semantics

**Step 4: Run test to verify it passes**

Run: `uv run --project backend pytest backend/tests/test_db_bootstrap.py -k "runtime_paths_create_missing_dirs or app_uses_lifespan_instead_of_event_hooks" -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add backend/app/runtime.py backend/app/main.py backend/tests/test_db_bootstrap.py
git commit -m "fix: harden runtime bootstrap lifecycle (docs/plans/2026-03-10-hardening-finish-implementation.md task: Lock reset-safe backend runtime bootstrap with failing tests) | opencode | gpt-5.1-codex-max"
```

### Task 2: Lock truthful reset-loss journey behavior in the frontend

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/__tests__/App.integration.test.tsx`
- Test: `frontend/src/__tests__/App.integration.test.tsx`

**Step 1: Write the failing test**

```tsx
it("replaces stale processing copy when reset removes a job", async () => {
  getJobStatusMock.mockRejectedValueOnce(
    new Error("Processing job no longer available after reset"),
  );

  render(<App />);
  ...

  expect(await screen.findByText(/lost after a reset/i)).toBeInTheDocument();
  expect(screen.getByText(/re-upload the song or return to the library/i)).toBeInTheDocument();
  expect(screen.queryByText(/splitting stems/i)).not.toBeInTheDocument();
});
```

Add a second failure for completed-result loss:

```tsx
it("replaces stale completion copy when reset removes a finished result", async () => {
  getJobStatusMock.mockResolvedValueOnce({ status: "complete", progress_pct: 100 });
  getResultMock.mockRejectedValueOnce(
    new Error("Processing result no longer available after reset"),
  );

  render(<App />);
  ...

  expect(await screen.findByText(/finished job result was lost after a reset/i)).toBeInTheDocument();
  expect(screen.getByText(/refresh the library or re-run processing/i)).toBeInTheDocument();
});
```

**Step 2: Run test to verify it fails**

Run: `npm --prefix frontend test -- --run src/__tests__/App.integration.test.tsx`
Expected: FAIL because `frontend/src/App.tsx` still preserves stale journey-stage messaging when reset-loss errors occur.

**Step 3: Write minimal implementation**

```tsx
function getJourneyResetLossState(error: unknown): { message: string; error: string } | null {
  if (!(error instanceof Error)) return null;
  if (error.message === "Processing job no longer available after reset") {
    return {
      message: "Reset removed this in-progress job. Re-upload the song or return to the library.",
      error: "This processing job was lost after a reset. DeChord cannot recover in-progress jobs yet.",
    };
  }
  if (error.message === "Processing result no longer available after reset") {
    return {
      message: "Reset removed the saved result for this job. Refresh the library or re-run processing.",
      error: "The finished job result was lost after a reset. Retry refresh or return to the library.",
    };
  }
  return null;
}
```

```tsx
const resetLoss = getJourneyResetLossState(error);
...
message: resetLoss?.message ?? "Processing failed",
error: resetLoss?.error ?? getJourneyErrorMessage(error),
```

Implementation details to keep:
- treat reset-loss as honest failure, not recoverable progress
- replace stale stage copy instead of layering the error under an old in-progress message
- keep the route in the processing journey only long enough to explain the failure clearly; do not fake resumed polling
- do not add background recovery, persistence, or retry infrastructure in this task

**Step 4: Run test to verify it passes**

Run: `npm --prefix frontend test -- --run src/__tests__/App.integration.test.tsx`
Expected: PASS.

**Step 5: Commit**

```bash
git add frontend/src/App.tsx frontend/src/__tests__/App.integration.test.tsx
git commit -m "fix: make reset-loss journey copy fully honest (docs/plans/2026-03-10-hardening-finish-implementation.md task: Lock truthful reset-loss journey behavior in the frontend) | opencode | gpt-5.1-codex-max"
```

### Task 3: Normalize misleading active verification references

**Files:**
- Modify: `docs/plans/2026-03-10-product-completion-program-implementation.md`
- Modify: `docs/plans/2026-03-09-opus53-frontend-redesign-implementation.md`

**Step 1: Review the failing reference set**

Run:

```bash
rg "TransportBarSpeed\.test\.tsx" docs/plans/2026-03-10-product-completion-program-implementation.md docs/plans/2026-03-09-opus53-frontend-redesign-implementation.md
```

Expected: MATCHES showing the outdated test name still appears in active execution docs.

**Step 2: Write minimal documentation cleanup**

Replace the stale references with the current test path:

```md
frontend/src/components/__tests__/TransportBar.transport.test.tsx
```

Keep this task narrow:
- update only the active source-of-truth docs used by the current program
- `docs/plans/2026-03-09-opus53-frontend-redesign-implementation.md` stays in scope because Task 12 still points to it as an execution/reference document for frontend verification history that can mislead the current program if left stale
- do not sweep historical archives beyond what still misleads current execution
- TDD does not apply to this documentation-only task; use targeted search verification instead

**Step 3: Run verification to confirm the cleanup**

Run:

```bash
rg "TransportBarSpeed\.test\.tsx" docs/plans/2026-03-10-product-completion-program-implementation.md docs/plans/2026-03-09-opus53-frontend-redesign-implementation.md
```

Expected: NO MATCHES.

**Step 4: Commit**

```bash
git add docs/plans/2026-03-10-product-completion-program-implementation.md docs/plans/2026-03-09-opus53-frontend-redesign-implementation.md
git commit -m "docs: remove misleading active verification leftovers (docs/plans/2026-03-10-hardening-finish-implementation.md task: Normalize misleading active verification references) | opencode | gpt-5.1-codex-max"
```

### Task 4: Run the hardening quality gate and record slice status

**Files:**
- Modify: `docs/plans/2026-03-10-hardening-finish-implementation.md`
- Modify: `docs/plans/2026-03-10-product-completion-program-implementation.md`
- Verify: `backend/tests/test_db_bootstrap.py`
- Verify: `frontend/src/__tests__/App.integration.test.tsx`

**Step 1: Write the failing test**

```md
<phase id="hardening-finish-plan-execution" status="planned">
  <task>[ ] Task 1: Lock reset-safe backend runtime bootstrap with failing tests.</task>
  <task>[ ] Task 2: Lock truthful reset-loss journey behavior in the frontend.</task>
  <task>[ ] Task 3: Normalize misleading active verification references.</task>
  <task>[ ] Task 4: Run the hardening quality gate and record slice status.</task>
</phase>
```

Treat incomplete XML tracking, missing verification evidence, and an un-updated Slice 6 ledger entry as the failure condition for this final task.

**Step 2: Run test to verify it fails**

Run: `uv run --project backend pytest backend/tests/test_db_bootstrap.py -k "runtime_paths_create_missing_dirs or app_uses_lifespan_instead_of_event_hooks" -q && npm --prefix frontend test -- --run src/__tests__/App.integration.test.tsx && npm --prefix frontend run build`
Expected: PASS for code only after Tasks 1-3 are complete, but documentation still fails until this plan and the Slice 6 ledger entry are updated with final status and verification evidence.

**Step 3: Write minimal implementation**

```md
<phase id="hardening-finish-plan-execution" status="completed">
  <task>[x] Task 1: Lock reset-safe backend runtime bootstrap with failing tests.</task>
  <task>[x] Task 2: Lock truthful reset-loss journey behavior in the frontend.</task>
  <task>[x] Task 3: Normalize misleading active verification references.</task>
  <task>[x] Task 4: Run the hardening quality gate and record slice status.</task>
</phase>
```

After code is green, record all of the following:
- exact backend and frontend commands from the quality gate
- the pre-reset result and the post-`make reset` / `make up` rerun result
- manual verification covering runtime-dir recreation, reset-loss honesty, and doc cleanup confirmation
- Slice 6 status and commit links in `docs/plans/2026-03-10-product-completion-program-implementation.md`
- warning-only notes limited to the accepted posture below

**Step 4: Run test to verify it passes**

Run these steps in order:

1. `uv run --project backend pytest backend/tests/test_db_bootstrap.py -k "runtime_paths_create_missing_dirs or app_uses_lifespan_instead_of_event_hooks" -q`
2. `npm --prefix frontend test -- --run src/__tests__/App.integration.test.tsx`
3. `npm --prefix frontend run build`
4. `make reset`
5. `make up`
6. confirm readiness from the real shell before post-reset checks, for example with `make status`, `make logs`, or the expected local frontend/backend routes
7. rerun `uv run --project backend pytest backend/tests/test_db_bootstrap.py -k "runtime_paths_create_missing_dirs or app_uses_lifespan_instead_of_event_hooks" -q`
8. rerun `npm --prefix frontend test -- --run src/__tests__/App.integration.test.tsx`
9. rerun `npm --prefix frontend run build`

Expected: PASS. The only accepted warning-only note is the existing Vite chunk-size warning for `alphaTab`, provided build still succeeds. Then manually verify reset-loss behavior from the real shell after readiness is confirmed.

## Hardening Quality Gate

- `uv run --project backend pytest backend/tests/test_db_bootstrap.py -k "runtime_paths_create_missing_dirs or app_uses_lifespan_instead_of_event_hooks" -q`
- `npm --prefix frontend test -- --run src/__tests__/App.integration.test.tsx`
- `npm --prefix frontend run build`
- `make reset`
- `make up` as a separate runtime-start step
- confirm readiness before post-reset checks using the real shell (`make status`, `make logs`, or expected local routes)
- rerun the same backend and frontend commands after reset and readiness confirmation
- manual verification covering:
  - backend recreates `backend/uploads`, `backend/stems`, and `backend/cache`
  - the app boots from a clean reset without stale runtime leftovers
  - processing-journey reset loss shows explicit truthful copy instead of stale progress text
  - active docs no longer reference `TransportBarSpeed.test.tsx`

### Accepted Warning-Only Posture

- `npm --prefix frontend run build` may continue to emit the existing Vite chunk-size warning for `alphaTab`
- reset may continue to discard in-flight jobs and results, but the product must explain that limitation honestly

### Must-Be-Green Posture

- runtime bootstrap tests pass
- frontend reset-loss integration tests pass
- `make reset` and `make up` succeed
- rerun verification after reset matches the expected outcomes
- Slice 6 ledger and XML tracking are updated with final status

**Step 5: Commit**

```bash
git add docs/plans/2026-03-10-hardening-finish-implementation.md docs/plans/2026-03-10-product-completion-program-implementation.md
git commit -m "docs: record hardening finish verification status (docs/plans/2026-03-10-hardening-finish-implementation.md task: Run the hardening quality gate and record slice status) | opencode | gpt-5.1-codex-max"
```

This final commit is documentation-only. Do not restage code already captured by the earlier atomic commits.
