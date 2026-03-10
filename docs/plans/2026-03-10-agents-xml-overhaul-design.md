# AGENTS XML Overhaul Design

<phase>Context and Goals</phase>
<task>[x] Capture the objectives for an XML-driven, single-source AGENTS.md.</task>
<task>[x] Record the branch policy favoring main with atomic commits.</task>
<task>[x] Note mandated subagent-first execution and lean controller context.</task>

<phase>Scope</phase>
<task>[x] Define required sections: execution rules, skills triggers, plan/task XML, Telegram, architecture, portless, design language.</task>
<task>[x] Include commit/message cross-linking and reset/verification expectations.</task>

## Design

- Wrap the document in a single `<agents>` root with `<section id="...">` children; individual rules use `<rule>` or `<step>` tags. Keep content concise and avoid stray markdown outside the XML frame.
- Plans and designs must store phases as `<phase>` and tasks as `<task>[ ] ...</task>` in `docs/plans/`; progression from `[ ]` to `[x]` remains the source of truth.
- Branch policy: operate on `main` by default for local, fast-moving work; ignore backward compatibility unless explicitly requested. Avoid feature branches unless a human directs otherwise. Keep commits small and atomic to enable easy revert.
- Commit and traceability: every completed task requires a commit that references the plan path, the task, the tool (`opencode`), and model (`gpt-5.1-codex-max`). Each completed task entry in the plan must add a clickable commit link after push to enable GitHub review.
- Skills and subagent enforcement: apply the 1% rule to trigger skills (brainstorming, writing-plans, subagent-driven-development or executing-plans, using-git-worktrees before execution, test-driven-development, verification-before-completion). Default to subagents for execution to keep the main agent lean; Telegram work and final handoff summaries run in subagents.
- Architecture overview: summarize frontend (React 19/Vite/Tailwind v4), backend (FastAPI, Python 3.13+, uv, LibSQL, Demucs-based stem/analysis pipeline), and flow (upload → optional stems → `bass_analysis.wav` → TabPipeline → MIDI/AlphaTex/tabs). List key directories: `frontend/`, `backend/`, `docs/plans/`, and `designs.*` as reference snapshots.
- Portless usage: document portless as the standard local routing/proxy layer; align with Make targets (`make up`, `make backend`, `make frontend`, `make portless-proxy-up`, `make portless-proxy-down`, `make portless-routes`) and instruct agents to use portless commands when starting services or debugging routing.
- Design language: state that `designs.opus46/5-3` is the canonical, chosen design language for look-and-feel; agents should follow this reference when implementing UI work. Other `designs.*` directories remain reference-only and must not be modified.
- Telegram rules: messages start with `CLI: opencode | Model: gpt-5.1-codex-max – …`, use emoji-friendly spacing, send only after verification via `ops/scripts/send-telegram-summary.sh` from a subagent, decrypt secrets from `ops/secrets/telegram.sops.yaml` only at send time, never print secrets, and report delivery failures.
- Reset/verification: run `make reset` before final verification/handoff. Use verification-before-completion to confirm tests and cleanliness before Telegram or final summary.
