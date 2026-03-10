# AGENTS XML Overhaul Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Rewrite `AGENTS.md` into an XML-framed, subagent-first guide that enforces main-branch, atomic commits, skill triggers, Telegram flow, portless usage, and the chosen design language from `designs.opus46/5-3`.

**Architecture:** Documentation-only change; preserves repo layout while adding clear rules for branches, plans, skills, verification, Telegram, and design references. No runtime behavior changes.

**Tech Stack:** Markdown with enforced XML tagging conventions.

---

<phase>Preparation</phase>
<task>[x] Confirm working on `main`; avoid feature branches per policy.</task>
<task>[x] Re-read `docs/plans/2026-03-10-agents-xml-overhaul-design.md` to align scope and decisions.</task>

<phase>Document Update</phase>
<task>[x] Snapshot current `AGENTS.md` context for reference.</task>
<task>[x] Rewrite `AGENTS.md` within an `<agents>` root and `<section>` children; convert rules into `<rule>`/`<step>` entries.</task>
<task>[x] Add main-branch/atomic-commit policy and cross-link commits from tasks (plan entries must link commits after push).</task>
<task>[x] Encode XML plan/task format (`<phase>`, `<task>[ ] ...</task>`) and plan storage rules under `docs/plans/`.</task>
<task>[x] Tighten skill triggers: brainstorming, writing-plans, subagent-driven-development or executing-plans, using-git-worktrees, test-driven-development, verification-before-completion (1% rule), default subagent execution.</task>
<task>[x] Expand Telegram section with emoji-friendly intro (`CLI: opencode | Model: gpt-5.1-codex-max - ...`), subagent-only sending, secrets handling, failure reporting.</task>
<task>[x] Add architecture overview (frontend/backend/flow/key dirs) and portless usage with Make targets.</task>
<task>[x] Add design language directive: follow `designs.opus46/5-3` as canonical look/feel; treat other `designs.*` as reference-only.</task>
<task>[x] Include reset/verification flow (`make reset` before final verification) and Telegram ordering.</task>

<phase>Verification and Traceability</phase>
<task>[x] Self-review `AGENTS.md` for completeness, XML correctness, and alignment with design doc.</task>
<task>[x] Run `make reset` (required before final verification/handoff).</task>
<task>[x] Update this plan’s tasks to `[x]` as completed.</task>
<task>[x] Commit with message referencing this plan path, the touched task, tool `opencode`, and model `gpt-5.1-codex-max`.</task>
<task>[ ] Push to enable clickable commit link in the plan.</task>
<task>[ ] Dispatch subagent to send Telegram summary after verification.</task>
