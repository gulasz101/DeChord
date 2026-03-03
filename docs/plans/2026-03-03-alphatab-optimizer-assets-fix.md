# AlphaTab Optimizer Assets Fix

**Date:** 2026-03-03  
**Goal:** Prevent alphaTab worker/font asset load failures and related frontend instability in dev mode.

## Task Checklist

- [ ] Reproduce frontend alphaTab worker/font errors and collect root-cause evidence.
- [ ] Add TDD guard for Vite optimizer exclusion of alphaTab.
- [ ] Apply minimal Vite config fix and restart frontend runtime.
- [ ] Verify `/api/songs` and alphaTab assets resolve via `dechord.localhost`.
- [ ] Commit with plan reference.

## Task Checklist (Completed)

- [x] Reproduce frontend alphaTab worker/font errors and collect root-cause evidence.
- [x] Add TDD guard for Vite optimizer exclusion of alphaTab.
- [x] Apply minimal Vite config fix and restart frontend runtime.
- [x] Verify `/api/songs` and alphaTab assets resolve via `dechord.localhost`.
- [x] Commit with plan reference.
