# Timeline Comment Lane — Design Spec

**Date:** 2026-03-14
**Status:** Approved
**Feature:** Restore and enhance clickable timeline comment lane in the Player

---

## Overview

Restore the MVP functionality of adding comments by clicking on the playback bar, extended with a two-bar transport layout, hover previews, and toast playback during song progression. All comments (chord-based and time-based) must appear as dots on the comment lane.

---

## 1. Layout & Components

### Two-bar Transport Structure

`TransportBar` is split into two visually distinct, vertically stacked bars inside the existing timeline area:

**Top bar — Comment Lane (`CommentLane`)**
- Height: 12px
- Background: `rgba(30, 30, 58, 0.7)` with 1px border `rgba(124, 58, 237, 0.15)`
- Border-radius: 6px
- Cursor: `crosshair`
- Subtle `click to add` hint text on the right (faded purple)
- Purple dot markers at computed positions

**Bottom bar — Seek / Playback (unchanged)**
- Existing `<input type="range">` seek slider
- No changes to seek behavior

### Dot Markers

Each dot represents one `SongNote` with a resolved `timestampSec`:

| State | Style |
|---|---|
| Own comment | Solid `#a78bfa`, white border `1.5px` |
| Other user's comment | Outline-only: transparent fill, `#a78bfa` border `1.5px` |

### Hover Preview Tooltip

Hovering any dot shows a small tooltip anchored above the dot:

```
┌─────────────────────────┐
│ Sarah K.                │  ← authorName, purple, semibold
│ "Watch the bass line"   │  ← note text
│ @ 1:23 · shows for 4.2s│  ← timestamp + toastDurationSec
└─────────────────────────┘
```

- Background: `rgba(17, 22, 56, 0.97)`
- Border: `1px solid rgba(167, 139, 250, 0.4)`
- Box-shadow: `0 4px 16px rgba(124, 58, 237, 0.3)`
- Z-index above all transport elements

### `TimelineCommentModal` Component (new file)

Three modes: `create` | `edit` | `reply`

**Header:** timestamp badge `@ 1:23` in purple

**Create mode fields:**
- Textarea: comment text
- Duration input: pre-filled with computed default (see §2), editable, labeled "Show for X seconds"
- Buttons: Save, Cancel

**Edit mode fields:**
- Same as create, pre-filled with existing note data
- Additional: Delete button (destructive, with confirmation)

**Reply mode:**
- Shows parent comment preview block at top (matching SongDetailPage threading style)
- Textarea for reply text
- No duration field (replies don't trigger toasts)
- Buttons: Reply, Cancel

Modal is centered, dark glass style matching designs.opus46:
- Background: `rgba(17, 22, 56, 0.98)`
- Border: `1px solid rgba(124, 58, 237, 0.6)`
- Border-radius: 8px
- Box-shadow: `0 8px 32px rgba(124, 58, 237, 0.4)`
- Playback continues while modal is open (no auto-pause)

---

## 2. Data Flow & Auth

### Ownership Detection

- `App.tsx` resolves `identityUserId: number | null` via fingerprint → `/api/identity/resolve`
- Pass `currentUserId: number | null` as a new prop to `PlayerPage`
- `SongNote` type gains `userId: number | null` field (see §3)
- Ownership check: `note.userId === currentUserId`

### Click Routing in `PlayerPage`

| Event | Handler |
|---|---|
| Click empty comment lane | `onCommentLaneClick(timestampSec)` → open modal `mode: "create"` |
| Click own dot | `onMarkerClick(noteId, timestampSec)` → look up note → open modal `mode: "edit"` |
| Click other user's dot | `onMarkerClick(noteId, timestampSec)` → look up note → open modal `mode: "reply"` |

### Default Toast Duration

When opening the create modal at `timestampSec`:
1. Find the chord in `chords[]` whose time range contains `timestampSec`
2. Default duration = `chordEnd - timestampSec`
3. Fallback: 4.0 seconds if no chord boundary found

### Toast Playback Engine

In `PlayerPage`, a `useEffect` watches `currentTime` from `useAudioPlayer`:

- Maintains `firedNoteIds: Set<number>` (reset on seek backward past any fired note)
- Each render tick: for each `SongNote` where `timestampSec !== null` and `toastDurationSec !== null`:
  - If `currentTime >= note.timestampSec` and note not in fired set → push to active toasts, schedule removal after `toastDurationSec * 1000` ms (note: `toastDurationSec` is stored in **seconds**; multiply by 1000 for `setTimeout`)
  - Add note ID to fired set
- `ToastCueLayer` receives the active toasts array (existing component, no changes needed)

---

## 3. API & Backend Changes

### `SongNote` Type Extension

Add `userId: number | null` to:
- `frontend/src/redesign/lib/types.ts` — `SongNote` interface
- `frontend/src/lib/types.ts` — `SongNote` interface (snake_case mirror)
- `backend/app/models.py` — `Note` dataclass: add `user_id: int | None = None`
- `backend/app/main.py` — include `user_id` in note serialization

### Chord-Type Notes Must Store `timestampSec`

Currently `type: "chord"` notes store `chordIndex` but leave `timestampSec: null`.

**Fix:** when creating a chord-type note in `PlayerPage`, compute `timestampSec = chords[chordIndex].startTime` and pass it alongside `chordIndex` to `onCreateNote`. Backend already accepts both fields.

This ensures all notes appear as dots on the comment lane.

### New `TransportBar` Props

```typescript
onCommentLaneClick: (timestampSec: number) => void;
onMarkerClick: (noteId: number, timestampSec: number) => void;
// noteMarkers extended:
noteMarkers: Array<{ id: number; timestampSec: number; userId: number | null }>;
```

Click-position → timestamp formula (inside the `CommentLane` click handler):
```ts
const rect = laneRef.current.getBoundingClientRect();
const timestampSec = ((e.clientX - rect.left) / rect.width) * duration;
```

### New `PlayerPage` Props (from `App.tsx`)

```typescript
currentUserId: number | null;        // new
onDeleteNote: (noteId: number) => Promise<void>;  // new (backend DELETE /api/notes/{id} exists)
// existing: onEditNote, onCreateNote, onCreateReply
```

### `App.tsx` Wiring

- Pass `identityUserId` as `currentUserId` to `PlayerPage`
- Implement `onDeleteNote` calling `deleteNote(noteId)` from `api.ts` then refreshing song data

---

## 4. Components Map

| File | Change |
|---|---|
| `frontend/src/redesign/components/TransportBar.tsx` | Add `CommentLane` sub-area, hover tooltip, two new callbacks, extend `noteMarkers` type |
| `frontend/src/redesign/components/TimelineCommentModal.tsx` | **New** — create/edit/reply modal |
| `frontend/src/redesign/pages/PlayerPage.tsx` | Modal state, toast engine, default duration calc, new props, chord-note timestamp fix |
| `frontend/src/App.tsx` | Pass `currentUserId`, implement `onDeleteNote`, pass to PlayerPage |
| `frontend/src/redesign/lib/types.ts` | Add `userId` to `SongNote` |
| `frontend/src/lib/types.ts` | Add `user_id` to `SongNote` |
| `backend/app/models.py` | Add `user_id` to `Note` |
| `backend/app/main.py` | Serialize `user_id` in note responses |

---

## 5. Testing

### Unit Tests

**`TimelineCommentModal`**
- Renders correctly in all three modes (create / edit / reply)
- Pre-fills duration field with computed default
- Calls `onSave` with correct payload
- Delete button triggers confirmation then `onDelete`
- Reply mode hides duration field, shows parent preview

**`TransportBar`**
- Click on empty lane area fires `onCommentLaneClick` with timestamp proportional to click position
- Click on a dot fires `onMarkerClick` with correct noteId and timestampSec
- Hovering dot shows preview tooltip with author, text, timestamp, duration
- Own dot rendered solid; other user's dot rendered outline

**Toast engine logic (unit)**
- Given notes and a sequence of `currentTime` values, correct toasts fire once at the right time
- Fired set resets on seek backward
- Toast removed after `toastDurationSec`

### Integration Tests (`PlayerPage.test.tsx`)

- Click empty comment lane → modal opens in create mode with correct timestamp
- Click own dot → modal in edit mode, pre-filled, delete button present
- Click other user's dot → modal in reply mode, parent preview shown
- Chord-click note creation passes both `chordIndex` and `timestampSec`, dot appears on lane
- Toast fires during playback at correct timestamp and clears after duration

---

## 6. Design Language Reference

Follow `designs.opus46` canonical design:
- Dark theme: `#0a0e27` base, `rgba(17,22,56,*)` panels
- Primary accent: `#7c3aed` / `#a78bfa` purple
- Secondary accent: `#14b8a6` teal (volume slider only)
- Text: `#e2e2f0` primary, `#8a8a9a` secondary, `#7a7a90` muted
- Blur: `backdrop-filter: blur(16px)` on overlapping panels
- Borders: `rgba(192, 192, 192, 0.06)` subtle, `rgba(124, 58, 237, 0.4-0.6)` accent
- Border-radius: `4px` containers, `6-8px` modals/tooltips
