# Processing Journey Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a route-level processing journey that starts immediately after upload, shows honest live job progress, and automatically opens the new song detail page when processing completes.

**Architecture:** Keep upload state in the existing `frontend/src/App.tsx` route shell by adding a `processing-journey` route, a presentational page for the journey UI, and a route-aware polling loop built on top of `uploadAudio`, `getJobStatus`, `getResult`, `getSong`, and `listSongStems`. Do not introduce persistent jobs infrastructure, a global jobs center, or background tracking outside the active route.

**Tech Stack:** React 19, TypeScript, Vite, Vitest, Testing Library, FastAPI API contracts.

---

## XML Tracking

<phase id="processing-journey-plan-execution" status="planned">
  <task>[ ] Task 1: Lock the processing journey API contract in frontend tests.</task>
  <task>[ ] Task 2: Add the processing journey page as a presentational route surface.</task>
  <task>[ ] Task 3: Wire upload, polling, and route transitions in App.tsx.</task>
  <task>[ ] Task 4: Verify the slice end-to-end and record the implementation result.</task>
</phase>

### Task 1: Lock the processing journey API contract in frontend tests

**Files:**
- Create: `frontend/src/lib/__tests__/api.processing-journey.test.ts`
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/lib/types.ts`
- Test: `frontend/src/lib/__tests__/api.processing-journey.test.ts`

**Step 1: Write the failing test**

```ts
import { describe, expect, it, vi } from "vitest";
import { getJobStatus, getResult } from "../api";

describe("processing journey api", () => {
  it("returns stage-rich status payloads", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        status: "processing",
        stage: "splitting_stems",
        progress_pct: 45,
        stage_history: ["queued", "analyzing_chords", "splitting_stems"],
        message: "Splitting stems...",
      }),
    }) as unknown as typeof fetch;

    await expect(getJobStatus("job-123")).resolves.toMatchObject({
      status: "processing",
      stage: "splitting_stems",
      progress_pct: 45,
    });
  });

  it("returns the completed song id from the result endpoint", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ song_id: 77, key: "Em", tempo: 120, duration: 42, chords: [] }),
    }) as unknown as typeof fetch;

    await expect(getResult("job-123")).resolves.toMatchObject({ song_id: 77 });
  });
});
```

**Step 2: Run test to verify it fails**

Run: `npm --prefix frontend test -- --run src/lib/__tests__/api.processing-journey.test.ts`
Expected: FAIL because the new test file does not exist yet, or because typings do not yet match the stage-rich payload assertions.

**Step 3: Write minimal implementation**

```ts
export interface AnalysisResult {
  song_id?: number;
}

export interface JobStatus {
  stage?: JobStage;
  stage_history?: JobStage[];
  progress_pct?: number;
  message?: string;
}
```

Create the new test file and only the minimal type or helper updates needed so `getJobStatus(...)` and `getResult(...)` remain the single source of truth for the route-level polling slice.

**Step 4: Run test to verify it passes**

Run: `npm --prefix frontend test -- --run src/lib/__tests__/api.processing-journey.test.ts`
Expected: PASS.

**Step 5: Commit**

```bash
git add frontend/src/lib/__tests__/api.processing-journey.test.ts frontend/src/lib/api.ts frontend/src/lib/types.ts
git commit -m "test: lock processing journey api contract (docs/plans/2026-03-10-processing-journey-implementation.md task: Lock the processing journey API contract in frontend tests) | opencode | gpt-5.1-codex-max"
```

### Task 2: Add the processing journey page as a presentational route surface

**Files:**
- Create: `frontend/src/redesign/pages/ProcessingJourneyPage.tsx`
- Create: `frontend/src/redesign/pages/__tests__/ProcessingJourneyPage.test.tsx`
- Modify: `frontend/src/redesign/lib/types.ts`
- Test: `frontend/src/redesign/pages/__tests__/ProcessingJourneyPage.test.tsx`

**Step 1: Write the failing test**

```tsx
import { render, screen } from "@testing-library/react";
import { ProcessingJourneyPage } from "../ProcessingJourneyPage";

it("renders an honest processing timeline and failure exit", () => {
  render(
    <ProcessingJourneyPage
      band={{ id: "10", name: "Default Band", avatarColor: "#000", members: [], projects: [] }}
      project={{ id: "20", name: "Default Project", description: "", songs: [], recentActivity: [], unreadCount: 0 }}
      journey={{
        songTitle: "La grenade",
        uploadFilename: "Clara Luciani - La grenade.mp3",
        status: "processing",
        stage: "splitting_stems",
        progressPct: 45,
        stageHistory: ["queued", "analyzing_chords", "splitting_stems"],
        message: "Splitting stems...",
        error: null,
      }}
      onBack={() => {}}
      onRetryRefresh={() => {}}
    />,
  );

  expect(screen.getByText("La grenade")).toBeTruthy();
  expect(screen.getByText("Splitting stems...")).toBeTruthy();
  expect(screen.getByText("queued")).toBeTruthy();
  expect(screen.getByText("analyzing_chords")).toBeTruthy();
  expect(screen.getByText("splitting_stems")).toBeTruthy();
});

it("renders failure recovery actions when the journey errors", () => {
  render(
    <ProcessingJourneyPage
      band={{ id: "10", name: "Default Band", avatarColor: "#000", members: [], projects: [] }}
      project={{ id: "20", name: "Default Project", description: "", songs: [], recentActivity: [], unreadCount: 0 }}
      journey={{
        songTitle: "La grenade",
        uploadFilename: "Clara Luciani - La grenade.mp3",
        status: "error",
        stage: "error",
        progressPct: 100,
        stageHistory: ["queued", "splitting_stems", "error"],
        message: "Processing failed",
        error: "Job not found after reset",
      }}
      onBack={() => {}}
      onRetryRefresh={() => {}}
    />,
  );

  expect(screen.getByText("Job not found after reset")).toBeTruthy();
  expect(screen.getByText("Back to Library")).toBeTruthy();
  expect(screen.getByText("Retry Refresh")).toBeTruthy();
});
```

**Step 2: Run test to verify it fails**

Run: `npm --prefix frontend test -- --run src/redesign/pages/__tests__/ProcessingJourneyPage.test.tsx`
Expected: FAIL because `ProcessingJourneyPage.tsx` and its journey props do not exist yet.

**Step 3: Write minimal implementation**

```tsx
export function ProcessingJourneyPage({ band, project, journey, onBack, onRetryRefresh }: Props) {
  return (
    <main>
      <h1>{journey.songTitle ?? journey.uploadFilename}</h1>
      <p>{journey.message}</p>
      <button onClick={onBack}>Back to Library</button>
      {journey.status === "error" ? <button onClick={onRetryRefresh}>Retry Refresh</button> : null}
    </main>
  );
}
```

Build only the route-level presentation for queued, processing, complete handoff, and error states. Keep it page-local and do not add data fetching inside this component.
The test and implementation must cover visible stage-history/timeline content plus the recovery actions promised by the design (`Back to Library` and `Retry Refresh`).

**Step 4: Run test to verify it passes**

Run: `npm --prefix frontend test -- --run src/redesign/pages/__tests__/ProcessingJourneyPage.test.tsx`
Expected: PASS.

**Step 5: Commit**

```bash
git add frontend/src/redesign/pages/ProcessingJourneyPage.tsx frontend/src/redesign/pages/__tests__/ProcessingJourneyPage.test.tsx frontend/src/redesign/lib/types.ts
git commit -m "feat: add processing journey page shell (docs/plans/2026-03-10-processing-journey-implementation.md task: Add the processing journey page as a presentational route surface) | opencode | gpt-5.1-codex-max"
```

### Task 3: Wire upload, polling, and route transitions in `App.tsx`

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/__tests__/App.integration.test.tsx`
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/redesign/pages/SongLibraryPage.tsx`
- Test: `frontend/src/__tests__/App.integration.test.tsx`

**Step 1: Write the failing test**

```tsx
it("navigates from upload to processing journey to song detail", async () => {
  uploadAudioMock.mockResolvedValueOnce({ job_id: "job-77", song_id: 77 });
  getJobStatusMock
    .mockResolvedValueOnce({ status: "queued", stage: "queued", progress_pct: 0, stage_history: ["queued"], message: "Queued" })
    .mockResolvedValueOnce({ status: "processing", stage: "splitting_stems", progress_pct: 45, stage_history: ["queued", "splitting_stems"], message: "Splitting stems..." })
    .mockResolvedValueOnce({ status: "complete", stage: "complete", progress_pct: 100, stage_history: ["queued", "splitting_stems", "complete"], message: "Completed" });
  getResultMock.mockResolvedValueOnce({ song_id: 77, key: "Em", tempo: 120, duration: 42, chords: [] });

  render(<App />);
  // existing upload interactions

  await waitFor(() => {
    expect(screen.getByText("Splitting stems...")).toBeTruthy();
  });

  await waitFor(() => {
    expect(screen.getByText("Generate Stems")).toBeTruthy();
  });
});
```

**Step 2: Run test to verify it fails**

Run: `npm --prefix frontend test -- --run src/__tests__/App.integration.test.tsx`
Expected: FAIL because `App.tsx` still refreshes the library directly after upload and has no processing route or polling lifecycle.

**Step 3: Write minimal implementation**

```tsx
type Route =
  | { page: "songs"; band: Band; project: Project }
  | {
      page: "processing-journey";
      band: Band;
      project: Project;
      songId: number;
      jobId: string;
      uploadFilename: string;
      processMode: ProcessMode;
      tabGenerationQuality: TabGenerationQuality;
    }
  | { page: "song-detail"; band: Band; project: Project; song: Song };

useEffect(() => {
  if (route.page !== "processing-journey") return;
  let cancelled = false;

  async function poll() {
    while (!cancelled) {
      const status = await getJobStatus(route.jobId);
      if (status.status === "complete") {
        const result = await getResult(route.jobId);
        const loadedBands = await refreshBands(user);
        const refreshedBand = findBandInHierarchy(loadedBands, route.band.id);
        const refreshedProject = findProjectInBand(refreshedBand, route.project.id);
        const projectSong = refreshedProject?.songs.find((song) => song.id === String(result.song_id ?? route.songId));
        const songSeed = projectSong ?? mapProjectSongSummaryToSong({
          id: result.song_id ?? route.songId,
          project_id: Number(route.project.id),
          title: route.uploadFilename.replace(/\.[^.]+$/, ""),
          original_filename: route.uploadFilename,
          created_at: new Date().toISOString(),
          key: result.key,
          tempo: result.tempo,
          duration: result.duration,
        });
        const songDetail = await getSong(result.song_id ?? route.songId);
        const stemsDetail = await listSongStems(result.song_id ?? route.songId);
        const detailed = mergeSongSummaryWithDetail(songSeed, songDetail, stemsDetail, user);
        setRoute({
          page: "song-detail",
          band: refreshedBand ?? route.band,
          project: refreshedProject ?? route.project,
          song: detailed,
        });
        return;
      }
      if (status.status === "error") {
        setJourneyState({ status: "error", error: status.error ?? "Processing failed" });
        return;
      }
      await new Promise((resolve) => setTimeout(resolve, 1000));
    }
  }

  void poll();
  return () => {
    cancelled = true;
  };
}, [route]);
```

Implementation details to keep:
- switch upload success from immediate library refresh to immediate `processing-journey` navigation
- include `processMode` and `tabGenerationQuality` in the route payload so the journey page can show honest upload context
- keep the polling loop route-aware and cancellable
- on completion, call `getResult(route.jobId)`, refresh hierarchy with `refreshBands(user)`, then call `getSong(songId)` and `listSongStems(songId)` to build the final `song-detail` route state
- use the existing `App.tsx` mapping helpers to merge summary, song detail, and stem data instead of inventing a `stubSong` shortcut
- handle `getJobStatus(...)` or `getResult(...)` failures as honest journey errors, including reset-lost jobs
- keep `SongLibraryPage` focused on upload initiation only

**Step 4: Run test to verify it passes**

Run: `npm --prefix frontend test -- --run src/__tests__/App.integration.test.tsx`
Expected: PASS, including the new upload-to-processing-to-song-detail path.

**Step 5: Commit**

```bash
git add frontend/src/App.tsx frontend/src/__tests__/App.integration.test.tsx frontend/src/lib/api.ts frontend/src/redesign/pages/SongLibraryPage.tsx
git commit -m "feat: wire route-level processing journey (docs/plans/2026-03-10-processing-journey-implementation.md task: Wire upload, polling, and route transitions in App.tsx) | opencode | gpt-5.1-codex-max"
```

### Task 4: Verify the slice end-to-end and record the implementation result

**Files:**
- Modify: `docs/plans/2026-03-10-processing-journey-implementation.md`
- Modify: `docs/plans/2026-03-10-product-completion-program-implementation.md`
- Verify: `frontend/src/lib/__tests__/api.processing-journey.test.ts`
- Verify: `frontend/src/redesign/pages/__tests__/ProcessingJourneyPage.test.tsx`
- Verify: `frontend/src/__tests__/App.integration.test.tsx`

**Step 1: Write the failing test**

```md
<phase id="processing-journey-plan-execution" status="planned">
  <task>[ ] Task 1: Lock the processing journey API contract in frontend tests.</task>
  <task>[ ] Task 2: Add the processing journey page as a presentational route surface.</task>
  <task>[ ] Task 3: Wire upload, polling, and route transitions in App.tsx.</task>
  <task>[ ] Task 4: Verify the slice end-to-end and record the implementation result.</task>
</phase>
```

Treat incomplete checklist state as the failure condition for this final task.

**Step 2: Run test to verify it fails**

Run: `npm --prefix frontend test -- --run src/lib/__tests__/api.processing-journey.test.ts src/redesign/pages/__tests__/ProcessingJourneyPage.test.tsx src/__tests__/App.integration.test.tsx`
Expected: PASS for code if previous tasks are done, but the documentation task still fails because the checklist and verification notes are not yet updated.

**Step 3: Write minimal implementation**

```md
<phase id="processing-journey-plan-execution" status="completed">
  <task>[x] Task 1: Lock the processing journey API contract in frontend tests.</task>
  <task>[x] Task 2: Add the processing journey page as a presentational route surface.</task>
  <task>[x] Task 3: Wire upload, polling, and route transitions in App.tsx.</task>
  <task>[x] Task 4: Verify the slice end-to-end and record the implementation result.</task>
</phase>
```

After code is green, record:
- exact test commands and outcomes in this plan
- manual verification using `test songs/Clara Luciani - La grenade.mp3`
- `make reset` followed by the focused rerun
- slice status and commit links in the master plan

**Step 4: Run test to verify it passes**

Run: `npm --prefix frontend test -- --run src/lib/__tests__/api.processing-journey.test.ts src/redesign/pages/__tests__/ProcessingJourneyPage.test.tsx src/__tests__/App.integration.test.tsx && make reset && npm --prefix frontend test -- --run src/lib/__tests__/api.processing-journey.test.ts src/redesign/pages/__tests__/ProcessingJourneyPage.test.tsx src/__tests__/App.integration.test.tsx`
Expected: PASS. Then manually verify upload with `test songs/Clara Luciani - La grenade.mp3`.

**Step 5: Commit**

```bash
git add docs/plans/2026-03-10-processing-journey-implementation.md docs/plans/2026-03-10-product-completion-program-implementation.md
git commit -m "docs: record processing journey verification status (docs/plans/2026-03-10-processing-journey-implementation.md task: Verify the slice end-to-end and record the implementation result) | opencode | gpt-5.1-codex-max"
```

This final commit is documentation-only. Do not restage code already captured by the earlier atomic commits.
