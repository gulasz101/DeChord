# Subagent Summary Routing Design

- [ ] Confirm the desired delegation policy for handoff summaries and Telegram delivery.
- [ ] Define how subagents should handle summary preparation, SOPS decryption, and notification sending.
- [ ] Document the approved instruction change for future jobs.

## Goal

Keep the main agent context lean by delegating final-summary preparation and Telegram notification work to subagents whenever the environment supports subagents.

## Approved Design

- Final handoff summaries should be prepared by a subagent when possible.
- Telegram notification work, including SOPS decryption and API delivery, should also run in a subagent when possible.
- The main agent should fall back to doing this work itself only when subagents are unavailable in the environment.
- The instructions should treat this as a default routing rule for future tasks, not an ad-hoc optimization.
