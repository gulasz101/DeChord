# Real Frontend No-Mocks Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Remove all redesign mock fallback from the real frontend and replace it with real inline band/project/song flows backed by the existing API and schema.

**Architecture:** Keep the Opus 5-3 route shell, but make `App.tsx` fully API-driven. Add minimal backend creation endpoints and project-scoped upload support, then expose inline creation panels and honest empty states in the redesign pages.

**Tech Stack:** FastAPI, React 19, Vite, TypeScript, Vitest, pytest.

---

## Execution Checklist

- [x] Task 1: Add backend tests for band creation, project creation, and project-scoped upload.
- [x] Task 2: Implement backend create-band, create-project, and project-scoped upload behavior.
- [x] Task 3: Add frontend API/type tests for the new real-data flows.
- [x] Task 4: Add frontend app integration tests proving no mock fallback and first-band inline creation.
- [ ] Task 5: Implement real API-only bootstrapping and the inline first-band flow.
- [ ] Task 6: Add project creation and project-scoped upload frontend tests.
- [ ] Task 7: Implement inline create-project and real song upload flows.
- [ ] Task 8: Verify, run `make reset`, finalize plan state, and notify.

## Notes

- Use TDD for all implementation tasks.
- Do not keep `MOCK_BANDS` reachable from the real runtime.
- Keep `frontend/src/redesign/lib/mockData.ts` only if needed for isolated design work, not for the actual app bootstrap.
- This environment does not expose a subagent dispatch tool, so literal subagent-driven development cannot be applied here. Use this plan as the execution record and keep task boundaries strict.

### Task 1: Add Backend Tests

**Files:**
- Modify: `backend/tests/test_api.py`
- Inspect: `backend/app/main.py`
- Inspect: `backend/app/db.py`

**Step 1: Write the failing tests**

Add tests for:
- `POST /api/bands` creates a band owned by the resolved/default user and membership row
- `POST /api/bands/{band_id}/projects` creates a project under the requested band
- `POST /api/analyze` accepts a project identifier and persists the song into that project

**Step 2: Run test to verify it fails**

Run:
```bash
uv run --project backend pytest backend/tests/test_api.py -k "create_band or create_project or project_scoped_upload" -q
```

Expected: FAIL because the routes or request handling do not exist yet.

**Step 3: Write minimal implementation**

Implement only the route handlers and upload persistence changes needed to satisfy the tests.

**Step 4: Run test to verify it passes**

Run the same backend command and confirm it passes.

**Step 5: Commit**

```bash
git add backend/app/main.py backend/tests/test_api.py docs/plans/2026-03-10-real-frontend-no-mocks-implementation.md
git commit -m "feat: add real band project bootstrap APIs (docs/plans/2026-03-10-real-frontend-no-mocks-implementation.md)"
```

### Task 2: Implement Backend Behavior

**Files:**
- Modify: `backend/app/main.py`
- Possibly modify: `backend/app/db.py`

**Step 1: Write any missing failing backend test**

If Task 1 exposed missing edge coverage, add one minimal test before touching more code.

**Step 2: Run the targeted backend test**

Run the same `uv run --project backend pytest ...` command and confirm the new edge case fails for the right reason.

**Step 3: Implement the smallest missing backend behavior**

Keep schema reuse minimal:
- create band
- create project
- persist upload in selected project

**Step 4: Re-run backend tests**

Confirm the targeted backend tests pass.

**Step 5: Commit**

```bash
git add backend/app/main.py backend/app/db.py backend/tests/test_api.py docs/plans/2026-03-10-real-frontend-no-mocks-implementation.md
git commit -m "feat: support real project-scoped bootstrap flows (docs/plans/2026-03-10-real-frontend-no-mocks-implementation.md)"
```

### Task 3: Add Frontend API/Type Tests

**Files:**
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/lib/types.ts`
- Modify: `frontend/src/lib/__tests__/api.bands-projects.test.ts`
- Possibly modify: `frontend/src/lib/__tests__/api.stems-status.test.ts`

**Step 1: Write the failing tests**

Add tests for:
- create band API helper
- create project API helper
- upload API helper sending project id

**Step 2: Run test to verify it fails**

Run:
```bash
npm --prefix frontend test -- --run src/lib/__tests__/api.bands-projects.test.ts src/lib/__tests__/api.stems-status.test.ts
```

Expected: FAIL because helpers/types do not exist yet.

**Step 3: Write minimal implementation**

Add only the request/response shapes and helper functions required by the tests.

**Step 4: Run test to verify it passes**

Run the same frontend command and confirm it passes.

**Step 5: Commit**

```bash
git add frontend/src/lib/api.ts frontend/src/lib/types.ts frontend/src/lib/__tests__/api.bands-projects.test.ts frontend/src/lib/__tests__/api.stems-status.test.ts docs/plans/2026-03-10-real-frontend-no-mocks-implementation.md
git commit -m "feat: add real frontend bootstrap api helpers (docs/plans/2026-03-10-real-frontend-no-mocks-implementation.md)"
```

### Task 4: Add Frontend No-Mocks Tests

**Files:**
- Modify: `frontend/src/__tests__/App.integration.test.tsx`
- Modify: `frontend/src/redesign/pages/__tests__/...` as needed

**Step 1: Write the failing tests**

Add tests proving:
- empty backend state does not show mock songs/bands
- first-band creation panel appears and submits

**Step 2: Run test to verify it fails**

Run:
```bash
npm --prefix frontend test -- --run src/__tests__/App.integration.test.tsx
```

Expected: FAIL because the app still falls back to mocks and lacks the inline creation flows.

**Step 3: Write minimal implementation later**

Do not implement yet; this task establishes the red baseline for the no-mock shell and first real band flow.

**Step 4: Commit after implementation tasks are complete**

No commit yet if tests are still red and implementation is pending.

### Task 5: Implement API-Only Bootstrap and First-Band Flow

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/redesign/pages/BandSelectPage.tsx`

**Step 1: Use the failing app integration tests from Task 4**

Run the app integration command and confirm the no-mocks expectations are red.

**Step 2: Write minimal implementation**

- remove `MOCK_BANDS` fallback from runtime
- keep loaded bands empty when backend is empty
- handle loading and error states honestly
- add the inline create-band panel and refresh hierarchy after success

**Step 3: Re-run app integration tests**

Confirm the no-mocks/bootstrap assertions and first-band creation assertions pass.

**Step 4: Commit**

```bash
git add frontend/src/App.tsx frontend/src/redesign/pages/BandSelectPage.tsx frontend/src/__tests__/App.integration.test.tsx docs/plans/2026-03-10-real-frontend-no-mocks-implementation.md
git commit -m "feat: remove runtime mock fallback from bootstrap (docs/plans/2026-03-10-real-frontend-no-mocks-implementation.md)"
```

### Task 6: Add Project and Upload Frontend Tests

**Files:**
- Modify: `frontend/src/__tests__/App.integration.test.tsx`
- Modify: `frontend/src/redesign/pages/__tests__/...` as needed

**Step 1: Write the failing tests**

Add tests proving:
- project creation panel appears and submits
- upload panel submits into the selected project

**Step 2: Run test to verify it fails**

Run:
```bash
npm --prefix frontend test -- --run src/__tests__/App.integration.test.tsx
```

Expected: FAIL because project creation and upload are not wired yet.

### Task 7: Implement Inline Project Creation and Upload

**Files:**
- Modify: `frontend/src/redesign/pages/ProjectHomePage.tsx`
- Modify: `frontend/src/redesign/pages/SongLibraryPage.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/__tests__/App.integration.test.tsx`

**Step 1: Use the failing project/upload tests from Task 6**

Run the app integration command and confirm the next creation/upload assertions are failing for the expected reason.

**Step 2: Write minimal implementation**

- add inline create-project panel
- refresh route hierarchy after successful project creation
- wire actual file input
- submit upload with selected project id
- refresh selected project songs after success
- keep empty state honest when there are still no songs

**Step 3: Re-run tests**

Run the targeted app/frontend API tests and confirm they pass.

**Step 4: Commit**

```bash
git add frontend/src/redesign/pages/ProjectHomePage.tsx frontend/src/redesign/pages/SongLibraryPage.tsx frontend/src/App.tsx frontend/src/__tests__/App.integration.test.tsx docs/plans/2026-03-10-real-frontend-no-mocks-implementation.md
git commit -m "feat: add real project creation and upload flows (docs/plans/2026-03-10-real-frontend-no-mocks-implementation.md)"
```

### Task 8: Verify and Finalize

**Files:**
- Modify: `docs/plans/2026-03-10-real-frontend-no-mocks-implementation.md`

**Step 1: Run fresh verification**

Run:
```bash
uv run --project backend pytest backend/tests/test_api.py -k "create_band or create_project or project_scoped_upload" -q
npm --prefix frontend test -- --run src/lib/__tests__/api.bands-projects.test.ts src/lib/__tests__/api.stems-status.test.ts src/__tests__/App.integration.test.tsx
```

**Step 2: Run reset**

Run:
```bash
make reset
```

**Step 3: Re-run fresh verification after reset**

Run the same backend and frontend commands again.

**Step 4: Mark checklist complete**

Update this plan so all finished tasks are `[x]`.

**Step 5: Commit**

```bash
git add docs/plans/2026-03-10-real-frontend-no-mocks-implementation.md
git commit -m "docs: finalize no-mocks frontend plan state (docs/plans/2026-03-10-real-frontend-no-mocks-implementation.md)"
```
