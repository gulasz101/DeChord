# Player Toast Redesign Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the unstyled bare-div toasts with animated gradient-banner toasts that slide in from the top-left, stack newest-on-top (max 5), show author name in per-author gradient colour, and fade out on dismiss.

**Architecture:** `ToastCueLayer` is rewritten to own all visual/animation logic. `PlayerPage` gains an `exitingToastIds` state set and forwards `authorName` to each active toast. All animation is pure CSS keyframes — no new dependencies.

**Tech Stack:** React 19, TypeScript, Tailwind v4, Vitest + React Testing Library, CSS keyframes.

**Spec:** `docs/superpowers/specs/2026-03-14-player-toast-design.md`

---

## Chunk 1: ToastCueLayer rewrite

### Task 1: Rewrite `ToastCueLayer` with styling, animation, and author gradient

**Files:**
- Modify: `frontend/src/redesign/components/ToastCueLayer.tsx`
- Create: `frontend/src/redesign/components/__tests__/ToastCueLayer.test.tsx`

---

- [ ] **Step 1: Write failing tests**

Create `frontend/src/redesign/components/__tests__/ToastCueLayer.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import "@testing-library/jest-dom";
import { describe, expect, it } from "vitest";
import { ToastCueLayer } from "../ToastCueLayer";

const baseToasts = [
  { id: 1, text: "try the bass lower", authorName: "Wojciech" },
  { id: 2, text: "tension resolves to Dm", authorName: "Anna" },
];

describe("ToastCueLayer", () => {
  it("renders all toasts with their text", () => {
    render(<ToastCueLayer toasts={baseToasts} exitingIds={new Set()} />);
    expect(screen.getByText("try the bass lower")).toBeInTheDocument();
    expect(screen.getByText("tension resolves to Dm")).toBeInTheDocument();
  });

  it("renders author names", () => {
    render(<ToastCueLayer toasts={baseToasts} exitingIds={new Set()} />);
    expect(screen.getByText("Wojciech")).toBeInTheDocument();
    expect(screen.getByText("Anna")).toBeInTheDocument();
  });

  it("applies data-testid per toast id", () => {
    render(<ToastCueLayer toasts={baseToasts} exitingIds={new Set()} />);
    expect(screen.getByTestId("toast-1")).toBeInTheDocument();
    expect(screen.getByTestId("toast-2")).toBeInTheDocument();
  });

  it("applies toast-exiting class to toasts in exitingIds", () => {
    render(<ToastCueLayer toasts={baseToasts} exitingIds={new Set([1])} />);
    expect(screen.getByTestId("toast-1").className).toMatch(/toast-exiting/);
    expect(screen.getByTestId("toast-2").className).not.toMatch(/toast-exiting/);
  });

  it("container has pointer-events-none so it never blocks player clicks", () => {
    const { container } = render(
      <ToastCueLayer toasts={baseToasts} exitingIds={new Set()} />
    );
    const wrapper = container.firstChild as HTMLElement;
    expect(wrapper.className).toMatch(/pointer-events-none/);
  });

  it("assigns a deterministic gradient class based on author name", () => {
    render(<ToastCueLayer toasts={[{ id: 1, text: "x", authorName: "Wojciech" }]} exitingIds={new Set()} />);
    // "Wojciech" hash: sum of char codes % 8 — must be stable across renders
    const toast = screen.getByTestId("toast-1");
    // gradient class follows pattern toast-gradient-{0-7}
    expect(toast.className).toMatch(/toast-gradient-\d/);
  });
});
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd /Users/wojciechgula/Projects/DeChord/frontend
bun run test src/redesign/components/__tests__/ToastCueLayer.test.tsx
```

Expected: multiple failures — `exitingIds` prop not accepted, no gradient classes, no author rendering.

- [ ] **Step 3: Rewrite `ToastCueLayer.tsx`**

Replace the entire file `frontend/src/redesign/components/ToastCueLayer.tsx`:

```tsx
import "./ToastCueLayer.css";

export interface Toast {
  id: number;
  text: string;
  authorName: string;
}

interface ToastCueLayerProps {
  toasts: Toast[];
  exitingIds: Set<number>;
}

/** Sum of char codes mod 8 — deterministic, no config needed. */
function authorGradientIndex(name: string): number {
  return name.split("").reduce((acc, c) => acc + c.charCodeAt(0), 0) % 8;
}

export function ToastCueLayer({ toasts, exitingIds }: ToastCueLayerProps) {
  return (
    <div className="toast-container pointer-events-none">
      {toasts.map((toast) => {
        const gradientIdx = authorGradientIndex(toast.authorName);
        const isExiting = exitingIds.has(toast.id);
        return (
          <div
            key={toast.id}
            data-testid={`toast-${toast.id}`}
            className={[
              "toast",
              `toast-gradient-${gradientIdx}`,
              isExiting ? "toast-exiting" : "",
            ]
              .filter(Boolean)
              .join(" ")}
          >
            <span className="toast-author">{toast.authorName}</span>
            <span className="toast-text">{toast.text}</span>
          </div>
        );
      })}
    </div>
  );
}
```

- [ ] **Step 4: Create `ToastCueLayer.css`**

Create `frontend/src/redesign/components/ToastCueLayer.css`:

```css
/* Container — fixed top-left, newest toast at top via col-reverse */
.toast-container {
  position: fixed;
  top: 16px;
  left: 16px;
  display: flex;
  flex-direction: column-reverse;
  gap: 8px;
  width: 340px;
  z-index: 9999;
}

/* Individual toast */
.toast {
  display: flex;
  flex-direction: column;
  gap: 3px;
  border-radius: 10px;
  padding: 10px 14px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
  animation: slideInLeft 0.28s cubic-bezier(0.22, 1, 0.36, 1) both;
}

.toast.toast-exiting {
  animation: fadeOut 0.35s ease forwards;
}

/* Author label */
.toast-author {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.07em;
  text-transform: uppercase;
  opacity: 0.8;
  color: #fff;
}

/* Note text */
.toast-text {
  font-size: 13px;
  line-height: 1.45;
  color: #fff;
}

/* 8 author gradients */
.toast-gradient-0 { background: linear-gradient(135deg, #7c3aed, #4f46e5); }
.toast-gradient-1 { background: linear-gradient(135deg, #0e7490, #0284c7); }
.toast-gradient-2 { background: linear-gradient(135deg, #be185d, #9333ea); }
.toast-gradient-3 { background: linear-gradient(135deg, #065f46, #0d9488); }
.toast-gradient-4 { background: linear-gradient(135deg, #b45309, #d97706); }
.toast-gradient-5 { background: linear-gradient(135deg, #1d4ed8, #0ea5e9); }
.toast-gradient-6 { background: linear-gradient(135deg, #9f1239, #e11d48); }
.toast-gradient-7 { background: linear-gradient(135deg, #4d7c0f, #16a34a); }

/* Entry animation */
@keyframes slideInLeft {
  from { transform: translateX(-110%); opacity: 0; }
  to   { transform: translateX(0);     opacity: 1; }
}

/* Exit animation */
@keyframes fadeOut {
  from { opacity: 1; }
  to   { opacity: 0; transform: scale(0.97); }
}
```

- [ ] **Step 5: Run tests — expect all to pass**

```bash
cd /Users/wojciechgula/Projects/DeChord/frontend
bun run test src/redesign/components/__tests__/ToastCueLayer.test.tsx
```

Expected: all 6 tests PASS.

- [ ] **Step 6: Commit**

```bash
cd /Users/wojciechgula/Projects/DeChord
git add frontend/src/redesign/components/ToastCueLayer.tsx \
        frontend/src/redesign/components/ToastCueLayer.css \
        frontend/src/redesign/components/__tests__/ToastCueLayer.test.tsx
git commit -m "feat(player): redesign ToastCueLayer — gradient banners, slide-in, author colour [plan: 2026-03-14-player-toast-redesign, Task 1, claude-code, claude-sonnet-4-6]"
```

---

## Chunk 2: PlayerPage wiring

### Task 2: Wire `exitingToastIds` state and `authorName` forwarding in `PlayerPage`

**Files:**
- Modify: `frontend/src/redesign/pages/PlayerPage.tsx`
- Modify: `frontend/src/redesign/pages/__tests__/PlayerPage.test.tsx`

---

- [ ] **Step 1: Write failing tests**

In `frontend/src/redesign/pages/__tests__/PlayerPage.test.tsx`, add to the existing describe block (or create a new one):

```tsx
// Add these imports if not already present:
// import { vi, describe, it, expect, beforeEach } from "vitest";
// import { render, screen, act } from "@testing-library/react";
// import { PlayerPage } from "../PlayerPage";

describe("PlayerPage — toast authorName forwarding", () => {
  it("includes authorName in active toast when note fires", async () => {
    // Arrange: song with one timed note at 0s
    const song = makeSong({
      notes: [
        {
          id: 42,
          text: "bend up here",
          authorName: "Wojciech",
          timestampSec: 0,
          toastDurationSec: 5,
          resolved: false,
          userId: 1,
        },
      ],
    });

    // Render player and tick time to 0.1s so the note fires
    const { unmount } = render(
      <PlayerPage song={song} onBack={vi.fn()} currentUserId={1} />
    );

    // advance simulated playback time — implementation detail:
    // PlayerPage checks currentTime in a useEffect; fire the effect manually
    // by fast-forwarding timers if needed, or check the DOM directly
    await act(async () => {
      vi.advanceTimersByTime(100);
    });

    // The toast should be rendered with data-testid="toast-42"
    // and contain "Wojciech" as the author label
    expect(screen.getByTestId("toast-42")).toBeInTheDocument();
    expect(screen.getByText("Wojciech")).toBeInTheDocument();

    unmount();
  });

  it("removes toast from DOM after toastDurationSec + exit animation (350ms)", async () => {
    const song = makeSong({
      notes: [
        {
          id: 99,
          text: "fade me out",
          authorName: "Anna",
          timestampSec: 0,
          toastDurationSec: 1,
          resolved: false,
          userId: 2,
        },
      ],
    });

    render(<PlayerPage song={song} onBack={vi.fn()} currentUserId={1} />);

    await act(async () => {
      vi.advanceTimersByTime(100); // fire note
    });
    expect(screen.getByTestId("toast-99")).toBeInTheDocument();

    await act(async () => {
      vi.advanceTimersByTime(1000 + 350 + 50); // duration + fade + buffer
    });
    expect(screen.queryByTestId("toast-99")).not.toBeInTheDocument();
  });
});
```

Note: `makeSong` is a test helper — check if one already exists in the test file; if not, add a minimal one:

```tsx
function makeSong(overrides: Partial<Song> = {}): Song {
  return {
    id: 1,
    title: "Test Song",
    artist: "Test",
    notes: [],
    stems: [],
    ...overrides,
  } as Song;
}
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd /Users/wojciechgula/Projects/DeChord/frontend
bun run test src/redesign/pages/__tests__/PlayerPage.test.tsx
```

Expected: failures on `authorName` not in toast DOM / toast not removed.

- [ ] **Step 3: Update `PlayerPage.tsx` — add `authorName` to toast push**

In `frontend/src/redesign/pages/PlayerPage.tsx`, find the block that calls `setActiveToasts` when a note fires (around line 260–266). Change:

```ts
setActiveToasts((prev) => [...prev, { id: toastId, text: note.text }]);
```

to:

```ts
setActiveToasts((prev) => [
  ...prev,
  { id: toastId, text: note.text, authorName: note.authorName ?? "Unknown" },
]);
```

- [ ] **Step 4: Add `exitingToastIds` state and two-phase exit**

Still in `PlayerPage.tsx`:

1. Add state near the top of the component (alongside `activeToasts`):

```ts
const [exitingToastIds, setExitingToastIds] = useState<Set<number>>(new Set());
```

2. Replace the `setTimeout` that removes a toast with a two-phase version:

Find:
```ts
setTimeout(() => {
  setActiveToasts((prev) => prev.filter((t) => t.id !== toastId));
}, note.toastDurationSec * 1000);
```

Replace with:
```ts
setTimeout(() => {
  // Phase 1: trigger fade-out animation
  setExitingToastIds((prev) => new Set([...prev, toastId]));
  // Phase 2: remove from DOM after animation completes (350ms)
  setTimeout(() => {
    setActiveToasts((prev) => prev.filter((t) => t.id !== toastId));
    setExitingToastIds((prev) => {
      const next = new Set(prev);
      next.delete(toastId);
      return next;
    });
  }, 350);
}, note.toastDurationSec * 1000);
```

3. Pass `exitingIds` to `ToastCueLayer`. Find:

```tsx
<ToastCueLayer toasts={activeToasts} />
```

Replace with:

```tsx
<ToastCueLayer toasts={activeToasts} exitingIds={exitingToastIds} />
```

- [ ] **Step 5: Update the `Toast` type import in `PlayerPage`**

`PlayerPage` declares its own `activeToasts` state. Make sure the type matches the updated `Toast` interface (with `authorName`). If `PlayerPage` has an inline type for `activeToasts`, update it:

```ts
// Before (if inline):
const [activeToasts, setActiveToasts] = useState<{ id: number; text: string }[]>([]);

// After:
const [activeToasts, setActiveToasts] = useState<{ id: number; text: string; authorName: string }[]>([]);
```

Or import the exported `Toast` type from `ToastCueLayer`:

```ts
import { ToastCueLayer, type Toast as ActiveToast } from "../components/ToastCueLayer";
// then:
const [activeToasts, setActiveToasts] = useState<ActiveToast[]>([]);
```

- [ ] **Step 6: Handle max-5 eviction**

Find where `activeToasts` is updated when a new toast is pushed. After the existing `prev.filter(...)` dedup, add the max-5 eviction:

```ts
setActiveToasts((prev) => {
  const deduped = prev.filter((t) => t.id !== toastId);
  const capped = deduped.length >= 5 ? deduped.slice(1) : deduped; // evict oldest
  return [...capped, { id: toastId, text: note.text, authorName: note.authorName ?? "Unknown" }];
});
```

- [ ] **Step 7: Run all tests**

```bash
cd /Users/wojciechgula/Projects/DeChord/frontend
bun run test
```

Expected: all tests PASS, no regressions.

- [ ] **Step 8: Commit**

```bash
cd /Users/wojciechgula/Projects/DeChord
git add frontend/src/redesign/pages/PlayerPage.tsx \
        frontend/src/redesign/pages/__tests__/PlayerPage.test.tsx
git commit -m "feat(player): wire exitingToastIds + authorName forwarding to ToastCueLayer [plan: 2026-03-14-player-toast-redesign, Task 2, claude-code, claude-sonnet-4-6]"
```

---

## Final Verification

- [ ] Run `make reset` then full test suite:

```bash
make reset
cd frontend && bun run test
```

- [ ] Manual smoke test: start the player, play a song with timed notes, confirm:
  - Toasts slide in from left
  - Each author gets a distinct gradient
  - New toasts appear at top of stack
  - Old ones fade out after their duration
  - Never more than 5 toasts visible simultaneously
