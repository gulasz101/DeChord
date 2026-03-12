# Hardening and Finish Design

**Date:** 2026-03-10

## XML Tracking

<phase id="hardening-finish-design" status="completed">
  <task>[x] Task 1: Define the finish-level reliability and hygiene promise.</task>
  <task>[x] Task 2: Compare hardening approaches and recommend the reliability-first slice.</task>
  <task>[x] Task 3: Specify architecture and data flow for runtime artifact hygiene, startup/reset behavior, verification posture, and narrow cleanup of misleading leftovers.</task>
  <task>[x] Task 4: Capture testing strategy, manual verification expectations, done criteria, and warning-vs-green rules.</task>
</phase>

## Product Promise

DeChord should finish this program by becoming reliable to restart, reliable to verify, and honest about what survives a reset. After `make reset` and `make up`, the app should boot from a clean runtime state, recreate the directories it needs, serve the real product without stale local leftovers, and surface truthful copy when reset removed in-flight work. The repository should also stop pointing active plans and verification commands at misleading leftovers that no longer exist.

For this slice, success means:
- startup recreates required runtime directories without depending on manual pre-seeding
- targeted verification can be rerun after `make reset` with the same commands and expected outcomes
- active plan and verification docs stop referencing stale test names or misleading checks
- the product stays honest that reset removes transient jobs and results instead of pretending they are recoverable

## Scope

This slice is intentionally reliability-first and cleanup-light.

In scope:
- centralize runtime artifact path ownership for `backend/uploads`, `backend/stems`, and `backend/cache`
- make backend startup/reset behavior explicit and repeatable, including replacing deprecated startup wiring if it pollutes verification output
- harden frontend reset-loss messaging so lost jobs/results are explained clearly and do not leave misleading in-progress copy behind
- normalize active documentation and verification references that point at outdated test names or similarly misleading leftovers
- define one finish-quality verification gate for the slice

Out of scope:
- durable job persistence, job resume, retry queues, or cancellation infrastructure
- a broader repository refactor, toolchain migration, or CI rebuild
- new deployment infrastructure, containers, hosted services, or background workers
- large UX redesigns unrelated to reset honesty or verification repeatability

## Current State

What already exists:
- `make reset` removes the local DB plus generated uploads, stems, and cache state
- `backend/app/main.py` already creates `uploads` and `stems` directories and initializes the DB on startup
- `frontend/src/App.tsx` already maps reset-driven `404` responses into user-facing processing errors
- focused verification commands for each completed slice are already recorded in the master plan

What is still brittle or misleading:
- runtime directory creation is split between import-time side effects, lazy file writes, and `make reset`, which is harder to reason about than one explicit bootstrap path
- backend verification still carries FastAPI `@app.on_event(...)` deprecation noise, which weakens finish-level verification clarity
- reset-loss copy is honest at the error-string level but can still preserve stale journey-stage messaging from before the reset
- active planning docs still include at least one outdated test reference: `TransportBarSpeed.test.tsx` no longer exists, while the real test file is `frontend/src/components/__tests__/TransportBar.transport.test.tsx`

## Approaches Considered

### Approach 1: Finish with verification docs only

Behavior:
- update the plan text and quality gate language
- leave runtime bootstrap and reset-loss handling as-is

Pros:
- smallest change set
- fast to land

Cons:
- leaves real runtime fragility untouched
- keeps warning noise in the finish gate
- would document known brittleness instead of reducing it

### Approach 2: Reliability and hygiene first with narrow cleanup

Behavior:
- centralize runtime path bootstrap in backend code
- move startup/shutdown wiring to a reset-safe lifecycle path
- add focused tests for runtime bootstrap and reset-loss UX behavior
- clean active docs that still reference outdated verification artifacts

Pros:
- matches the approved direction exactly
- improves both product behavior and repository hygiene without adding infrastructure
- creates a trustworthy final verification posture for Task 14

Cons:
- spans backend, frontend, and docs in one slice
- needs discipline to avoid turning cleanup into a broad refactor

### Approach 3: Broader architectural hardening

Behavior:
- add persistent jobs, resumable processing, richer health checks, and CI-like automation in one pass

Pros:
- ambitious end state

Cons:
- violates the guidance to keep defaults portable and avoid unnecessary infrastructure
- risks reopening product-surface work instead of tightening the finish line
- too large for the last slice in this program

## Recommendation

Use **Approach 2: reliability and hygiene first with narrow cleanup**.

This is the smallest slice that improves trust in the finished product. It makes runtime bootstrap explicit, makes reset behavior more honest, removes misleading active references, and gives the final verification step a cleaner signal without introducing new infrastructure.

## Architecture and Data Flow

### 1. Runtime artifact hygiene should have one owner

Generated local artifacts stay under the existing backend runtime tree:
- database: `backend/dechord.db`
- uploads: `backend/uploads/`
- stems: `backend/stems/`
- analysis cache: `backend/cache/`

Recommended direction:
- introduce one backend-owned runtime-path helper, for example in `backend/app/runtime.py`
- compute the existing default locations there and keep them portability-friendly relative to the backend workspace
- expose a single `ensure_runtime_dirs()` path used during app startup
- stop relying on import-time directory creation as the primary bootstrap mechanism

Data-flow rule:
1. `make reset` removes local runtime artifacts
2. backend startup initializes the DB and recreates required runtime directories
3. upload, stem generation, and cached analysis writes only target those known runtime roots
4. `.gitignore` remains the repository boundary that keeps those artifacts out of version control

Why this matters:
- reset safety becomes deterministic
- local runtime state is easier to reason about
- future cleanup work has one place to inspect instead of several side effects

### 2. Startup and shutdown should use an explicit lifecycle path

`backend/app/main.py` currently initializes the DB with `@app.on_event("startup")` and closes it with `@app.on_event("shutdown")`.

Recommended direction:
- move DB init, runtime-dir bootstrap, and DB close into a FastAPI lifespan handler
- keep startup work narrow: only what is required for local boot correctness
- do not add model downloads, background warmups, or heavyweight readiness checks

Finish rule:
- a clean local boot after `make reset` must not depend on leftover directories from a previous run
- targeted verification should not be polluted by avoidable lifecycle deprecation warnings from code we control

### 3. Reset honesty must be visible in the processing journey

Reset deletes runtime state. That is acceptable for this slice, but the product must describe it accurately.

Recommended frontend behavior in `frontend/src/App.tsx`:
- if `GET /api/status/{job_id}` or `GET /api/result/{job_id}` returns reset-loss `404`, convert the journey to a stable error state
- replace stale in-progress copy with reset-specific copy that explains what happened and what the user can do next
- stop implying that the job can still finish if the runtime state has already been wiped

Intentionally not in this slice:
- recovering lost in-progress jobs
- persisting the in-memory job table across reset or restart
- retry orchestration beyond user-driven re-upload or manual refresh

### 4. Final verification should separate green requirements from warning-only posture

The finish slice needs an explicit rule for what must pass and what may remain warning-only.

Must be green for this slice:
- runtime bootstrap tests for directory creation and lifecycle wiring
- frontend reset-loss integration coverage
- the focused hardening verification commands before reset and after `make reset` / `make up`
- active master-plan references updated to current test/file names

Warning-only for this slice:
- the existing frontend Vite chunk-size warning for `alphaTab`, as long as build succeeds
- reset destroying in-flight processing jobs and results, because the product will state that limitation honestly rather than hiding it
- optional deep pipeline or benchmark suites outside the focused hardening gate

Not acceptable as warning-only:
- missing runtime directories after reset
- startup lifecycle deprecation noise from code we are actively touching in this slice
- active docs that direct engineers to nonexistent tests or misleading verification commands

### 5. Cleanup should be narrow and source-of-truth oriented

Cleanup in this slice is not general repo polishing. It is limited to misleading leftovers that affect execution or verification.

Known narrow cleanup target:
- replace active references to `frontend/src/components/__tests__/TransportBarSpeed.test.tsx` with `frontend/src/components/__tests__/TransportBar.transport.test.tsx`

Cleanup rule:
- prioritize the master plan and any still-used execution docs
- do not rewrite historical documents unless they are still acting as live instructions for this program

## Testing Strategy

### Backend tests

- extend `backend/tests/test_db_bootstrap.py`
- cover runtime directory creation for missing `uploads`, `stems`, and `cache`
- cover the explicit lifecycle path so startup/shutdown no longer rely on deprecated event hooks

### Frontend integration tests

- extend `frontend/src/__tests__/App.integration.test.tsx`
- cover reset-loss `404` handling for processing status/result fetches
- assert the journey ends in truthful reset-specific copy instead of stale progress messaging

### Documentation hygiene checks

- use targeted search commands against the active plan files to prove outdated test references are gone
- keep this cleanup narrow and explicit rather than broad repository churn

## Manual Verification Expectations

Use the standard local shell flow.

Manual checks:
- run `make reset`, then run `make up` as a separate runtime-start step, confirm frontend/backend readiness from the real shell, and only then run post-reset verification checks
- verify the local runtime directories exist again under `backend/`
- start a processing journey, reset local state, then confirm the UI explains that the job/result was lost after reset instead of looking stuck or still active
- rerun the focused hardening checks after reset and confirm the expected green/warning-only posture still matches the plan

## Done Criteria

This slice is done when:
- backend startup owns runtime directory bootstrap explicitly and repeatably
- targeted verification no longer carries avoidable startup-hook deprecation noise from the hardening code path
- processing-journey reset-loss behavior is honest and stable in the UI
- active slice docs no longer point at nonexistent verification files
- the hardening quality gate is documented clearly enough for Task 13 and Task 14 to execute without extra repo archaeology

## Risks and Deferred Work

- Durable processing-job persistence is still deferred. The slice should make that limitation explicit instead of inventing a half-persistent system.
- Historical plan files may still mention outdated paths; only active source-of-truth docs should be normalized here.
- Runtime bootstrap can sprawl into configuration work quickly. Keep the helper local and default-friendly rather than adding environment-heavy indirection.
- Some warnings are intentionally tolerated. The plan must clearly distinguish those from true blockers so finish verification stays credible.

## Decision Summary

- centralize runtime artifact bootstrap under backend ownership
- replace deprecated startup/shutdown wiring with an explicit lifecycle path
- make reset-loss UX fully honest instead of partially honest
- clean only the misleading active references that affect execution
- treat `alphaTab` build warnings as warning-only, but require runtime bootstrap and active verification docs to be green
