# Band & Project Creation UX Fix — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix two broken creation flows — add a ghost "Create new band…" card that always appears in the band list, and move project creation into a modal so the "New" button in the project sidebar always works.

**Architecture:** Pure frontend changes in two components. No new files, no backend changes, no API changes. All state, handlers, and API wiring already exist — only rendering logic changes.

**Tech Stack:** React 19, TypeScript, Vitest, @testing-library/react, Tailwind v4

**Spec:** `docs/superpowers/specs/2026-03-15-band-project-creation-ux-fix.md`

---

## Chunk 1: BandSelectPage — ghost card + Enter key

---

### Task 1: Write failing tests for BandSelectPage band creation

**Files:**
- Create: `frontend/src/redesign/pages/__tests__/BandSelectPage.creation.test.tsx`

- [x] **Step 1: Create the test file**

```tsx
// frontend/src/redesign/pages/__tests__/BandSelectPage.creation.test.tsx
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { BandSelectPage } from "../BandSelectPage";
import type { Band, User } from "../../lib/types";

const user: User = {
  id: "1",
  name: "Alice",
  email: "alice@example.com",
  instrument: "Bass",
  avatar: "A",
};

const band: Band = {
  id: "1",
  name: "Shredders",
  avatarColor: "#7c3aed",
  projects: [],
  members: [],
};

describe("BandSelectPage — additional band creation", () => {
  it("does NOT render the ghost card when no bands exist", () => {
    render(
      <BandSelectPage user={user} bands={[]} onSelectBand={() => {}} onSignOut={() => {}} />,
    );
    expect(screen.queryByText(/create new band/i)).toBeNull();
  });

  it("renders ghost card when at least one band exists", () => {
    render(
      <BandSelectPage user={user} bands={[band]} onSelectBand={() => {}} onSignOut={() => {}} />,
    );
    expect(screen.getByText(/create new band/i)).toBeTruthy();
  });

  it("clicking the ghost card shows the inline creation form", () => {
    render(
      <BandSelectPage user={user} bands={[band]} onSelectBand={() => {}} onSignOut={() => {}} />,
    );
    fireEvent.click(screen.getByText(/create new band/i));
    expect(screen.getByLabelText("Band Name")).toBeTruthy();
  });

  it("Cancel hides the form and restores the ghost card", () => {
    render(
      <BandSelectPage user={user} bands={[band]} onSelectBand={() => {}} onSignOut={() => {}} />,
    );
    fireEvent.click(screen.getByText(/create new band/i));
    fireEvent.click(screen.getByText(/cancel/i));
    expect(screen.queryByLabelText("Band Name")).toBeNull();
    expect(screen.getByText(/create new band/i)).toBeTruthy();
  });

  it("submitting the form calls onCreateBand with the trimmed name", async () => {
    const onCreateBand = vi.fn().mockResolvedValue(undefined);
    render(
      <BandSelectPage
        user={user}
        bands={[band]}
        onSelectBand={() => {}}
        onSignOut={() => {}}
        onCreateBand={onCreateBand}
      />,
    );
    fireEvent.click(screen.getByText(/create new band/i));
    fireEvent.change(screen.getByLabelText("Band Name"), { target: { value: "  New Band  " } });
    fireEvent.click(screen.getByRole("button", { name: /save band/i }));
    await vi.waitFor(() => expect(onCreateBand).toHaveBeenCalledWith({ name: "New Band" }));
  });

  it("Enter key in the name input submits the form", async () => {
    const onCreateBand = vi.fn().mockResolvedValue(undefined);
    render(
      <BandSelectPage
        user={user}
        bands={[band]}
        onSelectBand={() => {}}
        onSignOut={() => {}}
        onCreateBand={onCreateBand}
      />,
    );
    fireEvent.click(screen.getByText(/create new band/i));
    fireEvent.change(screen.getByLabelText("Band Name"), { target: { value: "New Band" } });
    fireEvent.keyDown(screen.getByLabelText("Band Name"), { key: "Enter" });
    await vi.waitFor(() => expect(onCreateBand).toHaveBeenCalledWith({ name: "New Band" }));
  });

  it("Save Band button is disabled while a save is in flight", () => {
    let resolveCreate!: () => void;
    const onCreateBand = vi.fn().mockReturnValue(
      new Promise<void>((r) => { resolveCreate = r; }),
    );
    render(
      <BandSelectPage
        user={user}
        bands={[band]}
        onSelectBand={() => {}}
        onSignOut={() => {}}
        onCreateBand={onCreateBand}
      />,
    );
    fireEvent.click(screen.getByText(/create new band/i));
    fireEvent.change(screen.getByLabelText("Band Name"), { target: { value: "New Band" } });
    fireEvent.click(screen.getByRole("button", { name: /save band/i }));
    const saveButton = screen.getByRole("button", { name: /save band/i }) as HTMLButtonElement;
    expect(saveButton.disabled).toBe(true);
    resolveCreate();
  });

  it("form stays open when onCreateBand rejects (error silently swallowed)", async () => {
    const onCreateBand = vi.fn().mockRejectedValue(new Error("Network error"));
    render(
      <BandSelectPage
        user={user}
        bands={[band]}
        onSelectBand={() => {}}
        onSignOut={() => {}}
        onCreateBand={onCreateBand}
      />,
    );
    fireEvent.click(screen.getByText(/create new band/i));
    fireEvent.change(screen.getByLabelText("Band Name"), { target: { value: "New Band" } });
    fireEvent.click(screen.getByRole("button", { name: /save band/i }));
    await vi.waitFor(() => expect(onCreateBand).toHaveBeenCalled());
    expect(screen.getByLabelText("Band Name")).toBeTruthy();
  });
});
```

- [x] **Step 2: Run tests to confirm they all fail**

```bash
cd frontend && bun run test -- src/redesign/pages/__tests__/BandSelectPage.creation.test.tsx
```

Expected: All 8 tests FAIL. "ghost card" and "create new band" are not found because those elements don't exist yet.

---

### Task 2: Implement ghost card in BandSelectPage

**Files:**
- Modify: `frontend/src/redesign/pages/BandSelectPage.tsx`

- [x] **Step 1: Add the ghost card + inline form block after the bands list**

In `BandSelectPage.tsx`, the bands list is rendered in:
```tsx
<div className="space-y-4">
  {bands.map((band) => (
    // existing band cards...
  ))}
</div>
```

Add this immediately after the closing `</div>` of the `space-y-4` container, still inside `<main>`:

```tsx
{/* Ghost card / inline creation form — only when bands exist */}
{bands.length > 0 && (
  <div className="mt-4">
    {!isCreatingBand ? (
      <button
        onClick={() => setIsCreatingBand(true)}
        className="flex w-full items-center gap-5 border p-6 text-left transition-all hover:border-purple-500/30"
        style={{
          borderRadius: "6px",
          borderStyle: "dashed",
          borderColor: "rgba(124, 58, 237, 0.3)",
          background: "transparent",
        }}
      >
        <div
          className="flex h-14 w-14 shrink-0 items-center justify-center text-2xl font-bold"
          style={{ borderRadius: "3px", background: "rgba(124, 58, 237, 0.1)", color: "#a78bfa" }}
        >
          +
        </div>
        <span className="text-sm font-medium" style={{ color: "#a78bfa" }}>
          Create new band…
        </span>
      </button>
    ) : (
      <div
        className="border p-6"
        style={{
          borderRadius: "6px",
          background: "rgba(255, 255, 255, 0.03)",
          borderColor: "rgba(124, 58, 237, 0.2)",
        }}
      >
        <label
          className="block text-xs font-medium uppercase tracking-[0.18em]"
          style={{ color: "#a78bfa" }}
        >
          Band Name
          <input
            aria-label="Band Name"
            value={bandName}
            onChange={(event) => setBandName(event.target.value)}
            onKeyDown={(event) => { if (event.key === "Enter") void saveBand(); }}
            autoFocus
            className="mt-2 w-full border px-3 py-3 text-sm"
            style={{
              borderRadius: "3px",
              background: "rgba(10, 14, 39, 0.7)",
              borderColor: "rgba(192, 192, 192, 0.12)",
              color: "#e2e2f0",
            }}
          />
        </label>
        <div className="mt-4 flex gap-3">
          <button
            onClick={() => { setBandName(""); setIsCreatingBand(false); }}
            className="px-4 py-2 text-sm transition-colors hover:text-white"
            style={{ color: "#7a7a90" }}
          >
            Cancel
          </button>
          <button
            onClick={() => void saveBand()}
            disabled={!bandName.trim() || isSavingBand}
            className="px-5 py-2.5 text-sm font-semibold text-white transition-all hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-50"
            style={{ borderRadius: "3px", background: "linear-gradient(135deg, #14b8a6, #0f766e)" }}
          >
            Save Band
          </button>
        </div>
      </div>
    )}
  </div>
)}
```

- [x] **Step 2: Also add Enter-key support to the empty-state form input**

In the existing empty-state section (inside `bands.length === 0`), find the input:
```tsx
<input
  aria-label="Band Name"
  value={bandName}
  onChange={(event) => setBandName(event.target.value)}
  className="mt-2 w-full border px-3 py-3 text-sm"
```

Add `onKeyDown` handler:
```tsx
<input
  aria-label="Band Name"
  value={bandName}
  onChange={(event) => setBandName(event.target.value)}
  onKeyDown={(event) => { if (event.key === "Enter") void saveBand(); }}
  className="mt-2 w-full border px-3 py-3 text-sm"
```

- [x] **Step 3: Run tests to confirm they all pass**

```bash
cd frontend && bun run test -- src/redesign/pages/__tests__/BandSelectPage.creation.test.tsx
```

Expected: All 8 tests PASS.

- [x] **Step 4: Run the full test suite to check for regressions**

```bash
cd frontend && bun run test
```

Expected: All tests PASS.

- [x] **Step 5: Commit**

```bash
git add frontend/src/redesign/pages/BandSelectPage.tsx \
        frontend/src/redesign/pages/__tests__/BandSelectPage.creation.test.tsx
git commit -m "feat(ui): add ghost card for band creation when bands exist [plan: docs/plans/2026-03-15-band-project-creation-ux-fix.md, Task 2, cli: claude-code, model: claude-sonnet-4-6]"
```

Commit: https://github.com/gulasz101/DeChord/commit/a3e293d

---

## Chunk 2: ProjectHomePage — modal for project creation

---

### Task 3: Write failing tests for ProjectHomePage modal

**Files:**
- Create: `frontend/src/redesign/pages/__tests__/ProjectHomePage.creation.test.tsx`

- [x] **Step 1: Create the test file**

```tsx
// frontend/src/redesign/pages/__tests__/ProjectHomePage.creation.test.tsx
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ProjectHomePage } from "../ProjectHomePage";
import type { Band, Project, User } from "../../lib/types";

const user: User = {
  id: "1",
  name: "Alice",
  email: "alice@example.com",
  instrument: "Bass",
  avatar: "A",
};

const project: Project = {
  id: "9",
  name: "Album Prep",
  description: "First album",
  songs: [],
  recentActivity: [],
  unreadCount: 0,
};

const band: Band = {
  id: "3",
  name: "Shredders",
  members: [],
  projects: [project],
  avatarColor: "#7c3aed",
};

describe("ProjectHomePage — project creation modal", () => {
  it("modal is not visible by default", () => {
    render(
      <ProjectHomePage
        user={user}
        band={band}
        project={project}
        onSelectProject={() => {}}
        onOpenSongs={() => {}}
        onBack={() => {}}
      />,
    );
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("clicking New renders the modal", () => {
    render(
      <ProjectHomePage
        user={user}
        band={band}
        project={project}
        onSelectProject={() => {}}
        onOpenSongs={() => {}}
        onBack={() => {}}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /create new project/i }));
    expect(screen.getByRole("dialog")).toBeTruthy();
    expect(screen.getByLabelText("Project Name")).toBeTruthy();
  });

  it("modal closes on Cancel button click", () => {
    render(
      <ProjectHomePage
        user={user}
        band={band}
        project={project}
        onSelectProject={() => {}}
        onOpenSongs={() => {}}
        onBack={() => {}}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /create new project/i }));
    fireEvent.click(screen.getByRole("button", { name: /cancel/i }));
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("modal closes on Escape key", () => {
    render(
      <ProjectHomePage
        user={user}
        band={band}
        project={project}
        onSelectProject={() => {}}
        onOpenSongs={() => {}}
        onBack={() => {}}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /create new project/i }));
    fireEvent.keyDown(document, { key: "Escape" });
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("modal closes on backdrop click", () => {
    render(
      <ProjectHomePage
        user={user}
        band={band}
        project={project}
        onSelectProject={() => {}}
        onOpenSongs={() => {}}
        onBack={() => {}}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /create new project/i }));
    // Click the dialog element itself (the backdrop), not the card inside it
    fireEvent.click(screen.getByRole("dialog"));
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("submitting calls onCreateProject with name and description", async () => {
    const onCreateProject = vi.fn().mockResolvedValue(undefined);
    render(
      <ProjectHomePage
        user={user}
        band={band}
        project={project}
        onSelectProject={() => {}}
        onCreateProject={onCreateProject}
        onOpenSongs={() => {}}
        onBack={() => {}}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /create new project/i }));
    fireEvent.change(screen.getByLabelText("Project Name"), { target: { value: "Live Set" } });
    fireEvent.change(screen.getByLabelText("Project Description"), { target: { value: "Summer tour" } });
    fireEvent.click(screen.getByRole("button", { name: /save project/i }));
    await vi.waitFor(() =>
      expect(onCreateProject).toHaveBeenCalledWith({ name: "Live Set", description: "Summer tour" }),
    );
  });

  it("Save Project button is disabled when name is empty", () => {
    render(
      <ProjectHomePage
        user={user}
        band={band}
        project={project}
        onSelectProject={() => {}}
        onOpenSongs={() => {}}
        onBack={() => {}}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /create new project/i }));
    const saveButton = screen.getByRole("button", { name: /save project/i }) as HTMLButtonElement;
    expect(saveButton.disabled).toBe(true);
  });

  it("Save Project button is disabled while a save is in flight", () => {
    let resolveCreate!: () => void;
    const onCreateProject = vi.fn().mockReturnValue(
      new Promise<void>((r) => { resolveCreate = r; }),
    );
    render(
      <ProjectHomePage
        user={user}
        band={band}
        project={project}
        onSelectProject={() => {}}
        onCreateProject={onCreateProject}
        onOpenSongs={() => {}}
        onBack={() => {}}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /create new project/i }));
    fireEvent.change(screen.getByLabelText("Project Name"), { target: { value: "Live Set" } });
    fireEvent.click(screen.getByRole("button", { name: /save project/i }));
    const saveButton = screen.getByRole("button", { name: /save project/i }) as HTMLButtonElement;
    expect(saveButton.disabled).toBe(true);
    resolveCreate();
  });

  it("modal stays open when onCreateProject rejects (error silently swallowed)", async () => {
    const onCreateProject = vi.fn().mockRejectedValue(new Error("Network error"));
    render(
      <ProjectHomePage
        user={user}
        band={band}
        project={project}
        onSelectProject={() => {}}
        onCreateProject={onCreateProject}
        onOpenSongs={() => {}}
        onBack={() => {}}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /create new project/i }));
    fireEvent.change(screen.getByLabelText("Project Name"), { target: { value: "Live Set" } });
    fireEvent.click(screen.getByRole("button", { name: /save project/i }));
    await vi.waitFor(() => expect(onCreateProject).toHaveBeenCalled());
    expect(screen.getByRole("dialog")).toBeTruthy();
  });
});
```

- [x] **Step 2: Run tests to confirm they all fail**

```bash
cd frontend && bun run test -- src/redesign/pages/__tests__/ProjectHomePage.creation.test.tsx
```

Expected: All 9 tests FAIL. The "New" button has no `aria-label`, no `role="dialog"` exists, Escape key has no listener.

---

### Task 4: Implement the project creation modal in ProjectHomePage

**Files:**
- Modify: `frontend/src/redesign/pages/ProjectHomePage.tsx`

- [x] **Step 1: Add `useEffect` import**

`ProjectHomePage.tsx` currently imports only `useState`. Change the import:

```tsx
// Before:
import { useState } from "react";

// After:
import { useEffect, useState } from "react";
```

- [x] **Step 2: Add a dismiss helper and the Escape key listener inside the component**

After the existing state declarations and `saveProject` function, add:

```tsx
const dismissCreating = () => {
  setProjectName("");
  setProjectDescription("");
  setIsCreatingProject(false);
};

useEffect(() => {
  if (!isCreatingProject) return;
  const handleKeyDown = (event: KeyboardEvent) => {
    if (event.key === "Escape") dismissCreating();
  };
  document.addEventListener("keydown", handleKeyDown);
  return () => document.removeEventListener("keydown", handleKeyDown);
}, [isCreatingProject]);
```

Note: `dismissCreating` is defined before this `useEffect`. ESLint exhaustive-deps will flag it — wrap `dismissCreating` in `useCallback` only if the linter requires it; otherwise inline is fine.

- [x] **Step 3: Add `aria-label` to the "New" button**

Find the existing sidebar "New" button:
```tsx
<button
  onClick={() => setIsCreatingProject(true)}
  className="text-[10px] font-semibold uppercase tracking-[0.18em] transition-colors hover:text-white"
  style={{ color: "#a78bfa" }}
>
  New
</button>
```

Add `aria-label`:
```tsx
<button
  onClick={() => setIsCreatingProject(true)}
  aria-label="Create new project"
  className="text-[10px] font-semibold uppercase tracking-[0.18em] transition-colors hover:text-white"
  style={{ color: "#a78bfa" }}
>
  New
</button>
```

- [x] **Step 4: Add the modal overlay**

At the very end of the component's returned JSX (just before the final closing `</div>`), add the modal. The modal renders outside the layout flow, over everything:

```tsx
{/* Project creation modal */}
{isCreatingProject && (
  <div
    role="dialog"
    aria-modal="true"
    aria-label="New Project"
    className="fixed inset-0 z-50 flex items-center justify-center"
    style={{ background: "rgba(10, 14, 39, 0.8)" }}
    onClick={dismissCreating}
  >
    <div
      className="w-full max-w-md border p-8"
      style={{
        borderRadius: "6px",
        background: "#111638",
        borderColor: "rgba(124, 58, 237, 0.25)",
        backdropFilter: "blur(12px)",
      }}
      onClick={(event) => event.stopPropagation()}
    >
      <h2
        className="mb-6 text-2xl"
        style={{ fontFamily: "Playfair Display, serif", color: "#e2e2f0" }}
      >
        New Project
      </h2>

      <label
        className="block text-xs font-medium uppercase tracking-[0.18em]"
        style={{ color: "#a78bfa" }}
      >
        Project Name
        <input
          aria-label="Project Name"
          value={projectName}
          onChange={(event) => setProjectName(event.target.value)}
          autoFocus
          className="mt-2 w-full border px-3 py-3 text-sm"
          style={{
            borderRadius: "3px",
            background: "rgba(10, 14, 39, 0.7)",
            borderColor: "rgba(192, 192, 192, 0.12)",
            color: "#e2e2f0",
          }}
        />
      </label>

      <label
        className="mt-4 block text-xs font-medium uppercase tracking-[0.18em]"
        style={{ color: "#7a7a90" }}
      >
        Description
        <textarea
          aria-label="Project Description"
          value={projectDescription}
          onChange={(event) => setProjectDescription(event.target.value)}
          className="mt-2 min-h-24 w-full border px-3 py-3 text-sm"
          style={{
            borderRadius: "3px",
            background: "rgba(10, 14, 39, 0.7)",
            borderColor: "rgba(192, 192, 192, 0.12)",
            color: "#e2e2f0",
          }}
        />
      </label>

      <div className="mt-6 flex gap-3">
        <button
          onClick={dismissCreating}
          className="px-4 py-2 text-sm transition-colors hover:text-white"
          style={{ color: "#7a7a90" }}
        >
          Cancel
        </button>
        <button
          onClick={() => void saveProject()}
          disabled={!projectName.trim() || isSavingProject}
          className="px-5 py-2.5 text-sm font-semibold text-white transition-all hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-50"
          style={{ borderRadius: "3px", background: "linear-gradient(135deg, #14b8a6, #0f766e)" }}
        >
          Save Project
        </button>
      </div>
    </div>
  </div>
)}
```

- [x] **Step 5: Run the new tests to confirm they all pass**

```bash
cd frontend && bun run test -- src/redesign/pages/__tests__/ProjectHomePage.creation.test.tsx
```

Expected: All 9 tests PASS.

- [x] **Step 6: Run the full test suite to check for regressions**

```bash
cd frontend && bun run test
```

Expected: All tests PASS (including existing `ProjectHomePage.collaboration.test.tsx`).

- [x] **Step 7: Commit**

```bash
git add frontend/src/redesign/pages/ProjectHomePage.tsx \
        frontend/src/redesign/pages/__tests__/ProjectHomePage.creation.test.tsx
git commit -m "feat(ui): add project creation modal — fixes broken New button [plan: docs/plans/2026-03-15-band-project-creation-ux-fix.md, Task 4, cli: claude-code, model: claude-sonnet-4-6]"
```

Commit: https://github.com/gulasz101/DeChord/commit/99bd62e

---

## Smoke Test Checklist

After both tasks are committed, manually verify in the browser:

- [ ] Visit the app. Create a band. Confirm the ghost card appears below it.
- [ ] Click the ghost card. Enter a name. Press Enter. Confirm the band is created and the ghost card returns.
- [ ] Enter a band. Click "New" in the project sidebar with a project already selected. Confirm the modal appears.
- [ ] Press Escape. Confirm the modal closes.
- [ ] Click outside the modal card (on the dark backdrop). Confirm the modal closes.
- [ ] Fill in name + description, click Save Project. Confirm the new project appears in the sidebar.
