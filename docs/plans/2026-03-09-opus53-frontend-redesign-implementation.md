# Opus 5-3 Frontend Redesign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace production frontend UX with `designs.opus46/5-3` page flow and visuals while extending backend/frontend to a reset multi-user multi-band multi-project model with lightweight fingerprint identity and stem download endpoints.

**Architecture:** Execute in isolated worktree branch `codex/frontend-opus46-5-3`. Implement backend schema/API foundation first, then frontend routing/layout replacement, then player/stem/download integration, with test-first delivery and small commits after each task.

**Tech Stack:** FastAPI, SQLite/libSQL schema SQL, React 19 + TypeScript + Vite, Vitest, existing DeChord backend services.

---

## Task Checklist

- [x] Task 1: Introduce reset collaboration schema and DB bootstrap updates.
- [x] Task 2: Add lightweight fingerprint identity and account-claim endpoints.
- [x] Task 3: Add bands/projects/songs listing APIs for redesigned navigation.
- [x] Task 4: Add stem download APIs (single + zip) and backend tests.
- [x] Task 5: Add frontend domain/API client for identity + band/project/song flow.
- [x] Task 6: Replace frontend app routing/layout to Opus 5-3 navigation hierarchy.
- [ ] Task 7: Refactor Song Detail and Player pages to dedicated-route model with live data.
- [ ] Task 8: Wire stem download actions + claim-account UX in frontend.
- [ ] Task 9: Add/adjust frontend tests for new route and workflow behavior.
- [ ] Task 10: Run full verification and reset workflow (`make reset`) before handoff.
- [ ] Task 11: Prepare handoff summary and send Telegram notification.

### Task 1: Reset Schema for Multi-User/Multi-Project

**Files:**
- Modify: `backend/app/db_schema.sql`
- Modify: `backend/app/db.py`
- Modify: `backend/app/models.py`
- Test: `backend/tests/test_db_bootstrap.py`

**Step 1: Write failing tests**

Add tests asserting schema includes and boots tables:
- `users`
- `user_credentials`
- `bands`
- `band_memberships`
- `projects`
- `songs` (project-scoped)
- existing song analysis artifacts linked correctly.

**Step 2: Run test to verify RED**

Run: `pytest backend/tests/test_db_bootstrap.py -q`
Expected: missing/new table assertions fail.

**Step 3: Implement minimal schema/bootstrap changes**

Update schema SQL and bootstrap mapping for the new ownership model.

**Step 4: Run test to verify GREEN**

Run: `pytest backend/tests/test_db_bootstrap.py -q`
Expected: pass.

**Step 5: Commit**

```bash
git add backend/app/db_schema.sql backend/app/db.py backend/app/models.py backend/tests/test_db_bootstrap.py
git commit -m "feat: reset collaboration schema for bands/projects (docs/plans/2026-03-09-opus53-frontend-redesign-implementation.md)"
```

### Task 2: Fingerprint Identity + Claim Account

**Files:**
- Modify: `backend/app/main.py`
- Modify: `backend/app/models.py`
- Modify: `backend/app/db.py`
- Test: `backend/tests/test_api.py`

**Step 1: Write failing API tests**

Add tests for:
- `POST /api/identity/resolve` with fingerprint token creates/returns guest.
- guest username generation shape (musician-style).
- `POST /api/identity/claim` stores username + password hash and marks claimed.

**Step 2: Run RED tests**

Run: `pytest backend/tests/test_api.py -q -k "identity or claim"`
Expected: endpoint/contract failures.

**Step 3: Implement minimal endpoints**

Implement resolve/claim handlers and persistence.

**Step 4: Run GREEN tests**

Run: `pytest backend/tests/test_api.py -q -k "identity or claim"`
Expected: pass.

**Step 5: Commit**

```bash
git add backend/app/main.py backend/app/models.py backend/app/db.py backend/tests/test_api.py
git commit -m "feat: add fingerprint guest identity and claim flow (docs/plans/2026-03-09-opus53-frontend-redesign-implementation.md)"
```

### Task 3: Bands/Projects/Songs Navigation APIs

**Files:**
- Modify: `backend/app/main.py`
- Modify: `backend/app/models.py`
- Modify: `backend/app/db.py`
- Test: `backend/tests/test_api.py`

**Step 1: Write failing tests**

Add tests for endpoints:
- `GET /api/bands`
- `GET /api/bands/{band_id}/projects`
- `GET /api/projects/{project_id}/songs`

**Step 2: Run RED tests**

Run: `pytest backend/tests/test_api.py -q -k "bands or projects or songs"`
Expected: fail.

**Step 3: Implement minimal API logic**

Add queries and response contracts for new route hierarchy.

**Step 4: Run GREEN tests**

Run: `pytest backend/tests/test_api.py -q -k "bands or projects or songs"`
Expected: pass.

**Step 5: Commit**

```bash
git add backend/app/main.py backend/app/models.py backend/app/db.py backend/tests/test_api.py
git commit -m "feat: add band project song listing APIs (docs/plans/2026-03-09-opus53-frontend-redesign-implementation.md)"
```

### Task 4: Stem Download APIs (Single + Zip)

**Files:**
- Modify: `backend/app/main.py`
- Modify: `backend/app/stems.py`
- Test: `backend/tests/test_stems.py`
- Test: `backend/tests/test_api.py`

**Step 1: Write failing tests**

Add tests for:
- single stem download endpoint.
- zip archive download endpoint including non-archived stems.

**Step 2: Run RED tests**

Run: `pytest backend/tests/test_stems.py backend/tests/test_api.py -q -k "download or stem"`
Expected: fail.

**Step 3: Implement minimal zip/download logic**

Expose endpoints and archive composition.

**Step 4: Run GREEN tests**

Run: `pytest backend/tests/test_stems.py backend/tests/test_api.py -q -k "download or stem"`
Expected: pass.

**Step 5: Commit**

```bash
git add backend/app/main.py backend/app/stems.py backend/tests/test_stems.py backend/tests/test_api.py
git commit -m "feat: support single and zip stem downloads (docs/plans/2026-03-09-opus53-frontend-redesign-implementation.md)"
```

### Task 5: Frontend Domain Types + API Client for New Hierarchy

**Files:**
- Modify: `frontend/src/lib/types.ts`
- Modify: `frontend/src/lib/api.ts`
- Add: `frontend/src/lib/__tests__/api.identity.test.ts`
- Add: `frontend/src/lib/__tests__/api.bands-projects.test.ts`

**Step 1: Write failing tests**

Test request/response helpers for identity resolve/claim and band/project/song listing.

**Step 2: Run RED tests**

Run: `npm --prefix frontend test -- api.identity api.bands-projects`
Expected: fail.

**Step 3: Implement minimal API client/types**

Add typed models + fetch wrappers for new contracts.

**Step 4: Run GREEN tests**

Run: `npm --prefix frontend test -- api.identity api.bands-projects`
Expected: pass.

**Step 5: Commit**

```bash
git add frontend/src/lib/types.ts frontend/src/lib/api.ts frontend/src/lib/__tests__/api.identity.test.ts frontend/src/lib/__tests__/api.bands-projects.test.ts
git commit -m "feat: add frontend API client for identity bands and projects (docs/plans/2026-03-09-opus53-frontend-redesign-implementation.md)"
```

### Task 6: Replace Frontend Route Shell to Opus 5-3

**Files:**
- Modify: `frontend/src/App.tsx`
- Add/Modify: `frontend/src/pages/*.tsx` (new route-driven pages)
- Modify: `frontend/src/index.css`
- Test: `frontend/src/__tests__/App.integration.test.tsx`

**Step 1: Write failing route-flow tests**

Cover navigation sequence:
- identity bootstraps guest
- band list -> project list -> song list -> song detail -> player.

**Step 2: Run RED tests**

Run: `npm --prefix frontend test -- App.integration`
Expected: fail.

**Step 3: Implement minimal route shell**

Port Opus 5-3 page composition into production app and wire API-backed navigation state.

**Step 4: Run GREEN tests**

Run: `npm --prefix frontend test -- App.integration`
Expected: pass.

**Step 5: Commit**

```bash
git add frontend/src/App.tsx frontend/src/pages frontend/src/index.css frontend/src/__tests__/App.integration.test.tsx
git commit -m "feat: adopt opus 5-3 route-driven frontend shell (docs/plans/2026-03-09-opus53-frontend-redesign-implementation.md)"
```

### Task 7: Song Detail + Dedicated Player Integration

**Files:**
- Modify: `frontend/src/pages/SongDetailPage.tsx`
- Modify: `frontend/src/pages/PlayerPage.tsx`
- Modify: `frontend/src/components/StemMixerPanel.tsx`
- Modify: `frontend/src/components/TransportBar.tsx`
- Modify: `frontend/src/components/TabViewerPanel.tsx`
- Test: `frontend/src/components/__tests__/StemMixerPanel.test.tsx`
- Test: `frontend/src/components/__tests__/TransportBarSpeed.test.tsx`

**Step 1: Write failing tests**

Add tests for:
- opening dedicated player from song detail.
- retained player controls and stem version toggles.

**Step 2: Run RED tests**

Run: `npm --prefix frontend test -- StemMixerPanel TransportBarSpeed`
Expected: fail.

**Step 3: Implement minimal page/component integration**

Ensure player remains separate route and receives full song/stem payload.

**Step 4: Run GREEN tests**

Run: `npm --prefix frontend test -- StemMixerPanel TransportBarSpeed`
Expected: pass.

**Step 5: Commit**

```bash
git add frontend/src/pages/SongDetailPage.tsx frontend/src/pages/PlayerPage.tsx frontend/src/components/StemMixerPanel.tsx frontend/src/components/TransportBar.tsx frontend/src/components/TabViewerPanel.tsx frontend/src/components/__tests__/StemMixerPanel.test.tsx frontend/src/components/__tests__/TransportBarSpeed.test.tsx
git commit -m "feat: separate song detail and player flows with opus layout (docs/plans/2026-03-09-opus53-frontend-redesign-implementation.md)"
```

### Task 8: Claim Account UX + Stem Download Actions

**Files:**
- Modify: `frontend/src/pages/BandSelectPage.tsx`
- Modify: `frontend/src/pages/SongDetailPage.tsx`
- Modify: `frontend/src/pages/PlayerPage.tsx`
- Modify: `frontend/src/lib/api.ts`
- Add/Modify tests in `frontend/src/__tests__/` or `frontend/src/components/__tests__/`

**Step 1: Write failing tests**

Add tests for:
- claim account action flow.
- single stem download click wiring.
- download-all zip wiring.

**Step 2: Run RED tests**

Run: `npm --prefix frontend test -- download claim`
Expected: fail.

**Step 3: Implement minimal UX and wiring**

Connect UI actions to new backend endpoints.

**Step 4: Run GREEN tests**

Run: `npm --prefix frontend test -- download claim`
Expected: pass.

**Step 5: Commit**

```bash
git add frontend/src/pages/BandSelectPage.tsx frontend/src/pages/SongDetailPage.tsx frontend/src/pages/PlayerPage.tsx frontend/src/lib/api.ts frontend/src/__tests__ frontend/src/components/__tests__
git commit -m "feat: add claim account and stem download actions (docs/plans/2026-03-09-opus53-frontend-redesign-implementation.md)"
```

### Task 9: Full Test Sweep and Lint

**Files:**
- Modify only as required by failures.

**Step 1: Run backend tests**

Run: `pytest backend/tests -q`

**Step 2: Run frontend tests**

Run: `npm --prefix frontend test`

**Step 3: Run frontend lint/build**

Run:
- `npm --prefix frontend run lint`
- `npm --prefix frontend run build`

**Step 4: Fix failures with TDD loop**

For each failure, add/adjust test first where behavior changed, then implement minimal fix.

**Step 5: Commit**

```bash
git add -A
git commit -m "test: stabilize redesigned app verification suite (docs/plans/2026-03-09-opus53-frontend-redesign-implementation.md)"
```

### Task 10: Reset Workflow + Final Verification

**Files:**
- None expected unless reset reveals issue.

**Step 1: Run required reset workflow**

Run: `make reset`

**Step 2: Re-run critical verification after reset**

Run:
- `pytest backend/tests/test_api.py -q`
- `npm --prefix frontend test`

**Step 3: Commit only if fixes required**

If reset uncovers required fixes, commit with plan reference.

### Task 11: Handoff and Telegram Summary

**Files:**
- Optional: handoff doc under `docs/plans/` if needed.

**Step 1: Prepare concise handoff summary**

Include:
- completed task list
- endpoint changes
- route/UI changes
- verification evidence
- known limitations.

**Step 2: Send Telegram summary notification (unless user says `skip telegram`)**

Run `ops/scripts/send-telegram-summary.sh` with credentials decrypted at send-time from:
- `ops/secrets/telegram.sops.yaml`

**Step 3: Report delivery status**

Explicitly state success/failure in final handoff.

## Execution Notes

- Keep every task initially unchecked; mark `[x]` only when fully complete.
- Commit after each completed task with this plan path in commit message.
- Execute in worktree only: `/Users/wojciechgula/Projects/DeChord/.worktrees/codex/frontend-opus46-5-3`.
- Prefer subagent-driven execution where environment supports it.
- Apply strict TDD for implementation tasks.
