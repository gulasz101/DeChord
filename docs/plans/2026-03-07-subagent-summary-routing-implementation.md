# Subagent Summary Routing Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Update repo instructions so final-summary preparation and Telegram delivery are delegated to subagents by default, with fallback to the main agent only when subagents are unavailable.

**Architecture:** This is an instruction-only change in `AGENTS.md`. No runtime code changes are required because the existing Telegram workflow already exists; only the routing policy for how future agents should execute it changes.

**Tech Stack:** Markdown instructions

---

### Task 1: Track the design and implementation work

**Files:**
- Create: `docs/plans/2026-03-07-subagent-summary-routing-design.md`
- Create: `docs/plans/2026-03-07-subagent-summary-routing-implementation.md`

- [ ] Step 1: Add the approved design doc for subagent-based summary routing.
- [ ] Step 2: Add this implementation plan.
- [ ] Step 3: Commit the planning artifacts with a commit message that references `docs/plans/2026-03-07-subagent-summary-routing-implementation.md`.

### Task 2: Update the repo instruction policy

**Files:**
- Modify: `AGENTS.md`

- [ ] Step 1: Update the completion-notification rules so final-summary preparation, SOPS decryption, and Telegram delivery must be delegated to a subagent whenever the environment supports subagents.
- [ ] Step 2: Add an explicit fallback rule allowing the main agent to do the work only when subagents are unavailable.
- [ ] Step 3: Commit the instruction update with a commit message that references `docs/plans/2026-03-07-subagent-summary-routing-implementation.md`.

### Task 3: Final verification and completion

**Files:**
- Modify: `docs/plans/2026-03-07-subagent-summary-routing-design.md`
- Modify: `docs/plans/2026-03-07-subagent-summary-routing-implementation.md`

- [ ] Step 1: Run `make reset`.
- [ ] Step 2: Mark the completed plan tasks as `[x]`.
- [ ] Step 3: Commit the final verification updates with a commit message that references `docs/plans/2026-03-07-subagent-summary-routing-implementation.md`.
