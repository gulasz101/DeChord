# Spec: AGENTS.md Rewrite + Telegram Notification System

**Date:** 2026-03-15
**Status:** Approved
**Topic:** Make agent instructions unambiguous across Claude Code and OpenCode; replace behavioral Telegram compliance with script-enforced notification and user-reply loop.

---

## 1. Problem Statement

The current `AGENTS.md` contains prose rules that different models interpret differently, leading to:
- Telegram notifications silently dropped (no enforcement mechanism)
- Inconsistent commit formats across Claude Code and OpenCode sessions
- Ambiguous ordering of skills (brainstorming, plans, verification)

The fix: every rule becomes an imperative script call. Scripts don't hallucinate.

---

## 2. Architecture

Three layers:

```
AGENTS.md (instruction layer)
  └─ calls scripts by name, no logic
       ├─ ops/scripts/notify.sh           → writes TTY-scoped sentinel
       ├─ ops/scripts/ask-user-via-telegram.sh → singleton poller, returns answer
       └─ ops/scripts/send-telegram-summary.sh → sends to Telegram API (existing)

.claude/settings.json (enforcement layer)
  └─ Stop hook: globs sentinel files, sends, deletes
```

**Sentinel file:** `/tmp/dechord-notify-$(tty | tr '/' '_').pending`
- JSON: `{"title": "...", "summary": "..."}`
- Created by `notify.sh`, consumed and deleted by Stop hook
- TTY-scoped: unique per terminal window, no collision between concurrent sessions
- Created with `chmod 600` — not world-readable
- If `tty` returns non-zero (headless shell): `notify.sh` logs a warning to stderr and skips sentinel creation entirely; no file is written

**Poller lockfile:** `/tmp/dechord-telegram-ask-$(tty | tr '/' '_').lock`
- `flock -n` (non-blocking): if already locked, falls through to plain terminal input
- Held for entire script lifetime; released automatically by OS on process exit (including SIGKILL)
- **macOS note:** `flock` requires `brew install util-linux`. Scripts must check for `flock` at startup and exit with a clear error if missing.

---

## 3. Files Changed

| File | Action | Notes |
|---|---|---|
| `AGENTS.md` | Rewrite | Imperative rules only, no prose |
| `CLAUDE.md` | No change | Remains symlink → `AGENTS.md` |
| `ops/scripts/notify.sh` | Create | Writes TTY-scoped sentinel with chmod 600 |
| `ops/scripts/ask-user-via-telegram.sh` | Create | Singleton poller |
| `ops/scripts/send-telegram-summary.sh` | Minor update | Add `--sentinel-file` flag accepting JSON |
| `.claude/settings.json` | Update | Add Stop hook with absolute path resolution |

---

## 4. Script Designs

### 4.1 `notify.sh`

```
Usage: notify.sh "title" "summary body"
```

- Checks `tty` is available; if not (headless), logs warning to stderr and exits 0 without writing a file
- Resolves TTY-scoped sentinel path
- Writes JSON `{"title": ..., "summary": ...}` to sentinel with `chmod 600` (overwrites any existing — last call wins per session; see §6 for double-notify semantics)
- Exits 0; Stop hook handles the actual send
- **Stale sentinel cleanup:** on startup, `notify.sh` sweeps `/tmp/dechord-notify-*.pending` files older than 24 hours and deletes them, preventing accumulation in non-Claude-Code environments

### 4.2 `ask-user-via-telegram.sh`

```
Usage: answer=$(ops/scripts/ask-user-via-telegram.sh "Your question here?")
```

**Note:** This script is invoked to get user input at runtime. It is explicitly exempt from the `using-git-worktrees` rule — it is a notification utility, not a code-execution step.

**Prerequisite check:**
- Exits with clear error if `flock`, `sops`, `curl`, or `python3` are missing

**Singleton:**
- Acquires `flock -n` on TTY-scoped lockfile
- If lock unavailable: prints `⚠️  Telegram poller already active — answer at terminal:` and falls through to blocking `read` from stdin
- Lock released on exit (any exit path, including SIGKILL via OS fd cleanup)

**Offset file:**
- Path: `/tmp/dechord-telegram-offset-$(tty | tr '/' '_').txt` (chmod 600)
- **Always deleted at startup** — never trust a stale offset from a previously killed session
- Re-fetches current max `update_id` at startup before entering the poll loop, so pre-existing Telegram messages are never consumed as answers

**Flow:**
1. Delete any existing offset file for this TTY
2. Decrypt secrets via sops
3. Fetch current max `update_id` from Telegram; store as baseline in offset file (chmod 600)
4. Send question to Telegram: `❓ [Question]\nRepo: <name>\nBranch: <branch>`
5. Record `start_time`
6. Loop every 30 seconds until 2-hour wall-clock timeout:
   - Non-blocking stdin check (`read -t 1`)
   - Telegram long-poll: `GET /getUpdates?offset=<last+1>&timeout=25`
   - Filter responses to only accept messages from the configured `chat_id`
   - First result (stdin or Telegram) wins
7. On answer received:
   - Send Telegram confirmation: `✅ Got it! Forwarding to agent — continuing work...`
   - Echo answer to stdout
   - Delete offset file
   - Exit 0 (releases lock)
8. On 2-hour timeout:
   - Print to stderr: `⚠️  Telegram timeout reached — waiting at terminal`
   - Delete offset file
   - Fall through to blocking `read` from stdin

### 4.3 `send-telegram-summary.sh` (update)

Add `--sentinel-file PATH` flag:
- Reads JSON sentinel: extracts `title` and `summary`
- Equivalent to passing `--title` + `--summary-file` but from a single JSON source
- Existing flags unchanged (backwards compatible)

### 4.4 Stop Hook (`.claude/settings.json`)

```json
{
  "hooks": {
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "bash -c 'TTY_ID=$(tty 2>/dev/null | tr \"/\" \"_\") || exit 0; sentinel=\"/tmp/dechord-notify-${TTY_ID}.pending\"; [ -f \"$sentinel\" ] || exit 0; REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0; \"$REPO_ROOT/ops/scripts/send-telegram-summary.sh\" --sentinel-file \"$sentinel\" && rm -f \"$sentinel\"; exit 0'"
          }
        ]
      }
    ]
  }
}
```

**Notes:**
- `tty` failure (headless) → exits 0 silently; no sentinel means no send
- Uses `git rev-parse --show-toplevel` for absolute path to script — no cwd assumption
- Exits 0 on all paths to avoid blocking Claude Code session end
- Hook failure is logged to stderr; in headless CI environments this may be discarded (acceptable trade-off; no secondary failure marker needed at this scope)
- **Prohibition scope clarification:** the AGENTS.md rule "never call `send-telegram-summary.sh` directly" applies to agent instructions only. The Stop hook is infrastructure code, not an agent instruction, and may call the script directly.

---

## 5. AGENTS.md Rewrite

### Structure (XML sections preserved)

```xml
<agents>
  <section id="branching-and-commits">
    <rule>Work on main by default. No feature branches unless explicitly directed.</rule>
    <rule>Each task commit message MUST include: plan path, task number, CLI name, model name.
      Format: type(scope): description [plan: path, Task N, cli: name, model: name]
      This format applies to all commits from this point forward. Existing commits are grandfathered.
    </rule>
    <rule>After push: add clickable commit link to the completed task in the plan file.</rule>
    <rule>Delegate commit message writing and plan link updates to a subagent. Never do in main session.</rule>
  </section>

  <section id="plans-and-tasks">
    <rule>All progress tracked in docs/plans/ as XML with phase blocks and task checkboxes: [ ] pending, [x] done.</rule>
    <rule>docs/plans/ is the source of truth. Never contradict it.</rule>
  </section>

  <section id="skills-and-execution">
    <rule>Order is mandatory for any feature or bugfix: brainstorming → writing-plans → executing-plans (or subagent-driven-development for same-session work). No step may be skipped.</rule>
    <rule>Before any code execution step: invoke using-git-worktrees. Exception: notification scripts (ops/scripts/notify.sh, ops/scripts/ask-user-via-telegram.sh) are exempt from this rule.</rule>
    <rule>For all features and bugfixes: follow test-driven-development skill before writing implementation code.</rule>
    <rule>Default to subagent execution. Keep the controller session lean.</rule>
    <rule>Use context-mode MCP tools for all large output. Never pipe large results into main context.</rule>
  </section>

  <section id="notification">
    <rule>When user input is needed: run ops/scripts/ask-user-via-telegram.sh "question" and use its stdout as the answer.</rule>
    <rule>When a task is complete or a summary is ready: run ops/scripts/notify.sh "title" "summary". The Stop hook sends it at session end.</rule>
    <rule>Never call ops/scripts/send-telegram-summary.sh directly from agent instructions. Always use notify.sh or ask-user-via-telegram.sh.</rule>
  </section>

  <section id="reset-and-verification">
    <rule>Before final handoff: run make reset. Then invoke verification-before-completion skill. Both required, in this order.</rule>
    <rule>After verification passes: run ops/scripts/notify.sh with the final summary. Stop hook delivers it at session end.</rule>
  </section>

  <section id="architecture">
    <rule>Frontend: React 19, Vite, Tailwind v4.</rule>
    <rule>Backend: FastAPI, Python 3.13+, uv, LibSQL, Demucs stem/analysis pipeline.</rule>
    <rule>Flow: upload → optional stems → bass_analysis.wav → TabPipeline → MIDI/AlphaTex/tabs.</rule>
    <rule>Key directories: frontend/, backend/, docs/plans/. designs.* are reference-only, never modify.</rule>
    <rule>Never persist binary assets to filesystem. All blobs in LibSQL. Temp files in OS temp dirs only, deleted immediately after use.</rule>
  </section>

  <section id="portless">
    <rule>Local routing via portless. Use: make up, make backend, make frontend, make portless-proxy-up, make portless-proxy-down, make portless-routes.</rule>
  </section>

  <section id="design-language">
    <rule>Canonical look and feel: designs.opus46/5-3. All designs.* directories are reference-only. Never modify them.</rule>
  </section>
</agents>
```

---

## 6. Design Decisions & Edge Cases

### Double-notify semantics
If an agent calls `notify.sh` twice before session end, the second call overwrites the first. Only the final notification is delivered. This is intentional: the session-end summary should reflect the final state, not intermediate steps. Agents should compose a complete summary in a single `notify.sh` call.

### Sentinel accumulation in non-Claude-Code environments
When running in OpenCode or another CLI without the Stop hook, `notify.sh` still writes the sentinel. The file is never consumed. `notify.sh` performs a startup sweep deleting sentinel files older than 24 hours to prevent `/tmp` accumulation.

### flock on macOS
`flock` is not in macOS base system. Scripts check for it at startup and print a clear installation message (`brew install util-linux`) on failure. Alternative: `mkdir`-based locking as fallback if flock absent.

---

## 7. Error Handling

| Scenario | Behaviour |
|---|---|
| sops decryption fails | Script exits non-zero, prints error, agent falls back to terminal |
| Telegram API unreachable | Poller logs warning per iteration, continues until timeout, then falls back to terminal |
| Sentinel write fails (disk full etc.) | `notify.sh` exits non-zero, agent logs warning, session ends without notification |
| Stop hook fails | Exits 0 to not block Claude Code session end; error logged to stderr |
| Two sessions same TTY | Impossible by OS design |
| Poller already running (same TTY) | Non-blocking flock fails gracefully, falls through to terminal input |
| Headless shell / no TTY | `notify.sh` and Stop hook detect `tty` failure, skip silently, exit 0 |
| Stale offset file from SIGKILL | Deleted unconditionally at poller startup; next run re-fetches baseline update_id |
| Sentinel exists but no Stop hook (OpenCode) | Swept by `notify.sh` startup cleanup after 24h |
| Message from wrong chat_id received | Ignored by poller; loop continues |
| `flock` not installed (macOS) | Script prints install instructions, exits non-zero |
| Stop hook path wrong (wrong cwd) | Resolved via `git rev-parse --show-toplevel` — cwd-independent |

---

## 8. Testing Plan

1. **notify.sh unit:** call script, verify sentinel created with correct JSON and `chmod 600`; call again, verify overwrite (double-notify semantics)
2. **notify.sh headless:** run with `tty` mocked to fail; verify no sentinel written, exits 0
3. **notify.sh stale cleanup:** place a sentinel older than 24h in `/tmp`; run notify.sh; verify stale file deleted
4. **ask-user singleton:** start two instances concurrently; verify second falls through to terminal immediately without blocking
5. **ask-user stdin race:** send question; type answer at terminal before any Telegram reply; verify stdout captures terminal answer
6. **ask-user Telegram race:** send question; reply via Telegram from configured chat_id; verify stdout captures Telegram answer and confirmation message sent
7. **ask-user wrong chat_id:** send reply from a different chat_id; verify it is ignored and loop continues
8. **ask-user SIGKILL recovery:** start poller, SIGKILL it, verify offset file deleted on next startup and no old messages consumed
9. **ask-user timeout:** reduce timeout to 10s for test; verify fallback to blocking `read` and warning on stderr
10. **Stop hook:** write sentinel manually with correct JSON; trigger hook; verify Telegram message received and sentinel deleted
11. **Stop hook headless:** run hook in subshell with no TTY; verify exits 0, no error, no send attempted
12. **flock missing:** remove flock from PATH; run ask-user script; verify clear error message printed

---

## 9. Out of Scope

- Telegram message threading / reply-to (flat messages only)
- Multi-question queue (one in-flight question at a time by design)
- OpenCode-specific hooks (OpenCode relies on AGENTS.md instructions; scripts are portable)
- Telegram bot webhook mode (polling is simpler and sufficient)
- Secondary failure markers for Stop hook failures
