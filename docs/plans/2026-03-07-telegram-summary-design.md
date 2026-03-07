# Telegram Summary Notifications Design

- [x] Confirm the completion-summary trigger and Telegram destination with the user.
- [x] Choose the secret storage and delivery architecture.
- [x] Document the approved design for repo changes under `ops/` and `AGENTS.md`.

## Goal

Send a short Telegram summary to the user's private chat whenever Codex finishes a job and has a handoff summary, unless the user explicitly says `skip telegram`.

## Approved Design

- Trigger delivery from the final handoff event, not from git commits or per-task plan updates.
- Store Telegram credentials in `ops/secrets/telegram.sops.yaml`, committed only in encrypted form.
- Keep repository workflow scripts under `ops/scripts/`, starting with `ops/scripts/send-telegram-summary.sh`.
- Keep `AGENTS.md` declarative: it should define when to send, where secrets live, and the `skip telegram` override, but never contain plaintext secrets.
- Message content should stay phone-friendly: job context, work summary, verification status, and whether follow-up is needed.

## Notes

- The repo already enforces plan tracking and `make reset`; the Telegram workflow should fit into that existing handoff process.
- Strict TDD applies to the sender workflow implementation. Secret provisioning itself is configuration, so it can only be validated through decryption and end-to-end delivery checks.
