# Designs Prototype Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build five self-contained mocked frontend prototype apps under `designs/1` through `designs/5`, each covering the same DeChord collaboration flow with a different design language.

**Architecture:** Each prototype is a standalone Bun + Vite + React + TypeScript + Tailwind app with its own source tree, local mock data, route shell, and styling tokens. The five apps intentionally duplicate structure so design exploration remains independent and disposable.

**Tech Stack:** Bun, Vite, React 19, TypeScript, Tailwind CSS 4

---

## Task Checklist

- [x] Create the `designs/` directory structure and decide the standalone app template shape.
- [x] Scaffold prototype `designs/1` with Bun, Vite, React, TypeScript, and Tailwind.
- [x] Build prototype `designs/1` screens and styling around the IBM-inspired design language.
- [x] Scaffold prototype `designs/2` and adapt it to the DAW-inspired design language.
- [x] Scaffold prototype `designs/3` and adapt it to the editorial modern design language.
- [x] Scaffold prototype `designs/4` and adapt it to the Scandinavian instrument-lab design language.
- [ ] Scaffold prototype `designs/5` and adapt it to the live-performance design language.
- [ ] Verify each prototype can run independently with Bun on port `3001` from its own directory.
- [ ] Run the local reset workflow before final verification.
- [ ] Prepare final handoff summary and send the Telegram notification unless the user opts out.

## Prototype Exception Notes

- The user explicitly requested no tests for these review-only prototypes.
- Because these are disposable mocked design explorations, TDD is not being applied for this task.
- If that changes later and one or more designs are promoted into production work, TDD should resume for the real integration work.

### Task 1: Create the Designs Workspace

**Files:**
- Create: `designs/`
- Create: `designs/README.md`

**Step 1: Create the root workspace description**

Write `designs/README.md` describing:

- purpose of the prototypes
- how to run each design with Bun
- that each app is intentionally standalone

**Step 2: Commit**

```bash
git add designs/README.md docs/plans/2026-03-08-designs-prototype-implementation.md
git commit -m "docs: add designs prototype implementation plan (docs/plans/2026-03-08-designs-prototype-implementation.md)"
```

### Task 2: Scaffold Prototype 1

**Files:**
- Create: `designs/1/package.json`
- Create: `designs/1/bun.lock`
- Create: `designs/1/index.html`
- Create: `designs/1/tsconfig.json`
- Create: `designs/1/tsconfig.app.json`
- Create: `designs/1/tsconfig.node.json`
- Create: `designs/1/vite.config.ts`
- Create: `designs/1/postcss.config.js` if required by the chosen Tailwind setup
- Create: `designs/1/src/main.tsx`
- Create: `designs/1/src/App.tsx`
- Create: `designs/1/src/index.css`
- Create: `designs/1/src/mock/data.ts`
- Create: `designs/1/src/components/*`

**Step 1: Scaffold the Bun/Vite/Tailwind app**

Use the existing `frontend/` app as a reference for package versions and Vite/Tailwind conventions, but keep the design app independent.

**Step 2: Establish shared mocked routes**

Mock screens for:

- landing
- auth
- bands/projects switcher
- project dashboard
- song library
- song detail
- player

**Step 3: Implement IBM-inspired styling**

Apply:

- structured grid
- neutral palette with a restrained accent
- disciplined typography
- enterprise-style content blocks

**Step 4: Run the app**

Run:

```bash
bun install
bun run dev -- --host 0.0.0.0 --port 3001
```

Expected: Vite starts successfully and serves prototype 1 on port `3001`.

**Step 5: Commit**

```bash
git add designs/1
git commit -m "feat: add prototype design 1 (docs/plans/2026-03-08-designs-prototype-implementation.md)"
```

### Task 3: Scaffold Prototype 2

**Files:**
- Create: `designs/2/*`

**Step 1: Duplicate the standalone app structure**

Create a fresh standalone app under `designs/2` without introducing shared code dependencies on `designs/1`.

**Step 2: Rebuild the same mocked product flow**

Carry over the same route set and mock concepts:

- bands
- projects
- songs
- collaborators
- comments
- stems
- statuses

**Step 3: Implement DAW-inspired styling**

Apply:

- darker control surfaces
- track-lane organization
- transport-first player
- stronger stem/mixer visual treatment

**Step 4: Run the app**

Run:

```bash
bun install
bun run dev -- --host 0.0.0.0 --port 3001
```

Expected: Vite starts successfully and serves prototype 2 on port `3001`.

**Step 5: Commit**

```bash
git add designs/2
git commit -m "feat: add prototype design 2 (docs/plans/2026-03-08-designs-prototype-implementation.md)"
```

### Task 4: Scaffold Prototype 3

**Files:**
- Create: `designs/3/*`

**Step 1: Create the standalone app**

Scaffold the full Bun/Vite/Tailwind app under `designs/3`.

**Step 2: Recreate the shared mocked flow**

Keep the same route list and core interactions for comparability.

**Step 3: Implement editorial modern styling**

Apply:

- stronger typography
- more asymmetry
- cleaner marketing storytelling on landing
- crisp, high-legibility collaboration views

**Step 4: Run the app**

Run:

```bash
bun install
bun run dev -- --host 0.0.0.0 --port 3001
```

Expected: Vite starts successfully and serves prototype 3 on port `3001`.

**Step 5: Commit**

```bash
git add designs/3
git commit -m "feat: add prototype design 3 (docs/plans/2026-03-08-designs-prototype-implementation.md)"
```

### Task 5: Scaffold Prototype 4

**Files:**
- Create: `designs/4/*`

**Step 1: Create the standalone app**

Scaffold the full Bun/Vite/Tailwind app under `designs/4`.

**Step 2: Recreate the shared mocked flow**

Keep the shared route structure, data concepts, and playback information density.

**Step 3: Implement Scandinavian instrument-lab styling**

Apply:

- calm light surfaces
- natural tones
- reduced chrome
- clear, quiet collaboration panels

**Step 4: Run the app**

Run:

```bash
bun install
bun run dev -- --host 0.0.0.0 --port 3001
```

Expected: Vite starts successfully and serves prototype 4 on port `3001`.

**Step 5: Commit**

```bash
git add designs/4
git commit -m "feat: add prototype design 4 (docs/plans/2026-03-08-designs-prototype-implementation.md)"
```

### Task 6: Scaffold Prototype 5

**Files:**
- Create: `designs/5/*`

**Step 1: Create the standalone app**

Scaffold the full Bun/Vite/Tailwind app under `designs/5`.

**Step 2: Recreate the shared mocked flow**

Keep the same information architecture and mocked product model.

**Step 3: Implement live-performance styling**

Apply:

- bolder high-contrast presentation
- more kinetic accents
- sharper emphasis around transport, activity, and collaboration moments

**Step 4: Run the app**

Run:

```bash
bun install
bun run dev -- --host 0.0.0.0 --port 3001
```

Expected: Vite starts successfully and serves prototype 5 on port `3001`.

**Step 5: Commit**

```bash
git add designs/5
git commit -m "feat: add prototype design 5 (docs/plans/2026-03-08-designs-prototype-implementation.md)"
```

### Task 7: Final Verification

**Files:**
- Modify: `docs/plans/2026-03-08-designs-prototype-implementation.md`

**Step 1: Verify all five prototypes boot**

Run each from its own directory:

```bash
bun install
bun run dev -- --host 0.0.0.0 --port 3001
```

Expected: each design starts independently on port `3001` when run from its own directory.

**Step 2: Run the local reset workflow**

Run:

```bash
make reset
```

Expected: local runtime state is reset before final handoff.

**Step 3: Mark completed tasks**

Update the checklist in this plan file from `[ ]` to `[x]` for each finished task.

**Step 4: Commit final execution status**

```bash
git add docs/plans/2026-03-08-designs-prototype-implementation.md designs
git commit -m "chore: finalize designs prototype execution (docs/plans/2026-03-08-designs-prototype-implementation.md)"
```
