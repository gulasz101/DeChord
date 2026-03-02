# Stems Quality Engine Correction Plan

**Goal:** Restore high-quality stem extraction by using Demucs as the default engine and disabling automatic low-quality fallback unless explicitly enabled.

### Task 1: Add correction plan and commit

- [x] Step 1: Create this plan file under `docs/plans/`.
- [x] Step 2: Commit with plan reference.

### Task 2: TDD fix stem engine defaults and fallback behavior

**Files:**
- Modify: `backend/tests/test_stems.py`
- Modify: `backend/app/stems.py`

- [ ] Step 1: Add RED tests proving default path prefers demucs and fallback requires explicit opt-in.
- [ ] Step 2: Run targeted tests and confirm RED.
- [ ] Step 3: Implement default demucs engine and opt-in fallback-on-error behavior.
- [ ] Step 4: Run targeted tests and confirm GREEN.
- [ ] Step 5: Commit with plan reference.

### Task 3: Verification and plan completion

- [ ] Step 1: Run `cd backend && uv run pytest tests/test_stems.py -q`.
- [ ] Step 2: Mark all plan tasks complete.
