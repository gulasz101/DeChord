# Telegram Summary Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add repo-managed Telegram handoff notifications that decrypt bot credentials from SOPS at send time and default to sending unless the user says `skip telegram`.

**Architecture:** Add a small `ops/scripts/` delivery script that decrypts `ops/secrets/telegram.sops.yaml`, formats a plain-text Telegram message, and posts it via the Bot API. Update `AGENTS.md` so final handoffs default to sending Telegram summaries, and cover the script with a focused pytest regression test that stubs `sops` and `curl`.

**Tech Stack:** Bash, SOPS with age, Telegram Bot API, pytest, Python stdlib subprocess helpers

---

### Task 1: Track the design and execution plan

**Files:**
- Create: `docs/plans/2026-03-07-telegram-summary-design.md`
- Create: `docs/plans/2026-03-07-telegram-summary-implementation.md`

- [x] Step 1: Add the approved design doc with Telegram delivery decisions.
- [x] Step 2: Add this implementation plan with explicit execution and verification tasks.
- [x] Step 3: Commit the planning artifacts with a commit message that references `docs/plans/2026-03-07-telegram-summary-implementation.md`.

### Task 2: Write the failing delivery-script test

**Files:**
- Create: `backend/tests/test_telegram_summary_script.py`

- [x] Step 1: Write a pytest case that stubs `sops` and `curl`, runs `ops/scripts/send-telegram-summary.sh`, and asserts the script posts the composed summary using decrypted `bot_token` and `chat_id`.
- [x] Step 2: Run `cd backend && uv run pytest tests/test_telegram_summary_script.py -v` and verify the new test fails for the expected missing-script behavior.
- [x] Step 3: Commit the failing test with a commit message that references `docs/plans/2026-03-07-telegram-summary-implementation.md`.

### Task 3: Implement the Telegram notification workflow

**Files:**
- Create: `ops/.sops.yaml`
- Create: `ops/scripts/send-telegram-summary.sh`
- Create: `ops/secrets/telegram.sops.example.yaml`
- Create: `ops/secrets/telegram.sops.yaml`
- Modify: `AGENTS.md`

- [x] Step 1: Add the SOPS configuration and encrypted/example Telegram secret files under `ops/secrets/`.
- [x] Step 2: Implement `ops/scripts/send-telegram-summary.sh` with `--title`, `--summary-file`, `--skip`, and runtime SOPS decryption.
- [x] Step 3: Update `AGENTS.md` so Telegram summaries are the default final-handoff behavior unless the user says `skip telegram`.
- [x] Step 4: Run `cd backend && uv run pytest tests/test_telegram_summary_script.py -v` and verify the test passes.
- [x] Step 5: Commit the workflow implementation with a commit message that references `docs/plans/2026-03-07-telegram-summary-implementation.md`.

### Task 4: Final verification and live delivery check

**Files:**
- Modify: `docs/plans/2026-03-07-telegram-summary-design.md`
- Modify: `docs/plans/2026-03-07-telegram-summary-implementation.md`

- [x] Step 1: Run `make reset`.
- [x] Step 2: Re-run `cd backend && uv run pytest tests/test_telegram_summary_script.py -v`.
- [x] Step 3: Run `ops/scripts/send-telegram-summary.sh` against the encrypted secret file to send a real setup-complete Telegram message to chat `5471749508`.
- [x] Step 4: Mark all completed plan tasks as `[x]`.
- [x] Step 5: Commit the final verification updates with a commit message that references `docs/plans/2026-03-07-telegram-summary-implementation.md`.
