<agents>
  <section id="branching-and-commits">
    <rule>Work on main by default. No feature branches unless explicitly directed.</rule>
    <rule>Each task commit message MUST follow this exact format:
      type(scope): description [plan: docs/plans/FILENAME.md, Task N, cli: CLI_NAME, model: MODEL_NAME]
      Examples of cli values: claude-code, opencode. Examples of model values: claude-sonnet-4-6, kimi-k2.
      This format applies to all commits going forward. Existing commits are grandfathered.
    </rule>
    <rule>After every push: add a clickable commit URL to the completed task entry in the plan file.</rule>
    <rule>Delegate commit message writing and plan link updates to a subagent subprocess. Never perform these in the main session.</rule>
    <rule>Never leave work uncommitted!</rule>
  </section>

  <section id="plans-and-tasks">
    <rule>Track all progress in docs/plans/ using XML with phase blocks and task checkboxes: [ ] for pending, [x] for done.</rule>
    <rule>docs/plans/ is the source of truth for execution history. Never contradict it.</rule>
  </section>

  <section id="skills-and-execution">
    <rule>For every feature or bugfix, invoke skills in this exact order: brainstorming → writing-plans → executing-plans (or subagent-driven-development for same-session work). No step may be skipped.</rule>
    <rule>Before any code execution step, invoke using-git-worktrees to isolate the work. Exception: ops/scripts/notify.sh and ops/scripts/ask-user-via-telegram.sh are notification utilities and are exempt from this rule.</rule>
    <rule>For all features and bugfixes, follow the test-driven-development skill before writing any implementation code.</rule>
    <rule>Default to subagent execution. Keep the controller session lean.</rule>
    <rule>Use context-mode MCP tools for all large output. Never pipe large results into the main context window.</rule>
  </section>

  <section id="notification">
    <rule>When user input is needed during a session: run ops/scripts/ask-user-via-telegram.sh "question text" and use its stdout as the answer. The script races terminal input against a Telegram reply — whichever arrives first wins.</rule>
    <rule>When a task or session is complete and a summary is ready: run ops/scripts/notify.sh "title" "summary body". The Claude Code Stop hook delivers it to Telegram at session end.</rule>
    <rule>Never call ops/scripts/send-telegram-summary.sh directly from agent instructions. Always route through notify.sh or ask-user-via-telegram.sh.</rule>
  </section>

  <section id="reset-and-verification">
    <rule>Before final handoff: run make reset, then invoke the verification-before-completion skill. Both are required and must run in this order.</rule>
    <rule>After verification passes: run ops/scripts/notify.sh "title" "final summary". The Stop hook delivers it.</rule>
  </section>

  <section id="architecture">
    <rule>Frontend: React 19, Vite, Tailwind v4.</rule>
    <rule>Backend: FastAPI, Python 3.13+, uv, LibSQL, Demucs stem/analysis pipeline.</rule>
    <rule>Flow: upload → optional stems → bass_analysis.wav → TabPipeline → MIDI/AlphaTex/tabs.</rule>
    <rule>Key directories: frontend/, backend/, docs/plans/. The designs.* directories are reference-only — never modify them.</rule>
    <rule>Never persist binary assets (audio, stems, MIDI, tabs) to the local filesystem. All blobs must be stored in LibSQL. Temporary files during processing are allowed only in OS temp dirs and must be deleted immediately after reading into memory.</rule>
  </section>

  <section id="portless">
    <rule>Use portless as the standard local routing layer. Allowed commands: make up, make backend, make frontend, make portless-proxy-up, make portless-proxy-down, make portless-routes.</rule>
  </section>

  <section id="design-language">
    <rule>The canonical look and feel is defined in designs.opus46/5-3. All designs.* directories are reference-only and must never be modified.</rule>
  </section>
</agents>
