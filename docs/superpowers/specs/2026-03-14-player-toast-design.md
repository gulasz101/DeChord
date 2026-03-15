# Player Toast Redesign — Spec

**Date:** 2026-03-14
**Status:** Approved
**Scope:** `frontend/src/redesign/components/ToastCueLayer.tsx` + `PlayerPage.tsx` toast wiring

---

## Goal

Replace the unstyled bare `<div>` toasts with a polished, animated toast stack that appears in the **top-left corner** of the player during playback. Notes fire as coloured gradient banners, slide in from the left, stack newest-on-top, and fade out when their `toastDurationSec` expires.

---

## Visual Design

- **Style:** Coloured gradient banner — high contrast, readable at a glance while focused on the song.
- **Size:** Max width `340px`, `border-radius: 10px`, padding `10px 14px`.
- **Author name:** Shown above the note text in `10px` bold uppercase, `0.8` opacity.
- **Note text:** `13px`, `line-height: 1.45`, white.
- **Shadow:** `0 8px 32px rgba(0,0,0,0.5)` for depth.

### Author Colour System

8 preset gradients assigned by `authorName` hash. Same author always gets the same colour, no config needed.

| Index | Gradient |
|-------|----------|
| 0 | `#7c3aed → #4f46e5` (violet → indigo) |
| 1 | `#0e7490 → #0284c7` (cyan → blue) |
| 2 | `#be185d → #9333ea` (pink → purple) |
| 3 | `#065f46 → #0d9488` (emerald → teal) |
| 4 | `#b45309 → #d97706` (amber) |
| 5 | `#1d4ed8 → #0ea5e9` (blue → sky) |
| 6 | `#9f1239 → #e11d48` (rose) |
| 7 | `#4d7c0f → #16a34a` (lime → green) |

Hash function: sum of char codes modulo 8.

```ts
function authorGradientIndex(name: string): number {
  return name.split('').reduce((acc, c) => acc + c.charCodeAt(0), 0) % 8;
}
```

---

## Animation

### Entry — `slideInLeft`
```css
@keyframes slideInLeft {
  from { transform: translateX(-110%); opacity: 0; }
  to   { transform: translateX(0);     opacity: 1; }
}
```
Duration: `0.28s`, easing: `cubic-bezier(0.22, 1, 0.36, 1)` (fast settle, no bounce).

### Exit — `fadeOut`
Triggered by adding a CSS class `.toast-exiting` when the toast is scheduled for removal.
```css
@keyframes fadeOut {
  from { opacity: 1; }
  to   { opacity: 0; transform: scale(0.97); }
}
```
Duration: `0.35s ease`. The component removes the toast from state after the animation completes (`animationend` event or `setTimeout(350)`).

---

## Stacking Behaviour

- Container: `position: fixed; top: 16px; left: 16px` — always on top of the player.
- Layout: `display: flex; flex-direction: column-reverse; gap: 8px` — newest toast appears at the **top** naturally without JS reorder.
- **Max 5 toasts.** When a 6th fires, the oldest (bottom of the array) is removed immediately before the new one is added.
- `pointer-events: none` on the container — toasts never block player interaction.

---

## Data Interface Changes

The `Toast` interface gains `authorName`:

```ts
interface Toast {
  id: number;
  text: string;
  authorName: string;   // NEW — used for gradient assignment and label
}
```

`PlayerPage` already has `note.authorName` available on each note. It must be forwarded when pushing to `activeToasts`:

```ts
setActiveToasts((prev) => [
  ...prev,
  { id: toastId, text: note.text, authorName: note.authorName ?? 'Unknown' },
]);
```

---

## Component Structure

### `ToastCueLayer.tsx` (full rewrite)

Responsibilities:
1. Render a fixed top-left container.
2. Map each toast to a gradient-banner `<div>` with `slideInLeft` entry animation.
3. Handle exit: when a toast is marked for removal by `PlayerPage` (removed from `toasts` prop), trigger `fadeOut` via a local `exiting` set before deletion — **or** accept an `exitingIds: Set<number>` prop from the parent.

**Recommended exit strategy:** The parent (`PlayerPage`) manages a separate `exitingToastIds: Set<number>` state. On timeout, it adds the id to `exitingIds`, waits 350 ms, then removes it from `activeToasts`. `ToastCueLayer` applies `.toast-exiting` class when `exitingIds.has(toast.id)`.

### No new dependencies

All animation via CSS keyframes + Tailwind utility classes where possible. No Framer Motion.

---

## Files to Change

| File | Change |
|------|--------|
| `frontend/src/redesign/components/ToastCueLayer.tsx` | Full rewrite — styled, animated, author gradient |
| `frontend/src/redesign/pages/PlayerPage.tsx` | Add `authorName` to `activeToasts` push; add `exitingToastIds` state and exit logic |
| `frontend/src/redesign/components/__tests__/ToastCueLayer.test.tsx` | New or updated tests |

The legacy `frontend/src/components/ToastCueLayer.tsx` is unrelated and should not be touched.

---

## Testing

- Render 1–5 toasts → verify all visible with correct author names and `data-testid`.
- Render 6 toasts in sequence → oldest is absent from the DOM.
- Toast with a known `authorName` → verify correct gradient class applied.
- Exit: after `toastDurationSec` elapses (fake timers) → toast is removed from DOM.
- `pointer-events: none` on container → does not intercept click events.

---

## Out of Scope

- Click-to-dismiss on toasts.
- Hover-to-pause the dismiss timer.
- Toast position configuration (always top-left).
- Any changes to the comment modal, timeline lane, or backend.
