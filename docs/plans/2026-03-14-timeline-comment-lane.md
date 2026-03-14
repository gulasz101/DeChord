# Timeline Comment Lane — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore the clickable comment lane on the transport bar so users can add timestamped comments by clicking, see them as dots with hover previews, and hear them fire as toasts during playback.

**Architecture:** Two-bar transport layout — a `CommentLane` above the existing seek slider. A new `TimelineCommentModal` (create/edit/reply) is managed by `PlayerPage`, which also runs the toast playback engine. `TransportBar` emits click events up; `PlayerPage` orchestrates modal state and toast firing.

**Tech Stack:** React 19, TypeScript, Tailwind v4, Vitest + React Testing Library, FastAPI (Python 3.13), existing `api.ts` helpers.

> **Commit message rule (AGENTS.md):** Every commit must reference: plan path (`docs/plans/2026-03-14-timeline-comment-lane.md`), task name, tool name, and model. The templates below are content-only — expand them at commit time. Example: `feat(types): add userId to SongNote [plan: 2026-03-14-timeline-comment-lane, Task 1, claude-code, claude-sonnet-4-6]`

**Spec:** `docs/superpowers/specs/2026-03-14-timeline-comment-lane-design.md`

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `frontend/src/redesign/lib/types.ts` | Modify | Add `userId: number \| null` to `SongNote`; export `NoteMarker` interface |
| `frontend/src/lib/types.ts` | Modify | Add `user_id: number \| null` to `SongNote` (snake_case legacy) |
| `frontend/src/App.tsx` | Modify | Map `author_user_id` in `mapNote`; pass `currentUserId` + `onCreateReply` to `PlayerPage` |
| `frontend/src/redesign/components/TransportBar.tsx` | Modify | Add `CommentLane` sub-area with click + hover; extend `noteMarkers` type; two new callbacks |
| `frontend/src/redesign/components/TimelineCommentModal.tsx` | Create | Standalone modal — create/edit/reply modes |
| `frontend/src/redesign/pages/PlayerPage.tsx` | Modify | Modal state, toast engine, chord-note `timestampSec` fix, updated `noteMarkers`, new props |
| `frontend/src/redesign/components/__tests__/TransportBar.comment.test.tsx` | Create | TransportBar comment lane unit tests |
| `frontend/src/redesign/components/__tests__/TimelineCommentModal.test.tsx` | Create | Modal unit tests |
| `frontend/src/redesign/pages/__tests__/PlayerPage.test.tsx` | Modify | Add integration tests for lane click → modal, chord note fix, toast engine |

---

## Chunk 1: Foundation — userId in Types + mapNote

### Task 1: Add `userId` to `SongNote` in both type files

**Files:**
- Modify: `frontend/src/redesign/lib/types.ts`
- Modify: `frontend/src/lib/types.ts`

The backend `_load_song_notes` already returns `author_user_id`. We just need to surface it in the frontend types and mapper.

- [ ] **Step 1: Add `userId` to redesign SongNote and export `NoteMarker`**

In `frontend/src/redesign/lib/types.ts`, add `userId` to `SongNote` and append the `NoteMarker` interface (used by `TransportBar` and its tests):

```typescript
export interface SongNote {
  id: number;
  type: "time" | "chord" | "general";
  timestampSec: number | null;
  chordIndex: number | null;
  text: string;
  toastDurationSec: number | null;
  authorName: string | null;
  authorAvatar: string | null;
  userId: number | null;   // ← add this line
  resolved: boolean;
  parentId: number | null;
  createdAt: string;
  updatedAt: string;
}

// New — add after SongNote
export interface NoteMarker {
  id: number;
  timestampSec: number;
  userId: number | null;
  authorName?: string | null;
  text?: string;
  toastDurationSec?: number | null;
}
```

- [ ] **Step 2: Add `user_id` to legacy SongNote**

In `frontend/src/lib/types.ts`, find the `SongNote` interface and add `user_id: number | null` after `author_avatar`:

```typescript
// In frontend/src/lib/types.ts — SongNote interface
export interface SongNote {
  id: number;
  type: "time" | "chord" | "general";
  timestamp_sec: number | null;
  chord_index: number | null;
  text: string;
  toast_duration_sec: number | null;
  author_name: string | null;
  author_avatar: string | null;
  user_id: number | null;   // ← add this line
  resolved: boolean;
  parent_id: number | null;
  created_at: string;
  updated_at: string;
}
```

- [ ] **Step 3: Update `mapNote` in `App.tsx`**

Find `function mapNote` (~line 162). Add `author_user_id` to the input type and `userId` to the return:

```typescript
function mapNote(note: {
  id: number;
  type: "time" | "chord" | "general";
  timestamp_sec: number | null;
  chord_index: number | null;
  text: string;
  toast_duration_sec: number | null;
  resolved: boolean;
  author_name: string | null;
  author_avatar: string | null;
  author_user_id: number | null;   // ← add
  parent_id: number | null;
  created_at: string;
  updated_at: string;
}): SongNote {
  return {
    id: note.id,
    type: note.type,
    timestampSec: note.timestamp_sec,
    chordIndex: note.chord_index,
    text: note.text,
    toastDurationSec: note.toast_duration_sec,
    authorName: note.author_name,
    authorAvatar: note.author_avatar,
    userId: note.author_user_id,   // ← add
    resolved: note.resolved,
    parentId: note.parent_id,
    createdAt: note.created_at,
    updatedAt: note.updated_at,
  };
}
```

- [ ] **Step 4: Verify TypeScript compiles**

```bash
cd frontend && bun run tsc --noEmit
```

Expected: no errors (TypeScript may warn about usages that don't pass `author_user_id` — these are internal API response objects, so add `| undefined` to the input type if needed, defaulting to `note.author_user_id ?? null`).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/redesign/lib/types.ts frontend/src/lib/types.ts frontend/src/App.tsx
git commit -m "feat(types): add userId to SongNote and wire through mapNote"
```

---

## Chunk 2: TransportBar Comment Lane + TimelineCommentModal

### Task 2: Extend TransportBar with CommentLane

**Files:**
- Modify: `frontend/src/redesign/components/TransportBar.tsx`
- Create: `frontend/src/redesign/components/__tests__/TransportBar.comment.test.tsx`

The note lane currently renders purple dots but has no click handler. We split it into a proper `CommentLane` with click detection, hover tooltips, and ownership-based dot styling. `NoteMarker` is imported from `redesign/lib/types.ts` (added in Task 1) — no inline redeclaration.

- [ ] **Step 1: Write failing tests**

Create `frontend/src/redesign/components/__tests__/TransportBar.comment.test.tsx`:

```typescript
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { TransportBar } from "../TransportBar";
import type { NoteMarker } from "../../lib/types";

const baseProps = {
  currentTime: 30,
  duration: 120,
  playing: false,
  volume: 0.8,
  speedPercent: 100,
  loopActive: false,
  noteMarkers: [],
  currentUserId: null,
  onTogglePlay: vi.fn(),
  onSeek: vi.fn(),
  onSeekRelative: vi.fn(),
  onVolumeChange: vi.fn(),
  onSpeedChange: vi.fn(),
  onClearLoop: vi.fn(),
  onCommentLaneClick: vi.fn(),
  onMarkerClick: vi.fn(),
};

describe("TransportBar CommentLane", () => {
  it("fires onCommentLaneClick with correct timestamp when clicking empty lane", () => {
    const onCommentLaneClick = vi.fn();
    render(<TransportBar {...baseProps} onCommentLaneClick={onCommentLaneClick} />);
    const lane = screen.getByTestId("comment-lane");
    // Simulate click at 50% of lane width → 0.5 * 120 = 60s
    Object.defineProperty(lane, "getBoundingClientRect", {
      value: () => ({ left: 0, width: 200, top: 0, right: 200, bottom: 12, height: 12 }),
    });
    fireEvent.click(lane, { clientX: 100 }); // 50% → 60s
    expect(onCommentLaneClick).toHaveBeenCalledWith(expect.closeTo(60, 0));
  });

  it("fires onMarkerClick when clicking a dot, not onCommentLaneClick", () => {
    const onMarkerClick = vi.fn();
    const onCommentLaneClick = vi.fn();
    const markers = [{ id: 42, timestampSec: 30, userId: 7 }];
    render(
      <TransportBar
        {...baseProps}
        noteMarkers={markers}
        onMarkerClick={onMarkerClick}
        onCommentLaneClick={onCommentLaneClick}
      />,
    );
    fireEvent.click(screen.getByTestId("comment-marker-42"));
    expect(onMarkerClick).toHaveBeenCalledWith(42, 30);
    expect(onCommentLaneClick).not.toHaveBeenCalled();
  });

  it("shows hover tooltip with author and text on dot hover", async () => {
    const markers: NoteMarker[] = [
      { id: 1, timestampSec: 30, userId: 5, authorName: "Sarah K.", text: "Watch this", toastDurationSec: 4.2 },
    ];
    render(<TransportBar {...baseProps} noteMarkers={markers} />);
    const dot = screen.getByTestId("comment-marker-1");
    fireEvent.mouseEnter(dot);
    expect(await screen.findByText("Sarah K.")).toBeInTheDocument();
    expect(screen.getByText("Watch this")).toBeInTheDocument();
  });

  it("renders own dot with solid style and other dot with outline style", () => {
    const markers: NoteMarker[] = [
      { id: 1, timestampSec: 10, userId: 99 },  // own
      { id: 2, timestampSec: 40, userId: 5 },   // other
    ];
    render(<TransportBar {...baseProps} currentUserId={99} noteMarkers={markers} />);
    expect(screen.getByTestId("comment-marker-1")).toHaveAttribute("data-own", "true");
    expect(screen.getByTestId("comment-marker-2")).toHaveAttribute("data-own", "false");
  });
});
```

- [ ] **Step 2: Run tests — expect FAIL**

```bash
cd frontend && bun vitest run src/redesign/components/__tests__/TransportBar.comment.test.tsx
```

Expected: FAIL — `comment-lane` testId not found, new props not typed.

- [ ] **Step 3: Update TransportBar props and implement CommentLane**

At the top of `TransportBar.tsx`, add the import:
```typescript
import type { NoteMarker } from "../../lib/types";
```

Replace the existing `interface TransportBarProps` and the note lane section in `TransportBar.tsx`:

```typescript
// NoteMarker is now imported from types.ts — do NOT redeclare it here

interface TransportBarProps {
  currentTime: number;
  duration: number;
  playing: boolean;
  volume: number;
  speedPercent: number;
  loopActive: boolean;
  loopLabel?: string;
  noteMarkers: NoteMarker[];
  currentUserId: number | null;
  onTogglePlay: () => void;
  onSeek: (time: number) => void;
  onSeekRelative: (delta: number) => void;
  onVolumeChange: (v: number) => void;
  onSpeedChange: (s: number) => void;
  onClearLoop: () => void;
  onCommentLaneClick: (timestampSec: number) => void;
  onMarkerClick: (noteId: number, timestampSec: number) => void;
}
```

Replace the note lane `<div>` block (the `mb-1 h-3` div) with:

```tsx
{/* Comment lane */}
<div
  data-testid="comment-lane"
  className="relative mb-1 w-full cursor-crosshair overflow-visible rounded"
  style={{ height: "12px", background: "rgba(30, 30, 58, 0.7)", border: "1px solid rgba(124, 58, 237, 0.15)" }}
  onClick={(e) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const ts = ((e.clientX - rect.left) / rect.width) * (duration || 1);
    onCommentLaneClick(Math.max(0, Math.min(ts, duration)));
  }}
>
  {noteMarkers.map((m) => {
    const left = duration > 0 ? (m.timestampSec / duration) * 100 : 0;
    const isOwn = m.userId !== null && m.userId === currentUserId;
    return (
      <CommentDot
        key={m.id}
        marker={m}
        left={left}
        isOwn={isOwn}
        onMarkerClick={onMarkerClick}
      />
    );
  })}
  <span
    className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 text-[8px] tracking-wide"
    style={{ color: "rgba(167, 139, 250, 0.3)" }}
  >
    click to add
  </span>
</div>
```

Add a `CommentDot` sub-component in the same file (above `TransportBar`). The file already has `formatTime` defined — do NOT add a second one, just reuse it:

```tsx
interface CommentDotProps {
  marker: NoteMarker;
  left: number;
  isOwn: boolean;
  onMarkerClick: (noteId: number, timestampSec: number) => void;
}

function CommentDot({ marker, left, isOwn, onMarkerClick }: CommentDotProps) {
  const [hovered, setHovered] = React.useState(false);

  return (
    <div
      data-testid={`comment-marker-${marker.id}`}
      data-own={String(isOwn)}
      className="absolute top-1/2 -translate-x-1/2 -translate-y-1/2 cursor-pointer"
      style={{ left: `${left}%` }}
      onClick={(e) => {
        e.stopPropagation();
        onMarkerClick(marker.id, marker.timestampSec);
      }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      {/* Dot */}
      <div
        className="h-2.5 w-2.5 rounded-full transition-transform hover:scale-125"
        style={
          isOwn
            ? { background: "#a78bfa", border: "1.5px solid #e2e2f0" }
            : { background: "transparent", border: "1.5px solid #a78bfa" }
        }
      />
      {/* Hover preview */}
      {hovered && (marker.authorName || marker.text) && (
        <div
          className="pointer-events-none absolute bottom-4 left-1/2 z-50 -translate-x-1/2 rounded-md px-3 py-2 shadow-xl"
          style={{
            background: "rgba(17, 22, 56, 0.97)",
            border: "1px solid rgba(167, 139, 250, 0.4)",
            boxShadow: "0 4px 16px rgba(124, 58, 237, 0.3)",
            whiteSpace: "nowrap",
            minWidth: "120px",
          }}
        >
          {marker.authorName && (
            <div className="mb-0.5 text-[10px] font-semibold" style={{ color: "#a78bfa" }}>
              {marker.authorName}
            </div>
          )}
          {marker.text && (
            <div className="text-[10px]" style={{ color: "#e2e2f0" }}>
              {marker.text}
            </div>
          )}
          <div className="mt-1 text-[9px]" style={{ color: "#7a7a90" }}>
            @ {formatTime(marker.timestampSec)}
            {marker.toastDurationSec != null && ` · shows for ${marker.toastDurationSec}s`}
          </div>
        </div>
      )}
    </div>
  );
}
```

Also add `import React from "react";` at the top if not present.

- [ ] **Step 4: Run tests — expect PASS**

```bash
cd frontend && bun vitest run src/redesign/components/__tests__/TransportBar.comment.test.tsx
```

Expected: all 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/redesign/components/TransportBar.tsx \
        frontend/src/redesign/components/__tests__/TransportBar.comment.test.tsx
git commit -m "feat(transport): add CommentLane with click, hover tooltip, and marker callbacks"
```

---

### Task 3: Create `TimelineCommentModal`

**Files:**
- Create: `frontend/src/redesign/components/TimelineCommentModal.tsx`
- Create: `frontend/src/redesign/components/__tests__/TimelineCommentModal.test.tsx`

- [ ] **Step 1: Write failing tests**

Create `frontend/src/redesign/components/__tests__/TimelineCommentModal.test.tsx`:

```typescript
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { TimelineCommentModal } from "../TimelineCommentModal";
import type { SongNote } from "../../lib/types";

const baseNote: SongNote = {
  id: 1,
  type: "time",
  timestampSec: 90,
  chordIndex: null,
  text: "Great riff here",
  toastDurationSec: 4.0,
  authorName: "Alice",
  authorAvatar: null,
  userId: 7,
  resolved: false,
  parentId: null,
  createdAt: "",
  updatedAt: "",
};

describe("TimelineCommentModal — create mode", () => {
  it("renders with timestamp badge and empty textarea", () => {
    render(
      <TimelineCommentModal
        mode="create"
        timestampSec={90}
        defaultDurationSec={4.5}
        onSave={vi.fn()}
        onClose={vi.fn()}
      />,
    );
    expect(screen.getByText(/@ 1:30/)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/add a comment/i)).toHaveValue("");
    expect(screen.getByLabelText(/show for/i)).toHaveValue("4.5");
  });

  it("calls onSave with text and duration when form is submitted", () => {
    const onSave = vi.fn();
    render(
      <TimelineCommentModal
        mode="create"
        timestampSec={90}
        defaultDurationSec={4.5}
        onSave={onSave}
        onClose={vi.fn()}
      />,
    );
    fireEvent.change(screen.getByPlaceholderText(/add a comment/i), { target: { value: "Nice chord" } });
    fireEvent.change(screen.getByLabelText(/show for/i), { target: { value: "6" } });
    fireEvent.click(screen.getByRole("button", { name: /save/i }));
    expect(onSave).toHaveBeenCalledWith({ text: "Nice chord", toastDurationSec: 6 });
  });

  it("does not call onSave with empty text", () => {
    const onSave = vi.fn();
    render(
      <TimelineCommentModal mode="create" timestampSec={0} defaultDurationSec={4} onSave={onSave} onClose={vi.fn()} />,
    );
    fireEvent.click(screen.getByRole("button", { name: /save/i }));
    expect(onSave).not.toHaveBeenCalled();
  });
});

describe("TimelineCommentModal — edit mode", () => {
  it("pre-fills text and duration from existing note", () => {
    render(
      <TimelineCommentModal
        mode="edit"
        timestampSec={90}
        defaultDurationSec={4}
        note={baseNote}
        onSave={vi.fn()}
        onDelete={vi.fn()}
        onClose={vi.fn()}
      />,
    );
    expect(screen.getByDisplayValue("Great riff here")).toBeInTheDocument();
    expect(screen.getByLabelText(/show for/i)).toHaveValue("4");
  });

  it("shows a Delete button in edit mode", () => {
    render(
      <TimelineCommentModal
        mode="edit"
        timestampSec={90}
        defaultDurationSec={4}
        note={baseNote}
        onSave={vi.fn()}
        onDelete={vi.fn()}
        onClose={vi.fn()}
      />,
    );
    expect(screen.getByRole("button", { name: /delete/i })).toBeInTheDocument();
  });

  it("calls onDelete when Delete is confirmed", () => {
    const onDelete = vi.fn();
    render(
      <TimelineCommentModal
        mode="edit"
        timestampSec={90}
        defaultDurationSec={4}
        note={baseNote}
        onSave={vi.fn()}
        onDelete={onDelete}
        onClose={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /delete/i }));
    // Confirmation step
    fireEvent.click(screen.getByRole("button", { name: /confirm/i }));
    expect(onDelete).toHaveBeenCalledWith(1);
  });
});

describe("TimelineCommentModal — reply mode", () => {
  it("shows parent comment preview, hides duration field, and calls onReply on submit", () => {
    const onReply = vi.fn();
    render(
      <TimelineCommentModal
        mode="reply"
        timestampSec={90}
        defaultDurationSec={4}
        note={baseNote}
        onSave={vi.fn()}
        onReply={onReply}
        onClose={vi.fn()}
      />,
    );
    expect(screen.getByText(/Great riff here/)).toBeInTheDocument(); // parent preview
    expect(screen.queryByLabelText(/show for/i)).not.toBeInTheDocument(); // no duration
    expect(screen.getByRole("button", { name: /reply/i })).toBeInTheDocument();
    // Submit
    fireEvent.change(screen.getByPlaceholderText(/add a comment/i), { target: { value: "Good point" } });
    fireEvent.click(screen.getByRole("button", { name: /reply/i }));
    expect(onReply).toHaveBeenCalledWith("Good point");
  });
});
```

- [ ] **Step 2: Run tests — expect FAIL**

```bash
cd frontend && bun vitest run src/redesign/components/__tests__/TimelineCommentModal.test.tsx
```

Expected: FAIL — module not found.

- [ ] **Step 3: Implement `TimelineCommentModal`**

Create `frontend/src/redesign/components/TimelineCommentModal.tsx`:

```tsx
import { useState } from "react";
import type { SongNote } from "../lib/types";

function formatTime(s: number): string {
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  return `${m}:${sec.toString().padStart(2, "0")}`;
}

interface SavePayload {
  text: string;
  toastDurationSec: number;
}

interface TimelineCommentModalProps {
  mode: "create" | "edit" | "reply";
  timestampSec: number;
  defaultDurationSec: number;
  note?: SongNote;        // required for edit/reply modes
  onSave: (payload: SavePayload) => void;   // create and edit only
  onReply?: (text: string) => void;         // reply mode only
  onDelete?: (noteId: number) => void;
  onClose: () => void;
}

export function TimelineCommentModal({
  mode,
  timestampSec,
  defaultDurationSec,
  note,
  onSave,
  onReply,
  onDelete,
  onClose,
}: TimelineCommentModalProps) {
  const [text, setText] = useState(mode === "edit" && note ? note.text : "");
  const [durationSec, setDurationSec] = useState(
    mode === "edit" && note?.toastDurationSec != null
      ? note.toastDurationSec
      : defaultDurationSec,
  );
  const [confirmDelete, setConfirmDelete] = useState(false);

  const handleSave = () => {
    if (!text.trim()) return;
    if (mode === "reply") {
      onReply?.(text.trim());
    } else {
      onSave({ text: text.trim(), toastDurationSec: durationSec });
    }
  };

  const modeLabel =
    mode === "create" ? "Add Comment" : mode === "edit" ? "Edit Comment" : "Reply";

  return (
    /* Backdrop */
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      style={{ background: "rgba(0,0,0,0.5)" }}
      onClick={onClose}
    >
      {/* Modal panel */}
      <div
        className="w-full max-w-md rounded-lg px-6 py-5 shadow-2xl"
        style={{
          background: "rgba(17, 22, 56, 0.98)",
          border: "1px solid rgba(124, 58, 237, 0.6)",
          boxShadow: "0 8px 32px rgba(124, 58, 237, 0.4)",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="mb-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold" style={{ color: "#a78bfa" }}>
              💬 {modeLabel}
            </span>
            <span
              className="rounded px-2 py-0.5 font-mono text-xs"
              style={{ background: "rgba(124,58,237,0.2)", color: "#a78bfa" }}
            >
              @ {formatTime(timestampSec)}
            </span>
          </div>
          <button
            onClick={onClose}
            className="text-sm"
            style={{ color: "#8a8a9a" }}
            aria-label="close"
          >
            ✕
          </button>
        </div>

        {/* Reply: parent preview */}
        {mode === "reply" && note && (
          <div
            className="mb-4 rounded p-3 text-xs"
            style={{
              background: "rgba(30,30,58,0.7)",
              border: "1px solid rgba(192,192,192,0.1)",
              color: "#8a8a9a",
            }}
          >
            <span className="font-semibold" style={{ color: "#a78bfa" }}>
              {note.authorName ?? "Unknown"}:{" "}
            </span>
            {note.text}
          </div>
        )}

        {/* Textarea */}
        <textarea
          className="mb-3 w-full resize-none rounded p-3 text-sm outline-none"
          style={{
            background: "rgba(30,30,58,0.8)",
            border: "1px solid rgba(192,192,192,0.12)",
            color: "#e2e2f0",
            minHeight: "80px",
          }}
          placeholder="Add a comment..."
          value={text}
          onChange={(e) => setText(e.target.value)}
          autoFocus
        />

        {/* Duration (create + edit only) */}
        {mode !== "reply" && (
          <div className="mb-4 flex items-center gap-2">
            <label
              htmlFor="toast-duration"
              className="text-xs"
              style={{ color: "#8a8a9a" }}
            >
              Show for
            </label>
            <input
              id="toast-duration"
              type="number"
              min={1}
              max={60}
              step={0.5}
              value={durationSec}
              onChange={(e) => setDurationSec(parseFloat(e.target.value) || defaultDurationSec)}
              className="w-20 rounded px-2 py-1 text-center text-xs outline-none"
              style={{
                background: "rgba(30,30,58,0.8)",
                border: "1px solid rgba(192,192,192,0.12)",
                color: "#e2e2f0",
              }}
              aria-label="show for (seconds)"
            />
            <span className="text-xs" style={{ color: "#8a8a9a" }}>
              seconds
            </span>
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-2">
          {!confirmDelete ? (
            <>
              <button
                onClick={handleSave}
                className="flex-1 rounded py-2 text-sm font-semibold text-white transition-all hover:brightness-110"
                style={{ background: "linear-gradient(135deg, #7c3aed, #5b21b6)" }}
              >
                {mode === "reply" ? "Reply" : "Save"}
              </button>
              {mode === "edit" && onDelete && note && (
                <button
                  onClick={() => setConfirmDelete(true)}
                  className="rounded px-3 py-2 text-sm font-semibold transition-colors hover:brightness-110"
                  style={{ background: "rgba(239,68,68,0.15)", color: "#f87171" }}
                >
                  Delete
                </button>
              )}
              <button
                onClick={onClose}
                className="rounded px-3 py-2 text-sm transition-colors"
                style={{ background: "rgba(30,30,58,0.8)", color: "#8a8a9a" }}
              >
                Cancel
              </button>
            </>
          ) : (
            <>
              <span className="flex-1 text-xs" style={{ color: "#f87171" }}>
                Delete this comment?
              </span>
              <button
                onClick={() => { if (note && onDelete) onDelete(note.id); }}
                className="rounded px-3 py-2 text-sm font-semibold"
                style={{ background: "rgba(239,68,68,0.3)", color: "#f87171" }}
              >
                Confirm
              </button>
              <button
                onClick={() => setConfirmDelete(false)}
                className="rounded px-3 py-2 text-sm"
                style={{ background: "rgba(30,30,58,0.8)", color: "#8a8a9a" }}
              >
                Keep
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
cd frontend && bun vitest run src/redesign/components/__tests__/TimelineCommentModal.test.tsx
```

Expected: all 7 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/redesign/components/TimelineCommentModal.tsx \
        frontend/src/redesign/components/__tests__/TimelineCommentModal.test.tsx
git commit -m "feat(player): add TimelineCommentModal with create/edit/reply modes"
```

---

## Chunk 3: PlayerPage Wiring

### Task 4: Fix chord-note `timestampSec` + update `noteMarkers` in PlayerPage

**Files:**
- Modify: `frontend/src/redesign/pages/PlayerPage.tsx`
- Modify: `frontend/src/redesign/pages/__tests__/PlayerPage.test.tsx`

Currently `timeNoteMarkers` only picks up `type === "time"` notes. Chord notes must also store `timestampSec` (chord start time) and appear on the lane.

- [ ] **Step 1: Add failing test to PlayerPage.test.tsx**

Find the existing test file and add at the end of the describe block:

```typescript
it("chord-type note creation passes timestampSec = chord start time", async () => {
  const onCreateNote = vi.fn();
  const song = makeSong({
    chords: [
      { start: 0, end: 5, label: "Am" },
      { start: 5, end: 10, label: "G" },
    ],
    notes: [],
  });
  render(<PlayerPage {...baseProps} song={song} onCreateNote={onCreateNote} />);

  // Advance playback to chord index 1 (t=6, inside G chord)
  act(() => { transportStore.update({ currentTime: 6 }); });

  // Click "Note on Current Chord" button
  fireEvent.click(screen.getByText(/note on current chord/i));
  const input = screen.getByPlaceholderText(/add a note/i);
  fireEvent.change(input, { target: { value: "G chord note" } });
  // Submit
  fireEvent.click(screen.getByText(/note on current chord/i));

  await waitFor(() => {
    expect(onCreateNote).toHaveBeenCalledWith(
      expect.objectContaining({
        type: "chord",
        chordIndex: 1,
        timestampSec: 5, // start of chord index 1
      }),
    );
  });
});
```

- [ ] **Step 2: Run to verify FAIL**

```bash
cd frontend && bun vitest run src/redesign/pages/__tests__/PlayerPage.test.tsx --reporter=verbose 2>&1 | tail -20
```

Expected: FAIL — `timestampSec` not included in `onCreateNote` call.

- [ ] **Step 3: Update chord note creation in PlayerPage**

Find the chord-note creation handler in `PlayerPage.tsx` (~line 336-340):

```typescript
// BEFORE:
await onCreateNote({ type: "chord", text: trimmedText, chordIndex: currentIndex });

// AFTER:
await onCreateNote({
  type: "chord",
  text: trimmedText,
  chordIndex: currentIndex,
  timestampSec: currentChord?.start ?? null,
});
```

- [ ] **Step 4: Update `timeNoteMarkers` → `allNoteMarkers`**

Find the `timeNoteMarkers` useMemo (~line 95) and replace:

```typescript
// BEFORE:
const timeNoteMarkers = useMemo(
  () => song.notes.filter((n) => n.type === "time" && n.timestampSec !== null)
        .map((n) => ({ id: n.id, timestampSec: n.timestampSec! })),
  [song.notes],
);

// AFTER:
const allNoteMarkers = useMemo(
  () =>
    song.notes
      .filter((n) => n.timestampSec !== null && !n.resolved)
      .map((n) => ({
        id: n.id,
        timestampSec: n.timestampSec!,
        userId: n.userId ?? null,
        authorName: n.authorName,
        text: n.text,
        toastDurationSec: n.toastDurationSec,
      })),
  [song.notes],
);
```

Update the reference to `timeNoteMarkers` in the `<TransportBar>` JSX to `allNoteMarkers`.

- [ ] **Step 5: Run test — expect PASS**

```bash
cd frontend && bun vitest run src/redesign/pages/__tests__/PlayerPage.test.tsx
```

- [ ] **Step 6: Commit**

```bash
git add frontend/src/redesign/pages/PlayerPage.tsx \
        frontend/src/redesign/pages/__tests__/PlayerPage.test.tsx
git commit -m "fix(player): chord notes now store timestampSec and appear on comment lane"
```

---

### Task 5: Add modal state + lane click wiring to PlayerPage

**Files:**
- Modify: `frontend/src/redesign/pages/PlayerPage.tsx`
- Modify: `frontend/src/redesign/pages/__tests__/PlayerPage.test.tsx`

- [ ] **Step 1: Add shared test helpers at module level (top of PlayerPage.test.tsx, outside all describe blocks)**

These are shared across Tasks 4, 5, and 6. Define them **once** near the top of the file, after the existing mock definitions:

```typescript
// Shared test helpers — module level
function makeSong(overrides: Partial<Song> = {}): Song {
  return {
    id: "1",
    title: "Test Song",
    artist: "",
    key: "Am",
    tempo: 120,
    duration: 120,
    status: "ready",
    chords: [{ start: 0, end: 120, label: "Am" }],
    stems: [],
    notes: [],
    updatedAt: "",
    ...overrides,
  };
}
const noteDefaults = {
  chordIndex: null,
  authorName: "Alice",
  authorAvatar: null,
  userId: null,
  resolved: false,
  parentId: null,
  createdAt: "",
  updatedAt: "",
};
```

- [ ] **Step 2: Add failing tests for modal wiring**

Add to `PlayerPage.test.tsx`:

```typescript
it("clicking empty comment lane opens create modal with correct timestamp", async () => {
  render(<PlayerPage {...baseProps} />);
  const lane = screen.getByTestId("comment-lane");
  Object.defineProperty(lane, "getBoundingClientRect", {
    value: () => ({ left: 0, width: 400, top: 0, right: 400, bottom: 12, height: 12 }),
  });
  fireEvent.click(lane, { clientX: 200 }); // 50% → 60s (duration=120)
  expect(await screen.findByText(/add comment/i)).toBeInTheDocument();
  expect(screen.getByText(/@ 1:00/)).toBeInTheDocument();
});

it("clicking own marker opens edit modal", async () => {
  const song = makeSong({
    notes: [
      { id: 5, type: "time", timestampSec: 30, text: "My note", userId: 1, toastDurationSec: 4, ...noteDefaults },
    ],
  });
  render(<PlayerPage {...baseProps} song={song} currentUserId={1} />);
  fireEvent.click(screen.getByTestId("comment-marker-5"));
  expect(await screen.findByText(/edit comment/i)).toBeInTheDocument();
  expect(screen.getByDisplayValue("My note")).toBeInTheDocument();
});

it("clicking another user's marker opens reply modal", async () => {
  const song = makeSong({
    notes: [
      { id: 6, type: "time", timestampSec: 30, text: "Their note", userId: 99, toastDurationSec: 4, ...noteDefaults },
    ],
  });
  render(<PlayerPage {...baseProps} song={song} currentUserId={1} />);
  fireEvent.click(screen.getByTestId("comment-marker-6"));
  expect(await screen.findByText(/reply/i)).toBeInTheDocument();
  expect(screen.getByText("Their note")).toBeInTheDocument(); // parent preview
});
```

- [ ] **Step 3: Run to verify FAIL**

```bash
cd frontend && bun vitest run src/redesign/pages/__tests__/PlayerPage.test.tsx 2>&1 | tail -20
```

- [ ] **Step 4: Add modal state + new props to PlayerPage**

At the top of `PlayerPage`, add these imports:
```typescript
import { TimelineCommentModal } from "../components/TimelineCommentModal";
```

Add new props to `PlayerPageProps`:
```typescript
interface PlayerPageProps {
  // ... existing ...
  currentUserId?: number | null;
  onCreateReply?: (parentId: number, text: string) => Promise<void> | void;
}
```

Add modal state inside the component:
```typescript
type ModalState =
  | { open: false }
  | { open: true; mode: "create"; timestampSec: number; defaultDurationSec: number }
  | { open: true; mode: "edit"; note: SongNote; timestampSec: number; defaultDurationSec: number }
  | { open: true; mode: "reply"; note: SongNote; timestampSec: number; defaultDurationSec: number };

const [modal, setModal] = useState<ModalState>({ open: false });
```

Add a helper to compute default duration from chord data:
```typescript
const computeDefaultDuration = useCallback(
  (timestampSec: number): number => {
    const chord = song.chords.find((c) => timestampSec >= c.start && timestampSec < c.end);
    if (chord) return Math.max(1, chord.end - timestampSec);
    return 4.0;
  },
  [song.chords],
);
```

Add lane click handlers:
```typescript
const handleCommentLaneClick = useCallback(
  (timestampSec: number) => {
    setModal({
      open: true,
      mode: "create",
      timestampSec,
      defaultDurationSec: computeDefaultDuration(timestampSec),
    });
  },
  [computeDefaultDuration],
);

const handleMarkerClick = useCallback(
  (noteId: number, timestampSec: number) => {
    const note = song.notes.find((n) => n.id === noteId);
    if (!note) return;
    const isOwn = note.userId !== null && note.userId === (currentUserId ?? null);
    setModal({
      open: true,
      mode: isOwn ? "edit" : "reply",
      note,
      timestampSec,
      defaultDurationSec: note.toastDurationSec ?? computeDefaultDuration(timestampSec),
    });
  },
  [song.notes, currentUserId, computeDefaultDuration],
);
```

Add modal save/close handlers (note: `onSave` handles create+edit; `onReply` handles reply — matching the split prop design of `TimelineCommentModal`):
```typescript
const handleModalSave = useCallback(
  async (payload: { text: string; toastDurationSec: number }) => {
    if (!modal.open || modal.mode === "reply") return;
    if (modal.mode === "create" && onCreateNote) {
      await onCreateNote({ type: "time", text: payload.text, timestampSec: modal.timestampSec, toastDurationSec: payload.toastDurationSec });
    } else if (modal.mode === "edit" && onEditNote) {
      await onEditNote(modal.note.id, { text: payload.text, toastDurationSec: payload.toastDurationSec });
    }
    setModal({ open: false });
  },
  [modal, onCreateNote, onEditNote],
);

const handleModalReply = useCallback(
  async (text: string) => {
    if (!modal.open || modal.mode !== "reply") return;
    if (onCreateReply) await onCreateReply(modal.note.id, text);
    setModal({ open: false });
  },
  [modal, onCreateReply],
);

const handleModalDelete = useCallback(
  async (noteId: number) => {
    if (onDeleteNote) await onDeleteNote(noteId);
    setModal({ open: false });
  },
  [onDeleteNote],
);
```

Pass the new callbacks and props to `<TransportBar>`:
```tsx
<TransportBar
  // ... existing props ...
  noteMarkers={allNoteMarkers}
  currentUserId={currentUserId ?? null}
  onCommentLaneClick={handleCommentLaneClick}
  onMarkerClick={handleMarkerClick}
/>
```

Render the modal at the end of the component return, before the closing tag:
```tsx
{modal.open && (
  <TimelineCommentModal
    mode={modal.mode}
    timestampSec={modal.timestampSec}
    defaultDurationSec={modal.defaultDurationSec}
    note={modal.mode !== "create" ? modal.note : undefined}
    onSave={handleModalSave}
    onReply={handleModalReply}
    onDelete={modal.mode === "edit" ? handleModalDelete : undefined}
    onClose={() => setModal({ open: false })}
  />
)}
```

Also add a test for `computeDefaultDuration` behaviour (exercised via the modal's pre-filled duration field):

```typescript
it("default duration in create modal = time remaining in clicked chord", async () => {
  const song = makeSong({
    chords: [
      { start: 0, end: 10, label: "Am" },
      { start: 10, end: 18, label: "G" },
    ],
    duration: 18,
    notes: [],
  });
  render(<PlayerPage {...baseProps} song={song} />);
  const lane = screen.getByTestId("comment-lane");
  Object.defineProperty(lane, "getBoundingClientRect", {
    value: () => ({ left: 0, width: 180, top: 0, right: 180, bottom: 12, height: 12 }),
  });
  // Click at pixel 120 → ts = (120/180)*18 = 12s — inside G chord (10–18), remaining = 6s
  fireEvent.click(lane, { clientX: 120 });
  await screen.findByText(/add comment/i);
  expect(screen.getByLabelText(/show for/i)).toHaveValue("6");
});

it("default duration falls back to 4s when click is past all chords", async () => {
  const song = makeSong({ chords: [{ start: 0, end: 5, label: "Am" }], duration: 120, notes: [] });
  render(<PlayerPage {...baseProps} song={song} />);
  const lane = screen.getByTestId("comment-lane");
  Object.defineProperty(lane, "getBoundingClientRect", {
    value: () => ({ left: 0, width: 120, top: 0, right: 120, bottom: 12, height: 12 }),
  });
  // Click at pixel 60 → ts = 60s — past the only chord (ends at 5s)
  fireEvent.click(lane, { clientX: 60 });
  await screen.findByText(/add comment/i);
  expect(screen.getByLabelText(/show for/i)).toHaveValue("4");
});
```

- [ ] **Step 5: Run tests — expect PASS**

```bash
cd frontend && bun vitest run src/redesign/pages/__tests__/PlayerPage.test.tsx
```

- [ ] **Step 6: Commit**

```bash
git add frontend/src/redesign/pages/PlayerPage.tsx \
        frontend/src/redesign/pages/__tests__/PlayerPage.test.tsx
git commit -m "feat(player): wire comment lane click to modal — create/edit/reply"
```

---

### Task 6: Toast playback engine in PlayerPage

**Files:**
- Modify: `frontend/src/redesign/pages/PlayerPage.tsx`
- Modify: `frontend/src/redesign/pages/__tests__/PlayerPage.test.tsx`

- [ ] **Step 1: Add failing tests**

Add to `PlayerPage.test.tsx`:

```typescript
it("fires a toast when playback time crosses a note's timestampSec", async () => {
  const song = makeSong({
    notes: [
      { id: 10, type: "time", timestampSec: 5, text: "Toast me!", toastDurationSec: 3, userId: null, ...noteDefaults },
    ],
  });
  render(<PlayerPage {...baseProps} song={song} />);

  // No toast initially
  expect(screen.queryByText("Toast me!")).not.toBeInTheDocument();

  // Advance time past the note
  act(() => { transportStore.update({ currentTime: 5.1 }); });

  expect(await screen.findByText("Toast me!")).toBeInTheDocument();
});

it("does not fire the same toast twice without seeking backward", async () => {
  const song = makeSong({
    notes: [
      { id: 11, type: "time", timestampSec: 5, text: "Once only", toastDurationSec: 10, userId: null, ...noteDefaults },
    ],
  });
  render(<PlayerPage {...baseProps} song={song} />);
  act(() => { transportStore.update({ currentTime: 5.1 }); });
  await screen.findByText("Once only");
  act(() => { transportStore.update({ currentTime: 5.5 }); });
  // Still just one toast (not duplicated)
  expect(screen.getAllByText("Once only")).toHaveLength(1);
});

it("resets fired toasts on seek backward", async () => {
  const song = makeSong({
    notes: [
      { id: 12, type: "time", timestampSec: 5, text: "Replay", toastDurationSec: 10, userId: null, ...noteDefaults },
    ],
  });
  render(<PlayerPage {...baseProps} song={song} />);
  act(() => { transportStore.update({ currentTime: 5.1 }); });
  await screen.findByText("Replay");
  // Seek back to 0
  act(() => { transportStore.update({ currentTime: 0 }); });
  // Advance past note again
  act(() => { transportStore.update({ currentTime: 5.2 }); });
  expect(await screen.findByText("Replay")).toBeInTheDocument();
});
```

- [ ] **Step 2: Run to verify FAIL**

```bash
cd frontend && bun vitest run src/redesign/pages/__tests__/PlayerPage.test.tsx 2>&1 | tail -20
```

- [ ] **Step 3: Implement toast engine in PlayerPage**

Add these imports at the top:
```typescript
import { ToastCueLayer } from "../../components/ToastCueLayer";
```

Add state for active toasts and fired set:
```typescript
const [activeToasts, setActiveToasts] = useState<Array<{ id: number; text: string }>>([]);
const firedNoteIds = useRef<Set<number>>(new Set());
const prevTimestamp = useRef<number>(0);
```

Add the toast engine `useEffect` (place after the loop/playback prefs effect):
```typescript
useEffect(() => {
  const currentTime = player.currentTime;

  // Reset fired set if user seeked backward past any fired note
  if (currentTime < prevTimestamp.current) {
    for (const note of song.notes) {
      if (note.timestampSec !== null && note.timestampSec > currentTime) {
        firedNoteIds.current.delete(note.id);
      }
    }
  }
  prevTimestamp.current = currentTime;

  // Fire notes whose timestamp has been crossed
  for (const note of song.notes) {
    if (
      note.timestampSec === null ||
      note.toastDurationSec === null ||
      note.resolved ||
      firedNoteIds.current.has(note.id)
    ) {
      continue;
    }
    if (currentTime >= note.timestampSec) {
      firedNoteIds.current.add(note.id);
      const toastId = note.id;
      setActiveToasts((prev) => [...prev, { id: toastId, text: note.text }]);
      setTimeout(() => {
        setActiveToasts((prev) => prev.filter((t) => t.id !== toastId));
      }, note.toastDurationSec * 1000);
    }
  }
}, [player.currentTime, song.notes]);
```

Render `ToastCueLayer` in the JSX (place it just before the closing `</div>` of the root element):
```tsx
<ToastCueLayer toasts={activeToasts} />
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
cd frontend && bun vitest run src/redesign/pages/__tests__/PlayerPage.test.tsx
```

- [ ] **Step 5: Verify TypeScript compiles**

```bash
cd frontend && bun run tsc --noEmit
```

Expected: no errors (validates `ToastCueLayer` import path `../../components/ToastCueLayer` resolves correctly from `redesign/pages/`).

- [ ] **Step 6: Commit**

```bash
git add frontend/src/redesign/pages/PlayerPage.tsx \
        frontend/src/redesign/pages/__tests__/PlayerPage.test.tsx
git commit -m "feat(player): add toast playback engine — fires notes as toasts at their timestamps"
```

---

### Task 7: Wire `currentUserId` + `onCreateReply` in App.tsx

**Files:**
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Add `currentUserId` to PlayerPage render**

Find the `<PlayerPage` render in App.tsx (~line 1024). Add two new props:

```tsx
<PlayerPage
  // ... all existing props ...
  currentUserId={identityUserId}
  onCreateReply={async (parentId: number, text: string) => {
    await createSongNote(parseInt(song.id), {
      type: "general",   // "general" is a valid enum value — backend accepts it for replies with parent_id
      text,
      parent_id: parentId,
    });
    await refreshSong();
  }}
/>
```

(Use the existing `createSongNote` import from `api.ts` and `refreshSong` pattern used elsewhere in App.tsx. The `type: "general"` enum value is confirmed valid in the backend `NoteCreate` schema — replies are identified by `parent_id`, not by type.)

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && bun run tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Smoke-test in browser**

```bash
make up
```

Open the app, navigate to a song in the player, verify:
- [ ] Comment lane is visible above seek bar
- [ ] Click empty lane → modal opens at correct timestamp
- [ ] Save a comment → dot appears on lane
- [ ] Hover dot → tooltip shows author + text
- [ ] Play song → toast fires at the comment's timestamp
- [ ] Click own dot → edit modal opens pre-filled
- [ ] Click other user's dot → reply modal opens

- [ ] **Step 4: Commit**

```bash
git add frontend/src/App.tsx
git commit -m "feat(app): pass currentUserId and onCreateReply to PlayerPage"
```

---

## Final Check

- [ ] Run full frontend test suite:
```bash
cd frontend && bun vitest run
```
Expected: all tests pass, no regressions.

- [ ] Run TypeScript check:
```bash
cd frontend && bun run tsc --noEmit
```
Expected: clean.
