<agents>
  <section id="branching-and-commits">
    <rule>Work on main by default and ignore backward compatibility unless explicitly requested; avoid feature branches unless directed; keep commits small and atomic to ease revert.</rule>
    <rule>Complete each task with a commit that references its plan path in docs/plans/, the specific task, the tool name opencode, and the model gpt-5.1-codex-max.</rule>
    <rule>After pushes, add clickable commit links to completed tasks in the plan so plan and history stay cross-referenced.</rule>
    <rule>Delegate commit message curation and plan commit-link updates to a subagent subprocess to keep the main context lean.</rule>
  </section>
  <section id="plans-and-tasks">
    <rule>Track all progress in docs/plans/ using XML with &lt;phase&gt; blocks and &lt;task&gt;[ ] ...&lt;/task&gt; entries; tasks start unchecked and move to [x] when done.</rule>
    <rule>Plans and design documents in docs/plans/ are the source of truth for execution history.</rule>
  </section>
  <section id="skills-and-execution">
    <rule>Apply the 1% trigger rule: invoke brainstorming, writing-plans, subagent-driven-development (same session) or executing-plans (parallel session), using-git-worktrees before execution, test-driven-development, and verification-before-completion whenever possibly relevant.</rule>
    <rule>Default to subagent execution to keep the controller lean; run Telegram and final handoff summaries in subagents.</rule>
    <rule>Follow TDD for all tasks; if TDD or subagent-driven development cannot apply, explicitly state why.</rule>
  </section>
  <section id="reset-and-verification">
    <rule>Run make reset before final verification or handoff and again before any Telegram send so checks start from a fresh runtime state.</rule>
    <rule>Use verification-before-completion to confirm cleanliness and test status before final summaries or Telegram.</rule>
  </section>
  <section id="telegram">
    <step>Send Telegram summaries by default after verification unless the user says skip telegram; dispatch a subagent to send only once reset/verification are complete.</step>
    <step>Use ops/scripts/send-telegram-summary.sh; decrypt secrets from ops/secrets/telegram.sops.yaml only at send time and never expose them.</step>
    <step>Prefix messages with CLI: opencode | Model: gpt-5.1-codex-max - ... and include upbeat emojis plus generous spacing in the message body; report any delivery failures.</step>
    <step>Send Telegram only after reset and verification steps complete.</step>
  </section>
  <section id="architecture">
    <rule>Frontend: React 19 with Vite and Tailwind v4.</rule>
    <rule>Backend: FastAPI on Python 3.13+ with uv, LibSQL, and a Demucs-based stem/analysis pipeline.</rule>
    <rule>Flow: upload -> optional stems -> bass_analysis.wav -> TabPipeline -> outputs (MIDI, AlphaTex, tabs).</rule>
    <rule>Key directories: frontend/, backend/, docs/plans/, and designs.* as reference snapshots only.</rule>
  </section>
  <section id="portless">
    <rule>Use portless as the standard local routing layer; prefer make up, make backend, make frontend, make portless-proxy-up, make portless-proxy-down, and make portless-routes.</rule>
  </section>
  <section id="design-language">
    <rule>Follow designs.opus46/5-3 as the canonical look and feel; designs.* directories preserve the initial configured design languages for reference and must remain unchanged; treat other designs.* directories as reference-only and do not modify them.</rule>
  </section>
</agents>
