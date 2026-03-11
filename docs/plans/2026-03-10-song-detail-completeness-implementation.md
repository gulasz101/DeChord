# Song Detail Completeness Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make song-detail asset management honest by turning `Upload Stem` into a real flow, surfacing real stem/tab provenance, and refreshing the active song-detail route after every asset action.

**Architecture:** Keep route ownership in `frontend/src/App.tsx`, keep `frontend/src/redesign/pages/SongDetailPage.tsx` presentational, and extend the current backend/API contracts just enough to support real stem uploads plus truthful provenance rendering. Reuse the existing stem and tab regeneration endpoints, and fetch tab metadata alongside song and stem detail so one shared refresh path rehydrates the page after upload or regenerate actions.

**Tech Stack:** React 19, TypeScript, Vite, Vitest, Testing Library, FastAPI, pytest, LibSQL.

---

## XML Tracking

<phase id="song-detail-completeness-plan-execution" status="planned">
  <task>[ ] Task 1: Lock the song-detail asset API contract in frontend tests.</task>
  <task>[ ] Task 2: Add backend upload-stem and provenance support.</task>
  <task>[ ] Task 3: Render honest asset management in `SongDetailPage`.</task>
  <task>[ ] Task 4: Wire song-detail refresh behavior in `App.tsx`.</task>
  <task>[ ] Task 5: Verify the slice end-to-end and record the implementation result.</task>
</phase>

### Task 1: Lock the song-detail asset API contract in frontend tests

**Files:**
- Create: `frontend/src/lib/__tests__/api.song-detail-assets.test.ts`
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/lib/types.ts`
- Test: `frontend/src/lib/__tests__/api.song-detail-assets.test.ts`

**Step 1: Write the failing test**

```ts
import { describe, expect, it, vi } from "vitest";
import { getSongTabs, listSongStems, uploadSongStem } from "../api";

describe("song detail asset api", () => {
  it("returns stem provenance metadata", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        stems: [
          {
            id: 10,
            stem_key: "bass",
            source_type: "user",
            display_name: "Bass DI",
            version_label: "manual-2",
            is_archived: false,
            uploaded_by_name: "Groove Bassline",
            relative_path: "stems/30/bass.wav",
            created_at: "2026-03-10T10:00:00Z",
          },
        ],
      }),
    }) as unknown as typeof fetch;

    await expect(listSongStems(30)).resolves.toMatchObject({
      stems: [expect.objectContaining({ source_type: "user", uploaded_by_name: "Groove Bassline" })],
    });
  });

  it("uploads a song-scoped stem with form data", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ stems: [] }) });
    global.fetch = fetchMock as unknown as typeof fetch;

    await uploadSongStem(30, { stemKey: "bass", file: new File(["bass"], "bass.wav", { type: "audio/wav" }) });

    expect(fetchMock).toHaveBeenCalledWith("/api/songs/30/stems/upload", expect.objectContaining({ method: "POST" }));
  });

  it("returns current tab provenance metadata", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        tab: {
          id: 99,
          source_stem_key: "bass",
          source_type: "user",
          source_display_name: "Bass DI",
          tab_format: "alphatex",
          generator_version: "v2-rhythm-grid",
          status: "complete",
          updated_at: "2026-03-10T10:05:00Z",
        },
      }),
    }) as unknown as typeof fetch;

    await expect(getSongTabs(30)).resolves.toMatchObject({
      tab: expect.objectContaining({ source_stem_key: "bass", source_display_name: "Bass DI" }),
    });
  });
});
```

**Step 2: Run test to verify it fails**

Run: `npm --prefix frontend test -- --run src/lib/__tests__/api.song-detail-assets.test.ts`
Expected: FAIL because `uploadSongStem(...)` does not exist yet and the current stem/tab types do not include provenance fields.

**Step 3: Write minimal implementation**

```ts
export interface SongStemMeta {
  id: number;
  stem_key: string;
  source_type: "system" | "user";
  display_name: string;
  version_label: string;
  uploaded_by_name: string | null;
  is_archived: boolean;
  created_at: string;
}

export async function uploadSongStem(songId: number, payload: { stemKey: string; file: File }) {
  const form = new FormData();
  form.append("stem_key", payload.stemKey);
  form.append("file", payload.file);
  const res = await fetch(`${BASE}/api/songs/${songId}/stems/upload`, { method: "POST", body: form });
  if (!res.ok) throw new Error("Failed to upload stem");
  return res.json();
}
```

Only add the API surface and type fields needed for the rest of this slice. Do not add frontend-only fake provenance mapping.

**Step 4: Run test to verify it passes**

Run: `npm --prefix frontend test -- --run src/lib/__tests__/api.song-detail-assets.test.ts`
Expected: PASS.

**Step 5: Commit**

```bash
git add frontend/src/lib/__tests__/api.song-detail-assets.test.ts frontend/src/lib/api.ts frontend/src/lib/types.ts
git commit -m "test: lock song detail asset api contract (docs/plans/2026-03-10-song-detail-completeness-implementation.md task: Lock the song-detail asset API contract in frontend tests) | opencode | gpt-5.1-codex-max"
```

### Task 2: Add backend upload-stem and provenance support

**Files:**
- Modify: `backend/app/main.py`
- Modify: `backend/app/db_schema.sql`
- Modify: `backend/tests/test_api.py`
- Test: `backend/tests/test_api.py`

**Step 1: Write the failing test**

```py
def test_upload_song_stem_persists_user_asset_and_returns_provenance(tmp_path, monkeypatch):
    client = _build_client(tmp_path, monkeypatch)
    import app.main as main

    inserted = asyncio.run(
        main.execute(
            """
            INSERT INTO songs (user_id, title, original_filename, mime_type, audio_blob)
            VALUES (1, 'Demo Song', 'demo.mp3', 'audio/mpeg', x'00')
            RETURNING id
            """
        )
    )
    song_id = int(inserted.rows[0][0])

    stale_dir = tmp_path / "stale"
    stale_dir.mkdir(parents=True, exist_ok=True)
    stale_bass = stale_dir / "bass.wav"
    stale_bass.write_bytes(b"old-system-bass")
    asyncio.run(
        main.execute(
            """
            INSERT INTO song_stems (song_id, stem_key, relative_path, mime_type, duration)
            VALUES (?, 'bass', ?, 'audio/x-wav', 1.0)
            """,
            [song_id, str(stale_bass)],
        )
    )

    response = client.post(
        f"/api/songs/{song_id}/stems/upload",
        data={"stem_key": "bass"},
        files={"file": ("bass.wav", b"bass-audio", "audio/wav")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert [stem["stem_key"] for stem in payload["stems"]] == ["bass"]
    assert payload["stems"][0]["source_type"] == "user"
    assert payload["stems"][0]["uploaded_by_name"] is not None
    assert payload["stems"][0]["is_archived"] is False

    persisted = asyncio.run(
        main.execute(
            "SELECT stem_key, relative_path FROM song_stems WHERE song_id = ? ORDER BY stem_key ASC",
            [song_id],
        )
    )
    assert len(persisted.rows) == 1
    assert tuple(persisted.rows[0])[0] == "bass"
    assert tuple(persisted.rows[0])[1] != str(stale_bass)


def test_song_tabs_metadata_includes_source_provenance_fields(tmp_path, monkeypatch):
    client = _build_client(tmp_path, monkeypatch)
    import app.main as main

    inserted = asyncio.run(
        main.execute(
            """
            INSERT INTO songs (user_id, title, original_filename, mime_type, audio_blob)
            VALUES (1, 'Demo Song', 'demo.mp3', 'audio/mpeg', x'00')
            RETURNING id
            """
        )
    )
    song_id = int(inserted.rows[0][0])

    stem_dir = tmp_path / "uploaded" / str(song_id)
    stem_dir.mkdir(parents=True, exist_ok=True)
    bass = stem_dir / "bass.wav"
    bass.write_bytes(b"user-bass")
    asyncio.run(
        main.execute(
            """
            INSERT INTO song_stems (song_id, stem_key, relative_path, mime_type, duration)
            VALUES (?, 'bass', ?, 'audio/x-wav', 2.0)
            """,
            [song_id, str(bass)],
        )
    )
    midi_inserted = asyncio.run(
        main.execute(
            """
            INSERT INTO song_midis (song_id, source_stem_key, midi_blob, midi_format, engine, status, error_message)
            VALUES (?, 'bass', x'4D546864', 'mid', 'test', 'complete', NULL)
            RETURNING id
            """,
            [song_id],
        )
    )
    midi_id = int(midi_inserted.rows[0][0])
    asyncio.run(
        main.execute(
            """
            INSERT INTO song_tabs (song_id, source_midi_id, tab_blob, tab_format, tuning, strings, generator_version, status, error_message)
            VALUES (?, ?, ?, 'alphatex', 'E1,A1,D2,G2', 4, 'v2-rhythm-grid', 'complete', NULL)
            """,
            [song_id, midi_id, b"\\tempo 120\n\\sync(0 0 0 0)"],
        )
    )

    tabs_meta = client.get(f"/api/songs/{song_id}/tabs")

    assert tabs_meta.status_code == 200
    assert tabs_meta.json()["tab"]["source_stem_key"] == "bass"
    assert tabs_meta.json()["tab"]["source_type"] == "user"
```

**Step 2: Run test to verify it fails**

Run: `uv run --project backend pytest backend/tests/test_api.py -k "upload_song_stem_persists_user_asset_and_returns_provenance or song_tabs_metadata_includes_source_provenance_fields" -q`
Expected: FAIL because the upload endpoint does not exist yet and `/api/songs/{song_id}/tabs` does not return source provenance beyond `source_stem_key`.

**Step 3: Write minimal implementation**

```py
@app.post("/api/songs/{song_id}/stems/upload")
async def upload_song_stem(song_id: int, stem_key: str = Form(...), file: UploadFile = File(...)):
    content = await file.read()
    # validate song exists, write uploads to stems/<song_id>/uploads/, and upsert the
    # single active row for (song_id, stem_key) with user provenance metadata
    return {"stems": await _load_song_stems(song_id)}
```

Use this exact truth model for the slice:
- `song_stems` has one active row per `(song_id, stem_key)` because `backend/app/db_schema.sql` enforces `UNIQUE(song_id, stem_key)`.
- manual upload replaces the current active row for that `song_id + stem_key`; the API response for this slice returns only the active rows, not hidden history rows.
- stem regeneration replaces the active system rows for the generated `stem_key` values; it does not promise side-by-side active manual and system variants for the same key.
- frontend copy and tests must follow that exact contract: newest active asset wins for the key, and provenance explains whether the active row is `user` or `system`.

Add only the smallest schema and response changes needed so the frontend can render that current-state provenance truth. Do not invent archival/history behavior in this slice unless the backend actually persists and returns it.

**Step 4: Run test to verify it passes**

Run: `uv run --project backend pytest backend/tests/test_api.py -k "upload_song_stem_persists_user_asset_and_returns_provenance or song_tabs_metadata_includes_source_provenance_fields" -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add backend/app/main.py backend/app/db_schema.sql backend/tests/test_api.py
git commit -m "feat: add song detail stem provenance support (docs/plans/2026-03-10-song-detail-completeness-implementation.md task: Add backend upload-stem and provenance support) | opencode | gpt-5.1-codex-max"
```

### Task 3: Render honest asset management in `SongDetailPage`

**Files:**
- Modify: `frontend/src/redesign/pages/SongDetailPage.tsx`
- Modify: `frontend/src/redesign/pages/__tests__/SongDetailPage.test.tsx`
- Modify: `frontend/src/redesign/lib/types.ts`
- Test: `frontend/src/redesign/pages/__tests__/SongDetailPage.test.tsx`

**Step 1: Write the failing test**

```tsx
it("shows current stem provenance, uploads a stem, and renders current tab provenance", async () => {
  const onUploadStem = vi.fn().mockResolvedValue(undefined);

  render(
    <SongDetailPage
      user={user}
      band={band}
      project={project}
      song={{
        ...song,
        stems: [
          {
            id: "bass-user",
            stemKey: "bass",
            label: "Bass DI",
            uploaderName: "Groove Bassline",
            sourceType: "User",
            description: "Uploaded 2026-03-10",
            version: 2,
            isArchived: false,
            createdAt: "2026-03-10T10:00:00Z",
          },
        ],
        tab: {
          sourceStemKey: "bass",
          sourceDisplayName: "Bass DI",
          sourceType: "User",
          status: "complete",
          generatorVersion: "v2-rhythm-grid",
          updatedAt: "2026-03-10T10:05:00Z",
        },
      }}
      onOpenPlayer={() => {}}
      onBack={() => {}}
      onUploadStem={onUploadStem}
    />,
  );

  expect(screen.getByText("Bass DI")).toBeTruthy();
  expect(screen.getByText("User")).toBeTruthy();
  expect(screen.getByText(/Current bass tab/i)).toBeTruthy();
  expect(screen.getByText(/Generated from Bass DI/i)).toBeTruthy();

  fireEvent.click(screen.getByText("Upload Stem"));
  fireEvent.change(screen.getByLabelText("Stem File"), { target: { files: [new File(["bass"], "bass.wav", { type: "audio/wav" })] } });
  fireEvent.change(screen.getByLabelText("Stem Role"), { target: { value: "bass" } });
  fireEvent.click(screen.getByText("Confirm Stem Upload"));

  await waitFor(() => {
    expect(onUploadStem).toHaveBeenCalled();
  });
});
```

**Step 2: Run test to verify it fails**

Run: `npm --prefix frontend test -- --run src/redesign/pages/__tests__/SongDetailPage.test.tsx`
Expected: FAIL because the page has no real upload-stem panel and no tab provenance block.

**Step 3: Write minimal implementation**

```tsx
<button onClick={() => setOpenPanel(openPanel === "upload" ? null : "upload")}>Upload Stem</button>
{song.tab ? <section><h3>Current bass tab</h3><p>Generated from {song.tab.sourceDisplayName}</p></section> : null}
```

Implementation details to keep:
- add an upload panel with file input, stem-role selector, submit button, and inline loading/error/success states
- keep one action panel open at a time (`upload`, `stems`, or `tabs`)
- render provenance from route data, not from hardcoded labels
- if tab metadata is absent, show an honest empty state instead of fake readiness
- do not add comments workflow changes in this task

**Step 4: Run test to verify it passes**

Run: `npm --prefix frontend test -- --run src/redesign/pages/__tests__/SongDetailPage.test.tsx`
Expected: PASS.

**Step 5: Commit**

```bash
git add frontend/src/redesign/pages/SongDetailPage.tsx frontend/src/redesign/pages/__tests__/SongDetailPage.test.tsx frontend/src/redesign/lib/types.ts
git commit -m "feat: render honest song detail asset management (docs/plans/2026-03-10-song-detail-completeness-implementation.md task: Render honest asset management in SongDetailPage) | opencode | gpt-5.1-codex-max"
```

### Task 4: Wire song-detail refresh behavior in `App.tsx`

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/__tests__/App.integration.test.tsx`
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/lib/types.ts`
- Test: `frontend/src/__tests__/App.integration.test.tsx`

**Step 1: Write the failing test**

```tsx
it("refreshes song detail after upload and tab regeneration using the active route helper", async () => {
  getSongTabsMock
    .mockResolvedValueOnce({ tab: null })
    .mockResolvedValueOnce({
      tab: {
        id: 1,
        source_stem_key: "bass",
        source_type: "user",
        source_display_name: "Bass DI",
        tab_format: "alphatex",
        generator_version: "v2-rhythm-grid",
        status: "complete",
        error_message: null,
        created_at: "2026-03-10",
        updated_at: "2026-03-10",
      },
    });

  render(<App />);
  // navigate to song detail
  fireEvent.click(screen.getByText("Upload Stem"));
  fireEvent.change(screen.getByLabelText("Stem File"), { target: { files: [new File(["bass"], "bass.wav", { type: "audio/wav" })] } });
  fireEvent.click(screen.getByText("Confirm Stem Upload"));

  await waitFor(() => {
    expect(uploadSongStemMock).toHaveBeenCalledWith(30, expect.objectContaining({ stemKey: "bass" }));
  });
  await waitFor(() => {
    expect(getSongMock.mock.calls.length).toBeGreaterThan(1);
    expect(listSongStemsMock.mock.calls.length).toBeGreaterThan(1);
    expect(getSongTabsMock.mock.calls.length).toBeGreaterThan(1);
  });
});
```

**Step 2: Run test to verify it fails**

Run: `npm --prefix frontend test -- --run src/__tests__/App.integration.test.tsx`
Expected: FAIL because `App.tsx` does not yet fetch tab metadata into the song-detail route and has no upload-stem callback or shared song-detail asset refresh helper.

**Step 3: Write minimal implementation**

```tsx
const refreshSongDetailAssets = useCallback(async () => {
  if (route.page !== "song-detail") return;
  const detailed = await loadSongDetails(route.song);
  setRoute({ page: "song-detail", band: route.band, project: route.project, song: detailed });
}, [loadSongDetails, route]);
```

Implementation details to keep:
- extend `loadSongDetails(...)` to fetch `getSongTabs(songId)` alongside `getSong(songId)` and `listSongStems(songId)`
- map backend tab metadata into the song-detail route model
- pass `onUploadStem`, `onGenerateStems`, and `onGenerateBassTab` callbacks that all reuse the same active-route refresh helper
- keep refresh route-aware so it does not overwrite navigation after the user leaves the page

**Step 4: Run test to verify it passes**

Run: `npm --prefix frontend test -- --run src/__tests__/App.integration.test.tsx`
Expected: PASS, including the new song-detail asset refresh path.

**Step 5: Commit**

```bash
git add frontend/src/App.tsx frontend/src/__tests__/App.integration.test.tsx frontend/src/lib/api.ts frontend/src/lib/types.ts
git commit -m "feat: wire song detail asset refresh flow (docs/plans/2026-03-10-song-detail-completeness-implementation.md task: Wire song-detail refresh behavior in App.tsx) | opencode | gpt-5.1-codex-max"
```

### Task 5: Verify the slice end-to-end and record the implementation result

**Files:**
- Modify: `docs/plans/2026-03-10-song-detail-completeness-implementation.md`
- Modify: `docs/plans/2026-03-10-product-completion-program-implementation.md`
- Verify: `frontend/src/lib/__tests__/api.song-detail-assets.test.ts`
- Verify: `frontend/src/redesign/pages/__tests__/SongDetailPage.test.tsx`
- Verify: `frontend/src/__tests__/App.integration.test.tsx`
- Verify: `backend/tests/test_api.py`

**Step 1: Write the failing test**

```md
<phase id="song-detail-completeness-plan-execution" status="planned">
  <task>[ ] Task 1: Lock the song-detail asset API contract in frontend tests.</task>
  <task>[ ] Task 2: Add backend upload-stem and provenance support.</task>
  <task>[ ] Task 3: Render honest asset management in `SongDetailPage`.</task>
  <task>[ ] Task 4: Wire song-detail refresh behavior in `App.tsx`.</task>
  <task>[ ] Task 5: Verify the slice end-to-end and record the implementation result.</task>
</phase>
```

Treat incomplete XML tracking and missing verification notes as the failure condition for this final task.

**Step 2: Run test to verify it fails**

Run: `npm --prefix frontend test -- --run src/lib/__tests__/api.song-detail-assets.test.ts src/redesign/pages/__tests__/SongDetailPage.test.tsx src/__tests__/App.integration.test.tsx && uv run --project backend pytest backend/tests/test_api.py -k "upload_song_stem_persists_user_asset_and_returns_provenance or song_tabs_metadata_includes_source_provenance_fields or regenerate_song_stems or regenerate_song_tabs" -q`
Expected: PASS for code if Tasks 1-4 are complete, but documentation still fails until this plan and the master plan are updated with final status and verification evidence.

**Step 3: Write minimal implementation**

```md
<phase id="song-detail-completeness-plan-execution" status="completed">
  <task>[x] Task 1: Lock the song-detail asset API contract in frontend tests.</task>
  <task>[x] Task 2: Add backend upload-stem and provenance support.</task>
  <task>[x] Task 3: Render honest asset management in `SongDetailPage`.</task>
  <task>[x] Task 4: Wire song-detail refresh behavior in `App.tsx`.</task>
  <task>[x] Task 5: Verify the slice end-to-end and record the implementation result.</task>
</phase>
```

After code is green, record:
- exact focused frontend and backend commands with pass counts
- `make reset` and the post-reset rerun
- manual song-detail verification covering upload stem, regenerate stems, regenerate tab, and visible provenance
- slice status and commit links in the master plan ledger

**Step 4: Run test to verify it passes**

Run: `npm --prefix frontend test -- --run src/lib/__tests__/api.song-detail-assets.test.ts src/redesign/pages/__tests__/SongDetailPage.test.tsx src/__tests__/App.integration.test.tsx && uv run --project backend pytest backend/tests/test_api.py -k "upload_song_stem_persists_user_asset_and_returns_provenance or song_tabs_metadata_includes_source_provenance_fields or regenerate_song_stems or regenerate_song_tabs" -q && make reset && npm --prefix frontend test -- --run src/lib/__tests__/api.song-detail-assets.test.ts src/redesign/pages/__tests__/SongDetailPage.test.tsx src/__tests__/App.integration.test.tsx && uv run --project backend pytest backend/tests/test_api.py -k "upload_song_stem_persists_user_asset_and_returns_provenance or song_tabs_metadata_includes_source_provenance_fields or regenerate_song_stems or regenerate_song_tabs" -q`
Expected: PASS. Then manually verify the real song-detail asset flows.

**Step 5: Commit**

```bash
git add docs/plans/2026-03-10-song-detail-completeness-implementation.md docs/plans/2026-03-10-product-completion-program-implementation.md
git commit -m "docs: record song detail completeness verification status (docs/plans/2026-03-10-song-detail-completeness-implementation.md task: Verify the slice end-to-end and record the implementation result) | opencode | gpt-5.1-codex-max"
```

This final commit is documentation-only. Do not restage code already captured by the earlier atomic commits.
