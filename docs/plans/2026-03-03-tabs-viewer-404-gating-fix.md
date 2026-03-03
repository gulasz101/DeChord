# Tabs Viewer 404 Gating Fix

**Date:** 2026-03-03  
**Goal:** Prevent tab viewer 404s when no generated tab artifact exists and expose tab artifact availability via API metadata.

## Task Checklist

- [ ] Reproduce and confirm root cause (`/tabs/file` requested with empty `song_tabs`).
- [x] Add backend tab metadata endpoint with tests.
- [x] Add frontend API/client gating so tab viewer loads only when metadata exists.
- [x] Verify backend/frontend tests pass and confirm no direct 404 request on song load without tabs.
- [x] Commit with plan reference.

## Task Checklist (Completed)

- [x] Reproduce and confirm root cause (`/tabs/file` requested with empty `song_tabs`).
- [ ] Add backend tab metadata endpoint with tests.
- [ ] Add frontend API/client gating so tab viewer loads only when metadata exists.
- [ ] Verify backend/frontend tests pass and confirm no direct 404 request on song load without tabs.
- [ ] Commit with plan reference.
