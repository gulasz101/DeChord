# Designs Player Alignment Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Rework the five standalone design prototypes so they follow a realistic signed-out-to-player flow and reuse the existing DeChord player anatomy with design-specific styling.

**Architecture:** Rebuild `designs/1` as the canonical journey-first app, copy the aligned playback primitives into the other prototype directories, then theme each design with its own tokens and presentation. The prototypes remain standalone Bun + Vite + React + TypeScript + Tailwind apps with mocked data only.

**Tech Stack:** Bun, Vite, React 19, TypeScript, Tailwind CSS 4, alphaTab

---

## Task Checklist

- [ ] Add the player-alignment redesign plan and execution checklist.
- [x] Rebuild prototype `designs/1` around a realistic signed-out-to-player journey and aligned playback components.
- [x] Re-theme prototype `designs/2` with the new journey and aligned playback components.
- [x] Re-theme prototype `designs/3` with the new journey and aligned playback components.
- [x] Re-theme prototype `designs/4` with the new journey and aligned playback components.
- [x] Re-theme prototype `designs/5` with the new journey and aligned playback components.
- [ ] Verify all five rebuilt prototypes build and boot independently on port `3001`.
- [ ] Run `make reset` before final handoff.
- [ ] Send the Telegram summary after verification.

## Prototype Exception Notes

- The user still wants mocked review prototypes only.
- TDD is still intentionally skipped for this redesign pass because these apps remain disposable visual/product explorations.
- Subagent-driven development is not available in this environment, so implementation will proceed directly as a fallback.
