# Real Player Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make the player honest by replacing the simulated timer with one real audio-backed playback clock, loading real audio/tab assets, and syncing chords plus tabs to that shared transport.

**Architecture:** Keep route ownership in `frontend/src/App.tsx`, hydrate the player route from the existing song-detail loaders, and make `frontend/src/hooks/useAudioPlayer.ts` the only transport clock. `frontend/src/redesign/pages/PlayerPage.tsx` should become a thin player composition layer over real playback sources from `frontend/src/lib/playbackSources.ts`, while `frontend/src/components/TabViewerPanel.tsx`, `frontend/src/components/ChordTimeline.tsx`, and `frontend/src/components/TransportBar.tsx` all read/write the same hook state.

**Tech Stack:** React 19, TypeScript, Vite, Vitest, Testing Library, FastAPI, pytest, LibSQL.

---

## XML Tracking

<phase id="real-player-plan-execution" status="planned">
  <task>[ ] Task 1: Lock the player route and real-asset contract in tests.</task>
  <task>[ ] Task 2: Make `useAudioPlayer` the single transport clock.</task>
  <task>[ ] Task 3: Refactor `PlayerPage` and child components around real transport truth.</task>
  <task>[ ] Task 4: Wire `App.tsx` player hydration and optional playback-pref persistence.</task>
  <task>[ ] Task 5: Run the player quality gate and record implementation status.</task>
</phase>

### Task 1: Lock the player route and real-asset contract in tests

**Files:**
- Create: `frontend/src/redesign/pages/__tests__/PlayerPage.test.tsx`
- Modify: `frontend/src/lib/__tests__/playbackSources.mode.test.ts`
- Modify: `frontend/src/redesign/lib/types.ts`
- Test: `frontend/src/redesign/pages/__tests__/PlayerPage.test.tsx`
- Test: `frontend/src/lib/__tests__/playbackSources.mode.test.ts`

**Step 1: Write the failing test**

```tsx
it("renders the player shell with a real tab asset contract and no mock tab source", () => {
  render(<PlayerPage user={user} band={band} project={project} song={songWithTabAndPrefs} onBack={() => {}} />);

  expect(screen.queryByText("/mock-bass.alphatex")).toBeNull();
  expect(screen.getByTestId("player-page")).toHaveAttribute("data-tab-source-url", "/api/songs/30/tabs/file");
});
```

```ts
it("resolves full mix and selected stems to real backend urls", () => {
  expect(
    resolvePlaybackSources({
      songId: 30,
      playbackMode: "stems",
      stems: [{ stem_key: "drums", relative_path: "stems/30/drums.wav", mime_type: "audio/wav", duration: null }],
      enabledByStem: { drums: true },
    }),
  ).toMatchObject({
    audioSrc: "/api/audio/30",
    stemSources: [{ key: "drums", url: "/api/audio/30/stems/drums", enabled: true }],
    usingStems: true,
  });
});
```

**Step 2: Run test to verify it fails**

Run: `npm --prefix frontend test -- --run src/redesign/pages/__tests__/PlayerPage.test.tsx src/lib/__tests__/playbackSources.mode.test.ts`
Expected: FAIL because `PlayerPage` still hardcodes `"/mock-bass.alphatex"` and the component-level player contract is not yet locked to the real asset URLs.

**Step 3: Write minimal implementation**

```ts
export interface SongPlaybackPrefs {
  speedPercent: number;
  volume: number;
  loopStartIndex: number | null;
  loopEndIndex: number | null;
}
```

```tsx
<div data-testid="player-page" data-tab-source-url={tabSourceUrl ?? ""}>
  <TabViewerPanel tabSourceUrl={tabSourceUrl} currentTime={currentTime} isPlaying={playing} />
</div>
```

Implementation details to keep:
- add the player-facing playback-pref shape to `frontend/src/redesign/lib/types.ts` only as optional route data, not as a mandatory implementation promise for this slice
- keep `resolvePlaybackSources(...)` as the single source for real playback URLs
- add the smallest testable surface in `PlayerPage` so component tests can verify the real tab source without depending on route hydration work reserved for Task 4
- do not change backend code or `App.tsx` in this task

**Step 4: Run test to verify it passes**

Run: `npm --prefix frontend test -- --run src/redesign/pages/__tests__/PlayerPage.test.tsx src/lib/__tests__/playbackSources.mode.test.ts`
Expected: PASS.

**Step 5: Commit**

```bash
git add frontend/src/redesign/pages/__tests__/PlayerPage.test.tsx frontend/src/lib/__tests__/playbackSources.mode.test.ts frontend/src/redesign/lib/types.ts
git commit -m "test: lock real player asset contract (docs/plans/2026-03-10-real-player-implementation.md task: Lock the player route and real-asset contract in tests) | opencode | gpt-5.1-codex-max"
```

### Task 2: Make `useAudioPlayer` the single transport clock

**Files:**
- Modify: `frontend/src/hooks/useAudioPlayer.ts`
- Create: `frontend/src/hooks/__tests__/useAudioPlayer.transport.test.ts`
- Test: `frontend/src/hooks/__tests__/useAudioPlayer.transport.test.ts`

**Step 1: Write the failing test**

```ts
it("uses one clock for togglePlay, seek, loop, and ended cleanup", async () => {
  const hook = renderHook(() => useAudioPlayer("/api/audio/30"));

  act(() => {
    hook.result.current.seek(12);
    hook.result.current.setLoop({ start: 4, end: 8 });
    hook.result.current.togglePlay();
  });

  expect(hook.result.current.currentTime).toBe(12);

  act(() => {
    fakePrimaryAudio.currentTime = 8.1;
    runNextAnimationFrame();
  });

  expect(fakePrimaryAudio.currentTime).toBe(4);

  act(() => {
    fireEndedOnPrimaryAudio();
  });

  expect(hook.result.current.playing).toBe(false);
});
```

**Step 2: Run test to verify it fails**

Run: `npm --prefix frontend test -- --run src/hooks/__tests__/useAudioPlayer.transport.test.ts`
Expected: FAIL because the hook does not yet fully expose or guarantee all of the transport-truth behavior needed by `PlayerPage`, especially around loop/end cleanup and source lifecycle.

**Step 3: Write minimal implementation**

```ts
const togglePlay = useCallback(() => {
  const audios = audioRefs.current;
  if (audios.length === 0) return;
  if (playing) {
    pauseAudios(audios);
    setPlaying(false);
    return;
  }
  void playAudios(audios);
  setPlaying(true);
}, [playing]);
```

Implementation details to keep:
- the hook must remain the only transport clock used by the player
- treat `togglePlay` as the stable public play/pause control used by the page plan and tests
- preserve support for either one full mix or a set of enabled stems
- ensure loop handling, ended handling, and source teardown are explicit and testable
- do not reintroduce any page-level interval fallback

**Step 4: Run test to verify it passes**

Run: `npm --prefix frontend test -- --run src/hooks/__tests__/useAudioPlayer.transport.test.ts`
Expected: PASS.

**Step 5: Commit**

```bash
git add frontend/src/hooks/useAudioPlayer.ts frontend/src/hooks/__tests__/useAudioPlayer.transport.test.ts
git commit -m "feat: centralize real player transport clock (docs/plans/2026-03-10-real-player-implementation.md task: Make useAudioPlayer the single transport clock) | opencode | gpt-5.1-codex-max"
```

### Task 3: Refactor `PlayerPage` and child components around real transport truth

**Files:**
- Modify: `frontend/src/redesign/pages/PlayerPage.tsx`
- Modify: `frontend/src/components/TransportBar.tsx`
- Modify: `frontend/src/components/ChordTimeline.tsx`
- Modify: `frontend/src/components/TabViewerPanel.tsx`
- Modify: `frontend/src/redesign/pages/__tests__/PlayerPage.test.tsx`
- Modify: `frontend/src/components/__tests__/TabViewerPanel.test.tsx`
- Test: `frontend/src/redesign/pages/__tests__/PlayerPage.test.tsx`
- Test: `frontend/src/components/__tests__/TabViewerPanel.test.tsx`

**Step 1: Write the failing test**

```tsx
it("drives chords, transport, and tabs from one real currentTime source", async () => {
  render(<PlayerPage user={user} band={band} project={project} song={songWithTabAndPrefs} onBack={() => {}} />);

  fireEvent.click(screen.getByRole("button", { name: /play/i }));
  act(() => onHookTimeUpdate(18.5));

  expect(screen.getByText("18.5s")).toBeTruthy();
  expect(screen.getByTestId("current-chord-index")).toHaveTextContent("3");
  expect(tabViewerPanelSpy).toHaveBeenLastCalledWith(
    expect.objectContaining({ tabSourceUrl: "/api/songs/30/tabs/file", currentTime: 18.5, isPlaying: true }),
    expect.anything(),
  );
});
```

**Step 2: Run test to verify it fails**

Run: `npm --prefix frontend test -- --run src/redesign/pages/__tests__/PlayerPage.test.tsx src/components/__tests__/TabViewerPanel.test.tsx`
Expected: FAIL because `PlayerPage` still owns simulated transport state, the child component props are not yet aligned around the real hook contract, and the page still passes a mock tab URL.

**Step 3: Write minimal implementation**

```tsx
const tabSourceUrl = song.tab ? getTabFileUrl(Number(song.id)) : null;
const player = useAudioPlayer(audioSrc, stemSources);

const currentIndex = useMemo(() => {
  for (let i = song.chords.length - 1; i >= 0; i -= 1) {
    if (player.currentTime >= song.chords[i].start) return i;
  }
  return 0;
}, [player.currentTime, song.chords]);
```

Implementation details to keep:
- delete the page-local `setInterval(...)` playback simulation entirely
- initialize speed, volume, and loop UI from player prefs if present
- pass `player.currentTime`, `player.playing`, `player.seek`, `player.seekRelative`, `player.togglePlay`, `player.setPlaybackRate`, `player.setVolume`, and `player.setLoop` through to the child components as the single public transport contract
- reconcile prop mismatches in `TransportBar` and `ChordTimeline` so their public contracts match how the real player now uses them
- keep the player UI scope tight; no broad mixer redesign
- if prefs persistence is deferred, still wire sane local defaults so transport-truth work can land independently

**Step 4: Run test to verify it passes**

Run: `npm --prefix frontend test -- --run src/redesign/pages/__tests__/PlayerPage.test.tsx src/components/__tests__/TabViewerPanel.test.tsx`
Expected: PASS.

**Step 5: Commit**

```bash
git add frontend/src/redesign/pages/PlayerPage.tsx frontend/src/components/TransportBar.tsx frontend/src/components/ChordTimeline.tsx frontend/src/components/TabViewerPanel.tsx frontend/src/redesign/pages/__tests__/PlayerPage.test.tsx frontend/src/components/__tests__/TabViewerPanel.test.tsx
git commit -m "feat: wire player page to real transport truth (docs/plans/2026-03-10-real-player-implementation.md task: Refactor PlayerPage and child components around real transport truth) | opencode | gpt-5.1-codex-max"
```

### Task 4: Wire `App.tsx` player hydration and optional playback-pref persistence

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/redesign/lib/types.ts`
- Modify: `frontend/src/__tests__/App.integration.test.tsx`
- Test: `frontend/src/__tests__/App.integration.test.tsx`
- Modify: `frontend/src/lib/api.ts` (only if prefs persistence is included)
- Modify: `frontend/src/lib/types.ts` (only if prefs persistence is included)
- Verify: `backend/tests/test_api.py` (only if prefs persistence is included)

**Step 1: Write the failing test**

```tsx
it("hydrates the player route from song detail with the latest real song assets", async () => {
  render(<App />);

  // navigate to song detail, then open player

  await waitFor(() => {
    expect(getSongMock).toHaveBeenCalledWith(30);
  });

  await waitFor(() => {
    expect(screen.getByTestId("player-page")).toHaveAttribute("data-tab-source-url", "/api/songs/30/tabs/file");
  });
});
```

Optional follow-up test if prefs persistence is included in-slice:

```tsx
it("persists playback prefs only on discrete player setting changes", async () => {
  render(<App />);

  // navigate to song detail, then open player

  fireEvent.change(screen.getByLabelText(/speed/i), { target: { value: "80" } });

  await waitFor(() => {
    expect(savePlaybackPrefsMock).toHaveBeenCalledWith(30, {
      speed_percent: 80,
      volume: 1,
      loop_start_index: null,
      loop_end_index: null,
    });
  });
});
```

**Step 2: Run test to verify it fails**

Run: `npm --prefix frontend test -- --run src/__tests__/App.integration.test.tsx`
Expected: FAIL because the player route is not yet explicitly hydrated from the latest song detail before opening playback.

**Step 3: Write minimal implementation**

```tsx
const openPlayerForSong = useCallback(async (band: Band, project: Project, song: Song) => {
  const detailed = await loadSongDetails(song);
  setRoute({ page: "player", band, project, song: detailed });
}, [loadSongDetails]);
```

Optional prefs step if still in scope after transport truth lands:

```ts
await savePlaybackPrefs(songId, {
  speed_percent: speedPercent,
  volume,
  loop_start_index: loopStart,
  loop_end_index: loopEnd,
});
```

Implementation details to keep:
- hydrate the latest song detail before entering the `player` route
- map `playback_prefs` from `getSong(...)` into the redesign song model only if prefs persistence remains in scope
- keep prefs persistence optional for this slice; if transport truth is complete without it, defer the save path instead of forcing Task 4 to implement it
- if implemented, persist prefs only on discrete UI changes such as speed, volume, and loop adjustments; never on every playback tick
- keep `App.tsx` as the route owner and pass callbacks into `PlayerPage` instead of moving route logic into the page

**Step 4: Run test to verify it passes**

Run: `npm --prefix frontend test -- --run src/__tests__/App.integration.test.tsx`
Expected: PASS. If prefs persistence is included, also run `uv run --project backend pytest backend/tests/test_api.py -k "notes_and_playback_prefs_crud" -q` and expect PASS.

**Step 5: Commit**

```bash
git add frontend/src/App.tsx frontend/src/redesign/lib/types.ts frontend/src/__tests__/App.integration.test.tsx
git commit -m "feat: hydrate player route for real transport truth (docs/plans/2026-03-10-real-player-implementation.md task: Wire App.tsx player hydration and optional playback-pref persistence) | opencode | gpt-5.1-codex-max"
```

If prefs persistence is included in the same slice after transport truth is already green, make a separate small commit:

```bash
git add frontend/src/lib/api.ts frontend/src/lib/types.ts frontend/src/redesign/lib/types.ts frontend/src/App.tsx frontend/src/__tests__/App.integration.test.tsx
git commit -m "feat: persist optional real player playback prefs (docs/plans/2026-03-10-real-player-implementation.md task: Wire App.tsx player hydration and optional playback-pref persistence) | opencode | gpt-5.1-codex-max"
```

### Task 5: Run the player quality gate and record implementation status

**Files:**
- Modify: `docs/plans/2026-03-10-real-player-implementation.md`
- Modify: `docs/plans/2026-03-10-product-completion-program-implementation.md`
- Verify: `frontend/src/lib/__tests__/playbackSources.mode.test.ts`
- Verify: `frontend/src/hooks/__tests__/useAudioPlayer.transport.test.ts`
- Verify: `frontend/src/components/__tests__/TabViewerPanel.test.tsx`
- Verify: `frontend/src/redesign/pages/__tests__/PlayerPage.test.tsx`
- Verify: `frontend/src/__tests__/App.integration.test.tsx`
- Verify: `backend/tests/test_api.py`

**Step 1: Write the failing test**

```md
<phase id="real-player-plan-execution" status="planned">
  <task>[ ] Task 1: Lock the player route and real-asset contract in tests.</task>
  <task>[ ] Task 2: Make `useAudioPlayer` the single transport clock.</task>
  <task>[ ] Task 3: Refactor `PlayerPage` and child components around real transport truth.</task>
  <task>[ ] Task 4: Wire `App.tsx` player hydration and optional playback-pref persistence.</task>
  <task>[ ] Task 5: Run the player quality gate and record implementation status.</task>
</phase>
```

Treat incomplete XML tracking, missing verification evidence, and an un-updated Slice 3 ledger entry as the failure condition for this final task.

**Step 2: Run test to verify it fails**

Run: `npm --prefix frontend test -- --run src/lib/__tests__/playbackSources.mode.test.ts src/hooks/__tests__/useAudioPlayer.transport.test.ts src/components/__tests__/TabViewerPanel.test.tsx src/redesign/pages/__tests__/PlayerPage.test.tsx src/__tests__/App.integration.test.tsx`
Expected: PASS for code only after Tasks 1-4 are complete, but documentation still fails until this plan and the master plan ledger are updated with final status and verification evidence. If prefs persistence was included, also run `uv run --project backend pytest backend/tests/test_api.py -k "notes_and_playback_prefs_crud" -q` and expect PASS.

**Step 3: Write minimal implementation**

```md
<phase id="real-player-plan-execution" status="completed">
  <task>[x] Task 1: Lock the player route and real-asset contract in tests.</task>
  <task>[x] Task 2: Make `useAudioPlayer` the single transport clock.</task>
  <task>[x] Task 3: Refactor `PlayerPage` and child components around real transport truth.</task>
  <task>[x] Task 4: Wire `App.tsx` player hydration and optional playback-pref persistence.</task>
  <task>[x] Task 5: Run the player quality gate and record implementation status.</task>
</phase>
```

After code is green, record all of the following:
- exact frontend and backend commands from the player quality gate
- the pre-reset result and the post-`make reset` rerun result
- manual verification using `test songs/Clara Luciani - La grenade.mp3`
- Slice 3 status and commit links in `docs/plans/2026-03-10-product-completion-program-implementation.md`

**Step 4: Run test to verify it passes**

Run: `npm --prefix frontend test -- --run src/lib/__tests__/playbackSources.mode.test.ts src/hooks/__tests__/useAudioPlayer.transport.test.ts src/components/__tests__/TabViewerPanel.test.tsx src/redesign/pages/__tests__/PlayerPage.test.tsx src/__tests__/App.integration.test.tsx && make reset && npm --prefix frontend test -- --run src/lib/__tests__/playbackSources.mode.test.ts src/hooks/__tests__/useAudioPlayer.transport.test.ts src/components/__tests__/TabViewerPanel.test.tsx src/redesign/pages/__tests__/PlayerPage.test.tsx src/__tests__/App.integration.test.tsx`
Expected: PASS. Then manually verify the real player flow. If prefs persistence was included, also run `uv run --project backend pytest backend/tests/test_api.py -k "notes_and_playback_prefs_crud" -q` before reset and again after reset.

## Player Quality Gate

- `npm --prefix frontend test -- --run src/lib/__tests__/playbackSources.mode.test.ts src/hooks/__tests__/useAudioPlayer.transport.test.ts src/components/__tests__/TabViewerPanel.test.tsx src/redesign/pages/__tests__/PlayerPage.test.tsx src/__tests__/App.integration.test.tsx`
- if prefs persistence shipped, `uv run --project backend pytest backend/tests/test_api.py -k "notes_and_playback_prefs_crud" -q`
- `make reset`
- rerun the same commands above after reset
- manual verification with `test songs/Clara Luciani - La grenade.mp3` covering:
  - open player from a processed song
  - audible real play/pause/seek
  - chord click seeks real transport
  - tab viewer follows the same current time
  - stem playback mode, if enabled, still uses one shared clock
  - speed/volume/loop prefs restore only if persistence landed in the slice

### Task 5 Verification Record

- Record the exact pass/fail results here during execution.
- Record runtime URLs after the post-reset `make up` if manual verification requires a fresh runtime.
- Record the manual player observations here, including whether prefs persistence shipped or was explicitly deferred.

**Step 5: Commit**

```bash
git add docs/plans/2026-03-10-real-player-implementation.md docs/plans/2026-03-10-product-completion-program-implementation.md
git commit -m "docs: record real player verification status (docs/plans/2026-03-10-real-player-implementation.md task: Run the player quality gate and record implementation status) | opencode | gpt-5.1-codex-max"
```

This final commit is documentation-only. Do not restage code already captured by the earlier atomic commits.
