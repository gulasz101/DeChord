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

end of AGENTS.md
