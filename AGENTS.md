# AGENTS.md

## Execution and Progress Rules

- All progress MUST be tracked in Markdown plan files under `docs/plans/`.
- Every new task must start unchecked as `[ ]`.
- When a task is finished, it MUST be marked done as `[x]` in the relevant plan file.
- Task completion status in plans is the source of truth for execution history.

## Commit and Traceability Rules

- After finishing each task, commit the changes.
- Every task commit message MUST reference a specific plan path in `docs/plans/` so history is cross-referenced.
- Commit history and plan files together MUST provide a complete execution overview.

## Required Development Method

- All tasks and activities (including research) MUST use subagent-driven development and test-driven development (TDD).
- If subagent-driven development or TDD cannot be applied in a specific case, explicitly inform the user and explain why.

## Reset and Verification Rules

- After finishing development work and before final verification/handoff, run the local reset workflow (`make reset`) so testing starts from a fresh runtime state.

## Completion Notification Rules

- After finishing any job that has a final handoff summary, send a Telegram summary notification by default.
- Skip the Telegram notification only when the user explicitly says `skip telegram`.
- The Telegram notification MUST be sent after the required verification flow for that job is complete.
- Use `ops/scripts/send-telegram-summary.sh` to deliver the message.
- Telegram credentials MUST be loaded from the SOPS-encrypted file `ops/secrets/telegram.sops.yaml` and decrypted only at send time.
- Never print, commit, or persist plaintext Telegram secrets.
- If Telegram delivery fails, explicitly report that in the final handoff.


end of AGENTS.md
