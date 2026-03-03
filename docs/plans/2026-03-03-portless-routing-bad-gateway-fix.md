# Portless Routing Bad Gateway Fix Plan

**Goal:** Fix `Bad Gateway` after `make up` by ensuring backend/frontend bind to the exact host/port assigned by `portless`.

### Task 1: Track root cause and plan

- [x] Step 1: Create this plan file with unchecked tasks.
- [x] Step 2: Commit with plan path reference.

### Task 2: TDD-style routing fix in Makefile

**Files:**
- Modify: `Makefile`

- [x] Step 1: Confirm RED by reproducing `502` on `http://dechord.localhost:1355` and `http://api.dechord.localhost:1355/api/health`.
- [x] Step 2: Update backend command to defer `$HOST/$PORT` expansion to child shell so portless env is honored.
- [x] Step 3: Update frontend command to pass `--host "$HOST" --port "$PORT"` to Vite.
- [x] Step 4: Restart stack and confirm GREEN with successful HTTP responses.
- [x] Step 5: Commit with plan path reference.

### Task 3: Final verification and completion

- [ ] Step 1: Run `make status` and `portless list` and confirm both dechord routes are active.
- [ ] Step 2: Mark plan complete and commit with plan path reference.
