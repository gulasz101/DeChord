# Notes and Rehearsal Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make rehearsal notes real by adding truthful backend note state, then wiring create/edit/delete/resolve flows into song detail and player with time-linked and chord-linked interactions.

**Architecture:** Keep note truth in `backend/app/main.py` and route ownership in `frontend/src/App.tsx`. `frontend/src/redesign/pages/SongDetailPage.tsx` and `frontend/src/redesign/pages/PlayerPage.tsx` should stay presentational shells over route-owned mutation callbacks and hydrated song state, while `frontend/src/lib/api.ts`, `frontend/src/lib/types.ts`, and `frontend/src/redesign/lib/types.ts` align on one honest note contract.

**Tech Stack:** FastAPI, Python 3.13+, pytest, React 19, TypeScript, Vite, Vitest, Testing Library, LibSQL.

---

## XML Tracking

<phase id="notes-rehearsal-plan-execution" status="planned">
  <task>[ ] Task 1: Lock the backend note-truth contract with failing API tests.</task>
  <task>[ ] Task 2: Align frontend note types and route hydration with the truthful contract.</task>
  <task>[ ] Task 3: Add song-detail note CRUD and resolved-state interactions.</task>
  <task>[ ] Task 4: Add player rehearsal note capture and mutation flows.</task>
  <task>[ ] Task 5: Run the notes-and-rehearsal quality gate and record implementation status.</task>
</phase>

### Task 1: Lock the backend note-truth contract with failing API tests

**Files:**
- Modify: `backend/tests/test_api.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_api.py`

**Step 1: Write the failing test**

```python
def test_song_notes_support_resolve_and_truthful_payloads(tmp_path, monkeypatch):
    client = _build_client(tmp_path, monkeypatch)

    create = client.post("/api/analyze", files={"file": ("demo.mp3", b"audio", "audio/mpeg")})
    song_id = create.json()["song_id"]

    created = client.post(
        f"/api/songs/{song_id}/notes",
        json={"type": "chord", "text": "Tighten the verse lock", "chord_index": 1},
    )
    note_id = created.json()["id"]

    resolved = client.patch(f"/api/notes/{note_id}/resolve", json={"resolved": True})
    assert resolved.status_code == 200
    assert resolved.json()["resolved"] is True

    song = client.get(f"/api/songs/{song_id}")
    payload = song.json()["notes"][0]
    assert payload["resolved"] is True
    assert payload["author_name"]
    assert payload["created_at"]
```

Add two smaller failing cases in the same task:

```python
def test_create_time_note_requires_timestamp_sec(...):
    ...
    assert response.status_code == 400

def test_create_chord_note_requires_chord_index(...):
    ...
    assert response.status_code == 400
```

**Step 2: Run test to verify it fails**

Run: `uv run --project backend pytest backend/tests/test_api.py -k "song_notes_support_resolve_and_truthful_payloads or create_time_note_requires_timestamp_sec or create_chord_note_requires_chord_index" -q`
Expected: FAIL because `/api/notes/{note_id}/resolve` does not exist yet and `GET /api/songs/{song_id}` still returns incomplete note payloads.

**Step 3: Write minimal implementation**

```python
class NoteResolveUpdate(BaseModel):
    resolved: bool


@app.patch("/api/notes/{note_id}/resolve")
async def resolve_note(note_id: int, payload: NoteResolveUpdate):
    await execute(
        "UPDATE notes SET resolved = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        [1 if payload.resolved else 0, note_id],
    )
    return {"id": note_id, "resolved": payload.resolved}
```

```python
notes = [
    {
        "id": row[0],
        "type": row[1],
        "timestamp_sec": row[2],
        "chord_index": row[3],
        "text": row[4],
        "toast_duration_sec": row[5],
        "resolved": bool(row[6]),
        "author_name": row[7],
        "author_avatar": row[8],
        "created_at": row[9],
        "updated_at": row[10],
    }
    for row in notes_rs.rows
]
```

Implementation details to keep:
- keep create, patch-text, delete, and resolve as separate note actions
- return truthful note payload fields from `GET /api/songs/{song_id}` instead of leaving the frontend to invent them
- make resolve/unresolve idempotent and 404 on missing notes
- keep this task backend-only; do not touch frontend files yet

**Step 4: Run test to verify it passes**

Run: `uv run --project backend pytest backend/tests/test_api.py -k "song_notes_support_resolve_and_truthful_payloads or create_time_note_requires_timestamp_sec or create_chord_note_requires_chord_index" -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add backend/tests/test_api.py backend/app/main.py
git commit -m "feat: add truthful rehearsal note api contract (docs/plans/2026-03-10-notes-rehearsal-implementation.md task: Lock the backend note-truth contract with failing API tests) | opencode | gpt-5.1-codex-max"
```

### Task 2: Align frontend note types and route hydration with the truthful contract

**Files:**
- Modify: `frontend/src/lib/types.ts`
- Modify: `frontend/src/redesign/lib/types.ts`
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/__tests__/App.integration.test.tsx`
- Test: `frontend/src/__tests__/App.integration.test.tsx`

**Step 1: Write the failing test**

```tsx
it("preserves resolved note truth and note metadata when song details hydrate", async () => {
  getSongMock.mockResolvedValueOnce({
    song: { id: 30, title: "Demo", original_filename: "demo.mp3", mime_type: "audio/mpeg", created_at: "2026-03-10T00:00:00Z" },
    analysis: { key: "C", tempo: 120, duration: 10, chords: [{ start: 0, end: 2, label: "C" }] },
    notes: [{
      id: 91,
      type: "time",
      timestamp_sec: 4.2,
      chord_index: null,
      text: "Drop the fill",
      toast_duration_sec: null,
      resolved: true,
      author_name: "Wojtek",
      author_avatar: "WG",
      created_at: "2026-03-10T10:00:00Z",
      updated_at: "2026-03-10T10:05:00Z",
    }],
    playback_prefs: { speed_percent: 100, volume: 1, loop_start_index: null, loop_end_index: null },
  });

  render(<App />);

  await screen.findByText("Demo Band");
  await userEvent.click(screen.getByRole("button", { name: /demo band/i }));
  await userEvent.click(screen.getByRole("button", { name: /demo project/i }));
  await userEvent.click(screen.getByRole("button", { name: /demo song/i }));

  expect(screen.getByText(/show resolved/i)).toBeInTheDocument();
  expect(screen.queryByText(/no open comments/i)).toBeInTheDocument();
  expect(screen.getByText("Wojtek")).toBeInTheDocument();
});
```

Also add a failing contract assertion for the new API helper:

```ts
await resolveSongNote(91, true);
expect(fetch).toHaveBeenCalledWith("/api/notes/91/resolve", expect.objectContaining({ method: "PATCH" }));
```

**Step 2: Run test to verify it fails**

Run: `npm --prefix frontend test -- --run src/__tests__/App.integration.test.tsx`
Expected: FAIL because `App.tsx` still hardcodes `resolved: false`, invents author/timestamp values, and there is no resolve-note API helper yet.

**Step 3: Write minimal implementation**

```ts
export interface SongNote {
  id: number;
  type: "time" | "chord";
  timestamp_sec: number | null;
  chord_index: number | null;
  text: string;
  toast_duration_sec: number | null;
  resolved: boolean;
  author_name: string | null;
  author_avatar: string | null;
  created_at: string;
  updated_at: string;
}
```

```ts
export async function resolveSongNote(noteId: number, resolved: boolean): Promise<{ id: number; resolved: boolean }> {
  const res = await fetch(`${BASE}/api/notes/${noteId}/resolve`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ resolved }),
  });
  if (!res.ok) throw new Error("Failed to resolve note");
  return res.json();
}
```

```ts
resolved: note.resolved,
authorName: note.author_name,
authorAvatar: note.author_avatar,
createdAt: note.created_at,
```

Implementation details to keep:
- align frontend types with the backend contract before adding new page UI
- keep route-owned hydration in `App.tsx`
- do not fall back to synthesized current-user note authors for fetched notes in this slice
- if backend author metadata is missing, treat that as a Slice 4 contract failure and fix the backend contract rather than masking it in the frontend
- do not add page-local mutation UI in this task

**Step 4: Run test to verify it passes**

Run: `npm --prefix frontend test -- --run src/__tests__/App.integration.test.tsx`
Expected: PASS.

**Step 5: Commit**

```bash
git add frontend/src/lib/types.ts frontend/src/redesign/lib/types.ts frontend/src/lib/api.ts frontend/src/App.tsx frontend/src/__tests__/App.integration.test.tsx
git commit -m "feat: hydrate truthful rehearsal note state in app routes (docs/plans/2026-03-10-notes-rehearsal-implementation.md task: Align frontend note types and route hydration with the truthful contract) | opencode | gpt-5.1-codex-max"
```

### Task 3: Add song-detail note CRUD and resolved-state interactions

**Files:**
- Modify: `frontend/src/redesign/pages/SongDetailPage.tsx`
- Create: `frontend/src/redesign/pages/__tests__/SongDetailPage.notes.test.tsx`
- Modify: `frontend/src/__tests__/App.integration.test.tsx`
- Modify: `frontend/src/App.tsx`
- Test: `frontend/src/redesign/pages/__tests__/SongDetailPage.notes.test.tsx`
- Test: `frontend/src/__tests__/App.integration.test.tsx`

**Step 1: Write the failing test**

```tsx
it("creates manual timestamp notes, chord notes, and note mutations from song detail", async () => {
  const song = {
    ...baseSong,
    chords: [
      { start: 0, end: 2, label: "C" },
      { start: 2, end: 4, label: "G" },
    ],
    notes: [
      {
        id: 11,
        type: "chord",
        chordIndex: 0,
        timestampSec: null,
        text: "Lock verse entry",
        authorName: "Wojtek",
        authorAvatar: "WG",
        resolved: false,
        createdAt: "2026-03-10T10:00:00Z",
      },
    ],
  };
  const onCreateNote = vi.fn();
  const onEditNote = vi.fn();
  const onResolveNote = vi.fn();
  const onDeleteNote = vi.fn();

  render(
    <SongDetailPage
      user={user}
      band={band}
      project={project}
      song={song}
      onOpenPlayer={() => {}}
      onBack={() => {}}
      onCreateNote={onCreateNote}
      onEditNote={onEditNote}
      onResolveNote={onResolveNote}
      onDeleteNote={onDeleteNote}
    />,
  );

  await userEvent.type(screen.getByLabelText(/note text/i), "Bass pickup is late");
  await userEvent.click(screen.getByLabelText(/time note/i));
  await userEvent.clear(screen.getByLabelText(/timestamp/i));
  await userEvent.type(screen.getByLabelText(/timestamp/i), "01:18");
  await userEvent.click(screen.getByRole("button", { name: /add time note/i }));
  expect(onCreateNote).toHaveBeenCalledWith(expect.objectContaining({ type: "time", text: "Bass pickup is late", timestampSec: 78 }));

  await userEvent.type(screen.getByLabelText(/note text/i), "Verse entrance is late");
  await userEvent.click(screen.getByRole("button", { name: /add chord note/i }));
  expect(onCreateNote).toHaveBeenCalledWith(expect.objectContaining({ type: "chord", chordIndex: 0 }));

  await userEvent.click(screen.getByRole("button", { name: /resolve/i }));
  expect(onResolveNote).toHaveBeenCalledWith(11, true);
});
```

Add a route integration failure in `frontend/src/__tests__/App.integration.test.tsx` that confirms a successful Song Detail time-note or chord-note mutation triggers a refresh for the active song-detail route.

**Step 2: Run test to verify it fails**

Run: `npm --prefix frontend test -- --run src/redesign/pages/__tests__/SongDetailPage.notes.test.tsx src/__tests__/App.integration.test.tsx`
Expected: FAIL because `SongDetailPage` does not yet expose real note mutation controls or callbacks.

**Step 3: Write minimal implementation**

```tsx
interface SongDetailPageProps {
  ...
  onCreateNote?: (payload: { type: "time" | "chord"; text: string; timestampSec?: number; chordIndex?: number }) => Promise<void> | void;
  onEditNote?: (noteId: number, payload: { text: string }) => Promise<void> | void;
  onResolveNote?: (noteId: number, resolved: boolean) => Promise<void> | void;
  onDeleteNote?: (noteId: number) => Promise<void> | void;
}
```

```tsx
<input aria-label="Timestamp" value={timestampDraft} onChange={handleTimestampDraftChange} />
<button onClick={() => void runAction(() => onResolveNote?.(note.id, !note.resolved), note.resolved ? "Note reopened." : "Note resolved.")}>Resolve</button>
```

Implementation details to keep:
- keep song detail focused on manageable review/edit flows, not live transport capture
- make Song Detail time-note creation explicit with a manual timestamp field; do not rely on player transport, waveform picking, or hidden defaults
- normalize Song Detail timestamp input from `mm:ss` or numeric seconds into `timestampSec`; if needed, ship numeric-seconds-only, but document and test the exact accepted format
- render open notes first and resolved notes in the collapsible section
- reuse existing inline success/error messaging patterns already present in the page
- route the actual API work through `App.tsx`, then refresh song detail after success

**Step 4: Run test to verify it passes**

Run: `npm --prefix frontend test -- --run src/redesign/pages/__tests__/SongDetailPage.notes.test.tsx src/__tests__/App.integration.test.tsx`
Expected: PASS.

**Step 5: Commit**

```bash
git add frontend/src/redesign/pages/SongDetailPage.tsx frontend/src/redesign/pages/__tests__/SongDetailPage.notes.test.tsx frontend/src/__tests__/App.integration.test.tsx frontend/src/App.tsx
git commit -m "feat: add song detail rehearsal note workflows (docs/plans/2026-03-10-notes-rehearsal-implementation.md task: Add song-detail note CRUD and resolved-state interactions) | opencode | gpt-5.1-codex-max"
```

### Task 4: Add player rehearsal note capture and mutation flows

**Files:**
- Modify: `frontend/src/redesign/pages/PlayerPage.tsx`
- Modify: `frontend/src/redesign/pages/__tests__/PlayerPage.test.tsx`
- Modify: `frontend/src/__tests__/App.integration.test.tsx`
- Modify: `frontend/src/App.tsx`
- Test: `frontend/src/redesign/pages/__tests__/PlayerPage.test.tsx`
- Test: `frontend/src/__tests__/App.integration.test.tsx`

**Step 1: Write the failing test**

```tsx
it("creates a time note from the current transport and a chord note from the current chord", async () => {
  vi.mocked(useAudioPlayer).mockReturnValue({
    currentTime: 18.5,
    duration: 120,
    playing: false,
    volume: 1,
    playbackRate: 1,
    togglePlay: vi.fn(),
    seek: vi.fn(),
    seekRelative: vi.fn(),
    setVolume: vi.fn(),
    setPlaybackRate: vi.fn(),
    setLoop: vi.fn(),
  });

  const song = {
    ...baseSong,
    chords: [
      { start: 0, end: 8, label: "C" },
      { start: 8, end: 16, label: "F" },
      { start: 16, end: 24, label: "G" },
    ],
    notes: [],
  };
  const onCreateNote = vi.fn();
  const onEditNote = vi.fn();
  const onResolveNote = vi.fn();
  const onDeleteNote = vi.fn();

  render(
    <PlayerPage
      user={user}
      band={band}
      project={project}
      song={song}
      onBack={() => {}}
      onCreateNote={onCreateNote}
      onResolveNote={onResolveNote}
      onEditNote={onEditNote}
      onDeleteNote={onDeleteNote}
    />,
  );

  await userEvent.click(screen.getByRole("button", { name: /comments/i }));
  await userEvent.type(screen.getByLabelText(/note text/i), "Bass pickup drifts");
  await userEvent.click(screen.getByRole("button", { name: /note at current time/i }));
  expect(onCreateNote).toHaveBeenCalledWith(expect.objectContaining({ type: "time", timestampSec: 18.5 }));

  await userEvent.click(screen.getByRole("button", { name: /note on current chord/i }));
  expect(onCreateNote).toHaveBeenCalledWith(expect.objectContaining({ type: "chord", chordIndex: 2 }));
});
```

Add a route integration failure that verifies player note mutations refresh the active player route and preserve resolved/open grouping.

**Step 2: Run test to verify it fails**

Run: `npm --prefix frontend test -- --run src/redesign/pages/__tests__/PlayerPage.test.tsx src/__tests__/App.integration.test.tsx`
Expected: FAIL because the player comments panel is still read-only.

**Step 3: Write minimal implementation**

```tsx
interface PlayerPageProps {
  user: User;
  band: Band;
  project: Project;
  song: Song;
  onBack: () => void;
  onCreateNote?: (payload: { type: "time" | "chord"; text: string; timestampSec?: number; chordIndex?: number }) => Promise<void> | void;
  onEditNote?: (noteId: number, payload: { text: string }) => Promise<void> | void;
  onResolveNote?: (noteId: number, resolved: boolean) => Promise<void> | void;
  onDeleteNote?: (noteId: number) => Promise<void> | void;
}
```

```tsx
<button onClick={() => void onCreateNote?.({ type: "time", text: draftText, timestampSec: player.currentTime })}>
  Note at Current Time
</button>
<button onClick={() => void onCreateNote?.({ type: "chord", text: draftText, chordIndex: currentIndex })}>
  Note on Current Chord
</button>
```

Implementation details to keep:
- make player note capture fast and compact
- use `player.currentTime` as the time-note source of truth
- use `currentIndex` as the chord-note source of truth
- keep all mutations route-owned in `App.tsx`, then refresh the active player route after success
- do not add collaboration affordances or multi-user presence here

Test setup note:
- if `frontend/src/redesign/pages/__tests__/PlayerPage.test.tsx` already contains a shared `vi.mock("../../hooks/useAudioPlayer")` block, extend that exact mock in place instead of inventing a new helper name

**Step 4: Run test to verify it passes**

Run: `npm --prefix frontend test -- --run src/redesign/pages/__tests__/PlayerPage.test.tsx src/__tests__/App.integration.test.tsx`
Expected: PASS.

**Step 5: Commit**

```bash
git add frontend/src/redesign/pages/PlayerPage.tsx frontend/src/redesign/pages/__tests__/PlayerPage.test.tsx frontend/src/__tests__/App.integration.test.tsx frontend/src/App.tsx
git commit -m "feat: add player rehearsal note capture flows (docs/plans/2026-03-10-notes-rehearsal-implementation.md task: Add player rehearsal note capture and mutation flows) | opencode | gpt-5.1-codex-max"
```

### Task 5: Run the notes-and-rehearsal quality gate and record implementation status

**Files:**
- Modify: `docs/plans/2026-03-10-notes-rehearsal-implementation.md`
- Modify: `docs/plans/2026-03-10-product-completion-program-implementation.md`
- Verify: `backend/tests/test_api.py`
- Verify: `frontend/src/redesign/pages/__tests__/SongDetailPage.notes.test.tsx`
- Verify: `frontend/src/redesign/pages/__tests__/PlayerPage.test.tsx`
- Verify: `frontend/src/__tests__/App.integration.test.tsx`

**Step 1: Write the failing test**

```md
<phase id="notes-rehearsal-plan-execution" status="planned">
  <task>[ ] Task 1: Lock the backend note-truth contract with failing API tests.</task>
  <task>[ ] Task 2: Align frontend note types and route hydration with the truthful contract.</task>
  <task>[ ] Task 3: Add song-detail note CRUD and resolved-state interactions.</task>
  <task>[ ] Task 4: Add player rehearsal note capture and mutation flows.</task>
  <task>[ ] Task 5: Run the notes-and-rehearsal quality gate and record implementation status.</task>
</phase>
```

Treat incomplete XML tracking, missing verification evidence, and an un-updated Slice 4 ledger entry as the failure condition for this final task.

**Step 2: Run test to verify it fails**

Run: `uv run --project backend pytest backend/tests/test_api.py -k "song_notes_support_resolve_and_truthful_payloads or notes_and_playback_prefs_crud or create_time_note_requires_timestamp_sec or create_chord_note_requires_chord_index" -q && npm --prefix frontend test -- --run src/redesign/pages/__tests__/SongDetailPage.notes.test.tsx src/redesign/pages/__tests__/PlayerPage.test.tsx src/__tests__/App.integration.test.tsx`
Expected: PASS for code only after Tasks 1-4 are complete, but documentation still fails until this plan and the Slice 4 ledger entry are updated with final status and verification evidence.

**Step 3: Write minimal implementation**

```md
<phase id="notes-rehearsal-plan-execution" status="completed">
  <task>[x] Task 1: Lock the backend note-truth contract with failing API tests.</task>
  <task>[x] Task 2: Align frontend note types and route hydration with the truthful contract.</task>
  <task>[x] Task 3: Add song-detail note CRUD and resolved-state interactions.</task>
  <task>[x] Task 4: Add player rehearsal note capture and mutation flows.</task>
  <task>[x] Task 5: Run the notes-and-rehearsal quality gate and record implementation status.</task>
</phase>
```

After code is green, record all of the following:
- exact backend and frontend commands from the quality gate
- the pre-reset result and the post-`make reset` rerun result
- manual verification using `test songs/Clara Luciani - La grenade.mp3`
- Slice 4 status and commit links in `docs/plans/2026-03-10-product-completion-program-implementation.md`

**Step 4: Run test to verify it passes**

Run: `uv run --project backend pytest backend/tests/test_api.py -k "song_notes_support_resolve_and_truthful_payloads or notes_and_playback_prefs_crud or create_time_note_requires_timestamp_sec or create_chord_note_requires_chord_index" -q && npm --prefix frontend test -- --run src/redesign/pages/__tests__/SongDetailPage.notes.test.tsx src/redesign/pages/__tests__/PlayerPage.test.tsx src/__tests__/App.integration.test.tsx && make reset && uv run --project backend pytest backend/tests/test_api.py -k "song_notes_support_resolve_and_truthful_payloads or notes_and_playback_prefs_crud or create_time_note_requires_timestamp_sec or create_chord_note_requires_chord_index" -q && npm --prefix frontend test -- --run src/redesign/pages/__tests__/SongDetailPage.notes.test.tsx src/redesign/pages/__tests__/PlayerPage.test.tsx src/__tests__/App.integration.test.tsx`
Expected: PASS. Then manually verify the rehearsal note flow with the real song fixture.

## Notes and Rehearsal Quality Gate

- `uv run --project backend pytest backend/tests/test_api.py -k "song_notes_support_resolve_and_truthful_payloads or notes_and_playback_prefs_crud or create_time_note_requires_timestamp_sec or create_chord_note_requires_chord_index" -q`
- `npm --prefix frontend test -- --run src/redesign/pages/__tests__/SongDetailPage.notes.test.tsx src/redesign/pages/__tests__/PlayerPage.test.tsx src/__tests__/App.integration.test.tsx`
- `make reset`
- rerun the same backend and frontend commands after reset
- manual verification with `test songs/Clara Luciani - La grenade.mp3` covering:
  - create a chord-linked note from song detail
  - create a time-linked note from the player at the live transport time
  - edit note text from one surface and confirm the other surface reflects it after refresh
  - resolve and reopen a note, confirming open/resolved grouping stays honest
  - delete a note and confirm it disappears from both surfaces

### Task 5 Verification Record

- Fill this section only after implementation.
- Record exact command output summaries, reset evidence, manual verification notes, and Slice 4 ledger updates here.

**Step 5: Commit**

```bash
git add docs/plans/2026-03-10-notes-rehearsal-implementation.md docs/plans/2026-03-10-product-completion-program-implementation.md
git commit -m "docs: record notes rehearsal verification status (docs/plans/2026-03-10-notes-rehearsal-implementation.md task: Run the notes-and-rehearsal quality gate and record implementation status) | opencode | gpt-5.1-codex-max"
```

This final commit is documentation-only. Do not restage code already captured by the earlier atomic commits.
