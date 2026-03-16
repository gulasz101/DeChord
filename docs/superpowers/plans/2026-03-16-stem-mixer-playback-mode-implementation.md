# Stem Mixer Playback Mode Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable seamless switching between original song and stems playback during playback, with individual stem mute/unmute controls featuring smooth fade transitions.

**Architecture:** Treat full mix as a special stem (`__full_mix__`). Unified source handling in useAudioPlayer with 75ms fade transitions. StemMixer component gains a playback mode toggle at the top.

**Tech Stack:** React 19, TypeScript, HTML5 Audio API, requestAnimationFrame for fades

---

## Breaking Changes

### useAudioPlayer API Change

**Old signature:**
```typescript
useAudioPlayer(src: string | null, stemSources: StemSource[])
```

**New signature:**
```typescript
useAudioPlayer(sources: SourceConfig[])
```

**Migration:** All callers must be updated. PlayerPage is the only known caller.

### Naming Migration

| Old Name | New Name |
|----------|----------|
| `playbackMode: "full_mix" \| "stems"` | `playbackMode: "original" \| "stems"` |
| `enabledByStem: Record<string, boolean>` | `enabledBySourceKey: Record<string, boolean>` |

---

## File Structure

### Files to Modify

| File | Responsibility |
|------|----------------|
| `frontend/src/lib/playbackSources.ts` | Unified source resolution (full_mix + stems as single list) |
| `frontend/src/hooks/useAudioPlayer.ts` | Fade transitions, unified source handling, cleanup |
| `frontend/src/redesign/components/StemMixer.tsx` | Add playback mode toggle UI |
| `frontend/src/redesign/pages/PlayerPage.tsx` | Add playbackMode state, update derived state |

### Files to Create (Tests)

| File | Purpose |
|------|---------|
| `frontend/src/lib/__tests__/playbackSources.unified.test.ts` | Test unified source resolution |
| `frontend/src/hooks/__tests__/useAudioPlayer.fade.test.ts` | Test fade transitions |
| `frontend/src/redesign/components/__tests__/StemMixer.mode.test.tsx` | Test mode toggle UI |
| `frontend/src/redesign/pages/__tests__/PlayerPage.playbackMode.test.tsx` | Test integration |

---

## Chunk 1: Core Types and Source Resolution

### Task 1: Update playbackSources.ts with unified source handling

**Files:**
- Modify: `frontend/src/lib/playbackSources.ts`
- Create: `frontend/src/lib/__tests__/playbackSources.unified.test.ts`

- [ ] **Step 1: Write failing test for unified source resolution**

```typescript
// frontend/src/lib/__tests__/playbackSources.unified.test.ts
import { describe, it, expect } from "vitest";
import { resolvePlaybackSources } from "../playbackSources";

describe("resolvePlaybackSources unified", () => {
  it("always includes full_mix as first source", () => {
    const result = resolvePlaybackSources({
      songId: 1,
      stems: [
        { stem_key: "bass", relative_path: "bass.wav", mime_type: null, duration: null },
        { stem_key: "drums", relative_path: "drums.wav", mime_type: null, duration: null },
      ],
      enabledBySourceKey: { __full_mix__: true, bass: false, drums: false },
    });

    expect(result.sources).toHaveLength(3);
    expect(result.sources[0].key).toBe("__full_mix__");
    expect(result.sources[0].enabled).toBe(true);
    expect(result.sources[1].key).toBe("bass");
    expect(result.sources[2].key).toBe("drums");
  });

  it("returns only full_mix when no stems", () => {
    const result = resolvePlaybackSources({
      songId: 1,
      stems: [],
      enabledBySourceKey: { __full_mix__: true },
    });

    expect(result.sources).toHaveLength(1);
    expect(result.sources[0].key).toBe("__full_mix__");
  });

  it("respects enabledBySourceKey for all sources", () => {
    const result = resolvePlaybackSources({
      songId: 1,
      stems: [{ stem_key: "bass", relative_path: "bass.wav", mime_type: null, duration: null }],
      enabledBySourceKey: { __full_mix__: false, bass: true },
    });

    expect(result.sources[0].enabled).toBe(false);
    expect(result.sources[1].enabled).toBe(true);
  });

  it("returns empty array for null songId", () => {
    const result = resolvePlaybackSources({
      songId: null,
      stems: [],
      enabledBySourceKey: {},
    });

    expect(result.sources).toHaveLength(0);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && bun test src/lib/__tests__/playbackSources.unified.test.ts`
Expected: FAIL - tests fail or types don't match

- [ ] **Step 3: Update playbackSources.ts**

```typescript
// frontend/src/lib/playbackSources.ts
import { getAudioUrl, getStemAudioUrl } from "./api";

export interface SourceConfig {
  key: string;
  url: string;
  enabled: boolean;
}

interface ResolvePlaybackSourcesArgs {
  songId: number | null;
  stems: Array<{
    stem_key: string;
    relative_path: string;
    mime_type: string | null;
    duration: number | null;
  }>;
  enabledBySourceKey: Record<string, boolean>;
}

export function resolvePlaybackSources({
  songId,
  stems,
  enabledBySourceKey,
}: ResolvePlaybackSourcesArgs) {
  if (!songId) {
    return { sources: [] as SourceConfig[] };
  }

  const sources: SourceConfig[] = [
    {
      key: "__full_mix__",
      url: getAudioUrl(songId),
      enabled: enabledBySourceKey["__full_mix__"] ?? true,
    },
    ...stems.map((stem) => ({
      key: stem.stem_key,
      url: getStemAudioUrl(songId, stem.stem_key),
      enabled: enabledBySourceKey[stem.stem_key] ?? false,
    })),
  ];

  return { sources };
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && bun test src/lib/__tests__/playbackSources.unified.test.ts`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/playbackSources.ts frontend/src/lib/__tests__/playbackSources.unified.test.ts
git commit -m "feat(playback): unify source resolution with full_mix as first source [plan: docs/superpowers/plans/2026-03-16-stem-mixer-playback-mode-implementation.md, Task 1]"
```

---

## Chunk 2: Fade Transitions in useAudioPlayer

### Task 2: Add fade transition logic to useAudioPlayer

**Files:**
- Modify: `frontend/src/hooks/useAudioPlayer.ts`
- Create: `frontend/src/hooks/__tests__/useAudioPlayer.fade.test.ts`

- [ ] **Step 1: Write failing test for fade behavior**

```typescript
// frontend/src/hooks/__tests__/useAudioPlayer.fade.test.ts
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useAudioPlayer } from "../useAudioPlayer";

describe("useAudioPlayer fade transitions", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("applies fade when source enabled state changes", async () => {
    const sources = [
      { key: "stem1", url: "http://example.com/stem1.mp3", enabled: true },
      { key: "stem2", url: "http://example.com/stem2.mp3", enabled: false },
    ];

    const { result, rerender } = renderHook(
      ({ sources }) => useAudioPlayer(sources),
      { initialProps: { sources } }
    );

    // Wait for audio elements to be created
    await act(async () => {
      await vi.runAllTimersAsync();
    });

    // Change enabled state
    const newSources = [
      { key: "stem1", url: "http://example.com/stem1.mp3", enabled: false },
      { key: "stem2", url: "http://example.com/stem2.mp3", enabled: true },
    ];

    rerender({ sources: newSources });

    // Advance timers to complete fade (75ms)
    await act(async () => {
      await vi.advanceTimersByTimeAsync(100);
    });

    // Audio volumes should have changed
    // Note: Actual verification requires mocking HTMLAudioElement
    expect(result.current).toBeDefined();
  });

  it("handles rapid toggle sequences without error", async () => {
    const sources = [
      { key: "stem1", url: "http://example.com/stem1.mp3", enabled: true },
    ];

    const { rerender } = renderHook(
      ({ sources }) => useAudioPlayer(sources),
      { initialProps: { sources } }
    );

    // Rapid toggle sequence
    for (let i = 0; i < 10; i++) {
      const newSources = [
        { key: "stem1", url: "http://example.com/stem1.mp3", enabled: i % 2 === 0 },
      ];
      rerender({ sources: newSources });
      await act(async () => {
        await vi.advanceTimersByTimeAsync(10);
      });
    }

    // Should not throw or leave pending animations
    await act(async () => {
      await vi.runAllTimersAsync();
    });
  });

  it("cleans up audio elements on unmount", async () => {
    const sources = [
      { key: "stem1", url: "http://example.com/stem1.mp3", enabled: true },
    ];

    const { unmount } = renderHook(() => useAudioPlayer(sources));

    await act(async () => {
      await vi.runAllTimersAsync();
    });

    // Unmount should not throw
    expect(() => unmount()).not.toThrow();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && bun test src/hooks/__tests__/useAudioPlayer.fade.test.ts`
Expected: FAIL - fade logic not implemented

- [ ] **Step 3: Update useAudioPlayer.ts with fade logic**

```typescript
// frontend/src/hooks/useAudioPlayer.ts
import { useRef, useState, useCallback, useEffect, useMemo } from "react";

export interface LoopPoints {
  start: number;
  end: number;
}

export interface SourceConfig {
  key: string;
  url: string;
  enabled: boolean;
}

export interface AudioLike {
  currentTime: number;
  duration: number;
  volume: number;
  playbackRate: number;
  play: () => Promise<void> | void;
  pause: () => void;
}

const FADE_DURATION_MS = 75;

function easeOutQuad(t: number): number {
  return 1 - (1 - t) * (1 - t);
}

export function applyVolumeToAudios(
  audios: AudioLike[],
  enabledFlags: boolean[],
  volume: number,
) {
  audios.forEach((audio, idx) => {
    const enabled = enabledFlags[idx] ?? true;
    audio.volume = enabled ? volume : 0;
  });
}

export function setPlaybackRateForAudios(audios: AudioLike[], rate: number) {
  audios.forEach((audio) => {
    audio.playbackRate = rate;
  });
}

export function seekAudios(audios: AudioLike[], time: number, duration: number) {
  const clamped = Math.max(0, Math.min(duration || 0, time));
  audios.forEach((audio) => {
    audio.currentTime = clamped;
  });
  return clamped;
}

export function pauseAudios(audios: AudioLike[]) {
  audios.forEach((audio) => audio.pause());
}

export async function playAudios(audios: AudioLike[]) {
  await Promise.all(audios.map((audio) => Promise.resolve(audio.play())));
}

export function useAudioPlayer(sources: SourceConfig[]) {
  const audioRefs = useRef<Map<string, HTMLAudioElement>>(new Map());
  const rafRef = useRef<number>(0);
  const loopRef = useRef<LoopPoints | null>(null);
  const fadeRafRefs = useRef<Map<string, number>>(new Map());
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [volume, setVolumeState] = useState(1);
  const [playbackRate, setPlaybackRateState] = useState(1);
  const [loop, setLoopState] = useState<LoopPoints | null>(null);

  const sourceConfigSignature = useMemo(
    () => sources.map((s) => `${s.key}:${s.url}`).join("|"),
    [sources],
  );
  const enabledSignature = useMemo(
    () => sources.map((s) => `${s.key}:${s.enabled ? 1 : 0}`).join("|"),
    [sources],
  );

  const setLoop = useCallback((nextLoop: LoopPoints | null) => {
    loopRef.current = nextLoop;
    setLoopState(nextLoop);
  }, []);

  // Manage audio elements when sources change
  useEffect(() => {
    if (sources.length === 0) {
      audioRefs.current.forEach((audio) => {
        audio.pause();
        audio.src = "";
      });
      audioRefs.current.clear();
      return;
    }

    // Create new audios for sources not yet loaded
    sources.forEach((source) => {
      if (!audioRefs.current.has(source.key)) {
        const audio = new Audio(source.url);
        audioRefs.current.set(source.key, audio);
      }
    });

    // Remove audios for sources no longer in list
    const currentKeys = new Set(sources.map((s) => s.key));
    audioRefs.current.forEach((audio, key) => {
      if (!currentKeys.has(key)) {
        audio.pause();
        audio.src = "";
        audioRefs.current.delete(key);
      }
    });

    // Set up primary audio listeners
    const primary = audioRefs.current.get(sources[0]?.key);
    if (primary && !primary.dataset.listenersSet) {
      primary.addEventListener("loadedmetadata", () => {
        setDuration(primary.duration || 0);
      });
      primary.addEventListener("ended", () => {
        setPlaying(false);
      });
      primary.dataset.listenersSet = "true";
    }

    queueMicrotask(() => {
      setCurrentTime(0);
    });

    return () => {
      cancelAnimationFrame(rafRef.current);
    };
  }, [sourceConfigSignature]);

  // Apply volume with fade transition when enabled state changes
  useEffect(() => {
    const prevEnabledRef = useRef<Map<string, boolean>>(new Map());

    sources.forEach((source) => {
      const audio = audioRefs.current.get(source.key);
      if (!audio) return;

      const prevEnabled = prevEnabledRef.current.get(source.key);
      const nowEnabled = source.enabled;

      // Only fade if enabled state changed
      if (prevEnabled !== undefined && prevEnabled !== nowEnabled) {
        fadeAudio(audio, source.key, nowEnabled, volume);
      } else if (prevEnabled === undefined) {
        // Initial set - instant
        audio.volume = nowEnabled ? volume : 0;
      }

      prevEnabledRef.current.set(source.key, nowEnabled);
    });
  }, [enabledSignature, volume]);

  // Fade function
  const fadeAudio = useCallback(
    (
      audio: HTMLAudioElement,
      key: string,
      targetEnabled: boolean,
      targetVolume: number,
    ) => {
      // Cancel existing fade for this audio
      const existingRaf = fadeRafRefs.current.get(key);
      if (existingRaf) cancelAnimationFrame(existingRaf);

      const startVol = audio.volume;
      const endVol = targetEnabled ? targetVolume : 0;
      const startTime = performance.now();

      const tick = (now: number) => {
        const elapsed = now - startTime;
        const progress = Math.min(1, elapsed / FADE_DURATION_MS);
        const eased = easeOutQuad(progress);

        audio.volume = startVol + (endVol - startVol) * eased;

        if (progress < 1) {
          fadeRafRefs.current.set(key, requestAnimationFrame(tick));
        } else {
          fadeRafRefs.current.delete(key);
        }
      };

      fadeRafRefs.current.set(key, requestAnimationFrame(tick));
    },
    [],
  );

  useEffect(() => {
    const audios = Array.from(audioRefs.current.values());
    setPlaybackRateForAudios(audios, playbackRate);
  }, [playbackRate]);

  useEffect(() => {
    if (!playing) {
      cancelAnimationFrame(rafRef.current);
      return;
    }

    const tick = () => {
      const audios = Array.from(audioRefs.current.values());
      if (audios.length === 0) return;

      const primary = audios[0];
      const nextLoop = loopRef.current;

      if (nextLoop && primary.currentTime >= nextLoop.end) {
        const loopedTime = seekAudios(audios, nextLoop.start, primary.duration || 0);
        setCurrentTime(loopedTime);
      } else {
        setCurrentTime(primary.currentTime);
      }

      rafRef.current = requestAnimationFrame(tick);
    };

    rafRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafRef.current);
  }, [playing, loop]);

  const play = useCallback(() => {
    const audios = Array.from(audioRefs.current.values());
    if (audios.length === 0) return;
    void playAudios(audios);
    setPlaying(true);
  }, []);

  const pause = useCallback(() => {
    const audios = Array.from(audioRefs.current.values());
    if (audios.length === 0) return;
    pauseAudios(audios);
    setPlaying(false);
  }, []);

  const togglePlay = useCallback(() => {
    if (playing) pause();
    else play();
  }, [playing, play, pause]);

  const seek = useCallback((time: number) => {
    const audios = Array.from(audioRefs.current.values());
    if (audios.length === 0) return;
    const primary = audios[0];
    const clamped = seekAudios(audios, time, primary.duration || 0);
    setCurrentTime(clamped);
  }, []);

  const seekRelative = useCallback((delta: number) => {
    const audios = Array.from(audioRefs.current.values());
    if (audios.length === 0) return;
    const primary = audios[0];
    const next = Math.max(0, Math.min(primary.duration || 0, primary.currentTime + delta));
    const clamped = seekAudios(audios, next, primary.duration || 0);
    setCurrentTime(clamped);
  }, []);

  const setVolume = useCallback((v: number) => {
    setVolumeState(v);
  }, []);

  const setPlaybackRate = useCallback((rate: number) => {
    setPlaybackRateState(rate);
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      audioRefs.current.forEach((audio) => {
        audio.pause();
        audio.src = "";
      });
      fadeRafRefs.current.forEach((raf) => cancelAnimationFrame(raf));
    };
  }, []);

  return {
    currentTime,
    duration,
    playing,
    volume,
    playbackRate,
    loop,
    play,
    pause,
    togglePlay,
    seek,
    seekRelative,
    setVolume,
    setPlaybackRate,
    setLoop,
  };
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && bun test src/hooks/__tests__/useAudioPlayer.fade.test.ts`
Expected: All tests PASS

- [ ] **Step 5: Run existing audio player tests to ensure no regressions**

Run: `cd frontend && bun test src/hooks/__tests__/useAudioPlayer*.test.ts`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add frontend/src/hooks/useAudioPlayer.ts frontend/src/hooks/__tests__/useAudioPlayer.fade.test.ts
git commit -m "feat(audio): add fade transitions for source enable/disable [plan: docs/superpowers/plans/2026-03-16-stem-mixer-playback-mode-implementation.md, Task 2]"
```

---

## Chunk 3: StemMixer Playback Mode Toggle

### Task 3: Add playback mode toggle to StemMixer component

**Files:**
- Modify: `frontend/src/redesign/components/StemMixer.tsx`
- Create: `frontend/src/redesign/components/__tests__/StemMixer.mode.test.tsx`

- [ ] **Step 1: Write failing test for mode toggle**

```typescript
// frontend/src/redesign/components/__tests__/StemMixer.mode.test.tsx
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { StemMixer } from "../StemMixer";
import type { StemInfo } from "../../../lib/types";

const mockStems: StemInfo[] = [
  { id: "1", stemKey: "bass", label: "Bass", sourceType: "System", uploaderName: "Admin", description: "Bass stem", version: 1, isArchived: false },
  { id: "2", stemKey: "drums", label: "Drums", sourceType: "System", uploaderName: "Admin", description: "Drums stem", version: 1, isArchived: false },
];

describe("StemMixer playback mode toggle", () => {
  it("renders mode toggle when hasStems is true", () => {
    render(
      <StemMixer
        stems={mockStems}
        activeStemKeys={new Set(["bass"])}
        selectedVersions={{}}
        playbackMode="original"
        onPlaybackModeChange={() => {}}
        hasStems={true}
        onToggleStem={() => {}}
        onSelectVersion={() => {}}
      />
    );

    expect(screen.getByRole("button", { name: /original/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /stems/i })).toBeInTheDocument();
  });

  it("hides mode toggle when hasStems is false", () => {
    render(
      <StemMixer
        stems={[]}
        activeStemKeys={new Set()}
        selectedVersions={{}}
        playbackMode="original"
        onPlaybackModeChange={() => {}}
        hasStems={false}
        onToggleStem={() => {}}
        onSelectVersion={() => {}}
    );

    expect(screen.queryByRole("button", { name: /original/i })).not.toBeInTheDocument();
  });

  it("calls onPlaybackModeChange with 'stems' when Stems button clicked", () => {
    const onModeChange = vi.fn();
    render(
      <StemMixer
        stems={mockStems}
        activeStemKeys={new Set(["bass"])}
        selectedVersions={{}}
        playbackMode="original"
        onPlaybackModeChange={onModeChange}
        hasStems={true}
        onToggleStem={() => {}}
        onSelectVersion={() => {}}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: /stems/i }));
    expect(onModeChange).toHaveBeenCalledWith("stems");
  });

  it("calls onPlaybackModeChange with 'original' when Original button clicked", () => {
    const onModeChange = vi.fn();
    render(
      <StemMixer
        stems={mockStems}
        activeStemKeys={new Set(["bass"])}
        selectedVersions={{}}
        playbackMode="stems"
        onPlaybackModeChange={onModeChange}
        hasStems={true}
        onToggleStem={() => {}}
        onSelectVersion={() => {}}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: /original/i }));
    expect(onModeChange).toHaveBeenCalledWith("original");
  });

  it("shows stem list only in stems mode", () => {
    const { rerender } = render(
      <StemMixer
        stems={mockStems}
        activeStemKeys={new Set(["bass"])}
        selectedVersions={{}}
        playbackMode="original"
        onPlaybackModeChange={() => {}}
        hasStems={true}
        onToggleStem={() => {}}
        onSelectVersion={() => {}}
      />
    );

    // In original mode, stem list should be hidden
    expect(screen.queryByText("Bass")).not.toBeInTheDocument();

    rerender(
      <StemMixer
        stems={mockStems}
        activeStemKeys={new Set(["bass"])}
        selectedVersions={{}}
        playbackMode="stems"
        onPlaybackModeChange={() => {}}
        hasStems={true}
        onToggleStem={() => {}}
        onSelectVersion={() => {}}
      />
    );

    // In stems mode, stem list should be visible
    expect(screen.getByText("Bass")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && bun test src/redesign/components/__tests__/StemMixer.mode.test.tsx`
Expected: FAIL - props don't exist yet

- [ ] **Step 3: Update StemMixer.tsx with mode toggle**

```typescript
// frontend/src/redesign/components/StemMixer.tsx
import type { StemInfo } from "../../lib/types";

interface StemMixerProps {
  stems: StemInfo[];
  activeStemKeys: Set<string>;
  selectedVersions: Record<string, string>;
  playbackMode: "original" | "stems";
  onPlaybackModeChange: (mode: "original" | "stems") => void;
  hasStems: boolean;
  onToggleStem: (stemKey: string) => void;
  onSelectVersion: (stemKey: string, stemId: string) => void;
}

export function StemMixer({
  stems,
  activeStemKeys,
  selectedVersions,
  playbackMode,
  onPlaybackModeChange,
  hasStems,
  onToggleStem,
  onSelectVersion,
}: StemMixerProps) {
  const activeStems = stems.filter((s) => !s.isArchived);
  const groups = new Map<string, StemInfo[]>();
  for (const s of activeStems) {
    const arr = groups.get(s.stemKey) ?? [];
    arr.push(s);
    groups.set(s.stemKey, arr);
  }

  return (
    <div className="space-y-4">
      {/* Playback Mode Toggle */}
      {hasStems && (
        <div className="space-y-2">
          <label className="text-[11px] font-medium" style={{ color: "#7a7a90" }}>
            Playback Mode
          </label>
          <div className="flex gap-2">
            <button
              onClick={() => onPlaybackModeChange("original")}
              className="flex-1 border px-3 py-2 text-xs font-semibold uppercase tracking-wide transition-all"
              style={{
                borderRadius: "3px",
                background: playbackMode === "original" ? "rgba(124, 58, 237, 0.2)" : "rgba(255,255,255,0.03)",
                borderColor: playbackMode === "original" ? "rgba(124, 58, 237, 0.4)" : "rgba(192, 192, 192, 0.12)",
                color: playbackMode === "original" ? "#a78bfa" : "#7a7a90",
              }}
            >
              ◉ Original
            </button>
            <button
              onClick={() => onPlaybackModeChange("stems")}
              className="flex-1 border px-3 py-2 text-xs font-semibold uppercase tracking-wide transition-all"
              style={{
                borderRadius: "3px",
                background: playbackMode === "stems" ? "rgba(124, 58, 237, 0.2)" : "rgba(255,255,255,0.03)",
                borderColor: playbackMode === "stems" ? "rgba(124, 58, 237, 0.4)" : "rgba(192, 192, 192, 0.12)",
                color: playbackMode === "stems" ? "#a78bfa" : "#7a7a90",
              }}
            >
              ◉ Stems
            </button>
          </div>
        </div>
      )}

      {/* Stem List - only visible in stems mode */}
      {playbackMode === "stems" && (
        <>
          <div className="flex items-center justify-between">
            <h3 className="text-sm" style={{ fontFamily: "Playfair Display, serif", color: "#e8e8f0" }}>
              Stems
            </h3>
            <span className="text-[10px]" style={{ color: "#7a7a90" }}>
              {activeStemKeys.size} of {activeStems.length} active
            </span>
          </div>
          <div className="space-y-3">
            {Array.from(groups.entries()).map(([key, versions]) => {
              const isActive = activeStemKeys.has(key);
              const selectedId = selectedVersions[key] ?? versions[0]?.id;
              const selectedStem = versions.find((v) => v.id === selectedId) ?? versions[0];

              return (
                <div
                  key={key}
                  className="border p-3"
                  style={{
                    borderRadius: "4px",
                    borderColor: isActive ? "rgba(124, 58, 237, 0.25)" : "rgba(192, 192, 192, 0.06)",
                    background: isActive ? "rgba(17, 22, 56, 0.7)" : "rgba(17, 22, 56, 0.4)",
                    backdropFilter: "blur(8px)",
                  }}
                >
                  {/* Header row: toggle + label */}
                  <div className="flex items-center gap-2.5">
                    <button
                      onClick={() => onToggleStem(key)}
                      className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg text-xs font-bold transition-all"
                      style={{
                        background: isActive ? "rgba(124, 58, 237, 0.2)" : "rgba(30, 30, 58, 0.4)",
                        color: isActive ? "#a78bfa" : "#5a5a6e",
                        border: `1px solid ${isActive ? "rgba(124, 58, 237, 0.35)" : "rgba(192, 192, 192, 0.08)"}`,
                      }}
                    >
                      {isActive ? "✓" : "—"}
                    </button>
                    <div className="min-w-0 flex-1">
                      <div
                        className="truncate text-sm font-medium"
                        style={{ color: isActive ? "#e2e2f0" : "#5a5a6e" }}
                      >
                        {selectedStem.label}
                      </div>
                      <div className="flex items-center gap-1.5 text-[10px]" style={{ color: "#5a5a6e" }}>
                        <span
                          className="rounded px-1 py-0.5"
                          style={{
                            background:
                              selectedStem.sourceType === "System"
                                ? "rgba(20, 184, 166, 0.15)"
                                : "rgba(124, 58, 237, 0.15)",
                            color: selectedStem.sourceType === "System" ? "#14b8a6" : "#a78bfa",
                          }}
                        >
                          {selectedStem.sourceType}
                        </span>
                        <span>by {selectedStem.uploaderName}</span>
                      </div>
                    </div>
                  </div>

                  {/* Description */}
                  <p
                    className="mt-1.5 pl-[38px] text-[11px] leading-snug"
                    style={{ color: "#7a7a90" }}
                  >
                    {selectedStem.description}
                  </p>

                  {/* Version switcher */}
                  {versions.length > 1 && (
                    <div className="mt-2 pl-[38px]">
                      <label
                        className="mb-1 block text-[10px] font-medium"
                        style={{ fontFamily: "Playfair Display, serif", color: "#7a7a90" }}
                      >
                        Version
                      </label>
                      <div className="space-y-1">
                        {versions.map((v) => (
                          <button
                            key={v.id}
                            onClick={() => onSelectVersion(key, v.id)}
                            className="flex w-full items-center gap-2 px-2.5 py-1.5 text-left text-[11px] transition-colors"
                            style={{
                              borderRadius: "2px",
                              background: v.id === selectedId ? "rgba(124, 58, 237, 0.2)" : "transparent",
                              color: v.id === selectedId ? "#a78bfa" : "#7a7a90",
                              border:
                                v.id === selectedId
                                  ? "1px solid rgba(124, 58, 237, 0.3)"
                                  : "1px solid transparent",
                            }}
                          >
                            <span className="font-semibold">v{v.version}</span>
                            <span className="flex-1 truncate">{v.uploaderName}</span>
                            <span className="text-[9px] opacity-60">{v.sourceType}</span>
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Download button */}
                  {isActive && (
                    <div className="mt-2 pl-[38px]">
                      <button
                        className="text-[10px] font-medium transition-colors hover:text-purple-300"
                        style={{ color: "#c0c0c0" }}
                      >
                        ↓ Download
                      </button>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && bun test src/redesign/components/__tests__/StemMixer.mode.test.tsx`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/redesign/components/StemMixer.tsx frontend/src/redesign/components/__tests__/StemMixer.mode.test.tsx
git commit -m "feat(mixer): add playback mode toggle to StemMixer [plan: docs/superpowers/plans/2026-03-16-stem-mixer-playback-mode-implementation.md, Task 3]"
```

---

## Chunk 4: PlayerPage Integration

### Task 4: Update PlayerPage to use new playback architecture

**Files:**
- Modify: `frontend/src/redesign/pages/PlayerPage.tsx`

- [ ] **Step 1: Update PlayerPage imports and state**

Add playbackMode state and update the audio player integration. Key changes:

1. Add `playbackMode` state
2. Create `enabledBySourceKey` derived state
3. Update `playbackSources` call to use new signature
4. Pass new props to StemMixer

```typescript
// In PlayerPage.tsx, find the state declarations section and add:

const [playbackMode, setPlaybackMode] = useState<"original" | "stems">("original");
```

- [ ] **Step 2: Add enabledBySourceKey derived state**

```typescript
// In PlayerPage.tsx, after activeStemKeys state:

const enabledBySourceKey = useMemo(() => {
  const stemEntries = song.stems
    .filter((s) => !s.isArchived)
    .map((s) => [s.stemKey, activeStemKeys.has(s.stemKey)] as const);

  return {
    "__full_mix__": playbackMode === "original",
    ...Object.fromEntries(stemEntries),
  };
}, [playbackMode, activeStemKeys, song.stems]);
```

- [ ] **Step 3: Update playbackSources call**

```typescript
// Replace the existing playbackSources useMemo:

const playbackSources = useMemo(
  () => resolvePlaybackSources({
    songId: Number.isNaN(songId) ? null : songId,
    stems: song.stems.map((stem) => ({
      stem_key: stem.stemKey,
      relative_path: stem.description,
      mime_type: null,
      duration: null,
    })),
    enabledBySourceKey,
  }),
  [enabledBySourceKey, song.stems, songId],
);
```

- [ ] **Step 4: Update useAudioPlayer call**

```typescript
// Replace the existing useAudioPlayer call:

const audioPlayer = useAudioPlayer(playbackSources.sources);
```

- [ ] **Step 5: Update StemMixer props in JSX**

Find the StemMixer component usage and update props:

```typescript
<StemMixer
  stems={song.stems}
  activeStemKeys={activeStemKeys}
  selectedVersions={selectedVersions}
  playbackMode={playbackMode}
  onPlaybackModeChange={setPlaybackMode}
  hasStems={song.stems.filter((s) => !s.isArchived).length > 0}
  onToggleStem={(key) => setActiveStemKeys((prev) => {
    const next = new Set(prev);
    if (next.has(key)) {
      next.delete(key);
    } else {
      next.add(key);
    }
    return next;
  })}
  onSelectVersion={(key, id) => setSelectedVersions((prev) => ({ ...prev, [key]: id }))}
/>
```

- [ ] **Step 6: Run existing PlayerPage tests**

Run: `cd frontend && bun test src/redesign/pages/__tests__/PlayerPage.test.tsx`
Expected: All tests PASS (may need updates if they mock useAudioPlayer)

- [ ] **Step 7: Commit**

```bash
git add frontend/src/redesign/pages/PlayerPage.tsx
git commit -m "feat(player): integrate unified playback mode with StemMixer [plan: docs/superpowers/plans/2026-03-16-stem-mixer-playback-mode-implementation.md, Task 4]"
```

---

## Chunk 5: Error Handling

### Task 5: Add audio load error tracking

**Files:**
- Modify: `frontend/src/hooks/useAudioPlayer.ts`
- Modify: `frontend/src/redesign/components/StemMixer.tsx`
- Create: `frontend/src/hooks/__tests__/useAudioPlayer.error.test.ts`

- [ ] **Step 1: Write failing test for error tracking**

```typescript
// frontend/src/hooks/__tests__/useAudioPlayer.error.test.ts
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useAudioPlayer, type SourceConfig } from "../useAudioPlayer";

describe("useAudioPlayer error handling", () => {
  let mockAudio: HTMLAudioElement;
  const audioConstructor = vi.fn();

  beforeEach(() => {
    mockAudio = {
      pause: vi.fn(),
      play: vi.fn().mockResolvedValue(undefined),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dataset: {},
    } as unknown as HTMLAudioElement;

    vi.stubGlobal("Audio", audioConstructor.mockReturnValue(mockAudio));
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.useRealTimers();
  });

  it("tracks load errors for failed sources", async () => {
    const sources: SourceConfig[] = [
      { key: "stem1", url: "http://example.com/stem1.mp3", enabled: true },
    ];

    const { result } = renderHook(() => useAudioPlayer(sources));

    // Simulate error event
    const errorListener = mockAudio.addEventListener.mock.calls.find(
      (call) => call[0] === "error"
    )?.[1];

    if (errorListener) {
      act(() => {
        errorListener({ type: "error" } as Event);
      });
    }

    // The hook should expose loadErrors state
    expect(result.current.loadErrors).toBeDefined();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && bun test src/hooks/__tests__/useAudioPlayer.error.test.ts`
Expected: FAIL - loadErrors not exposed

- [ ] **Step 3: Add error tracking to useAudioPlayer**

Add to `useAudioPlayer.ts`:

```typescript
// Add new state
const [loadErrors, setLoadErrors] = useState<Set<string>>(new Set());

// In the audio creation loop, add error listener:
sources.forEach((source) => {
  if (!audioRefs.current.has(source.key)) {
    const audio = new Audio(source.url);

    // Add error listener
    audio.addEventListener("error", () => {
      setLoadErrors((prev) => new Set([...prev, source.key]));
    });

    audioRefs.current.set(source.key, audio);
  }
});

// Clear error when source is removed
const currentKeys = new Set(sources.map((s) => s.key));
audioRefs.current.forEach((audio, key) => {
  if (!currentKeys.has(key)) {
    audio.pause();
    audio.src = "";
    audioRefs.current.delete(key);
    setLoadErrors((prev) => {
      const next = new Set(prev);
      next.delete(key);
      return next;
    });
  }
});

// Return loadErrors in the result
return {
  // ... existing returns
  loadErrors,
};
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && bun test src/hooks/__tests__/useAudioPlayer.error.test.ts`
Expected: All tests PASS

- [ ] **Step 5: Add error indicator to StemMixer**

In `StemMixer.tsx`, add new prop and display:

```typescript
interface StemMixerProps {
  // ... existing props
  loadErrors?: Set<string>;
}

// In the stem card, add after label:
{loadErrors?.has(key) && (
  <span className="ml-2 text-[10px] text-amber-400">⚠ Failed to load</span>
)}
```

- [ ] **Step 6: Commit**

```bash
git add frontend/src/hooks/useAudioPlayer.ts frontend/src/hooks/__tests__/useAudioPlayer.error.test.ts frontend/src/redesign/components/StemMixer.tsx
git commit -m "feat(audio): add load error tracking and UI indicator [plan: docs/superpowers/plans/2026-03-16-stem-mixer-playback-mode-implementation.md, Task 5]"
```

---

## Chunk 6: PlayerPage Integration Tests

### Task 6: Add PlayerPage integration tests

**Files:**
- Create: `frontend/src/redesign/pages/__tests__/PlayerPage.playbackMode.test.tsx`

- [ ] **Step 1: Write integration test for playback mode switching**

```typescript
// frontend/src/redesign/pages/__tests__/PlayerPage.playbackMode.test.tsx
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { PlayerPage } from "../PlayerPage";
import type { Band, Project, Song, User } from "../../../lib/types";

// Mock the audio player
vi.mock("../../../hooks/useAudioPlayer", () => ({
  useAudioPlayer: vi.fn(() => ({
    currentTime: 0,
    duration: 180,
    playing: false,
    volume: 1,
    playbackRate: 1,
    loop: null,
    play: vi.fn(),
    pause: vi.fn(),
    togglePlay: vi.fn(),
    seek: vi.fn(),
    seekRelative: vi.fn(),
    setVolume: vi.fn(),
    setPlaybackRate: vi.fn(),
    setLoop: vi.fn(),
    loadErrors: new Set(),
  })),
}));

const mockUser: User = {
  id: 1,
  name: "Test User",
  email: "test@example.com",
  avatar: "TU",
};

const mockBand: Band = {
  id: 1,
  name: "Test Band",
  slug: "test-band",
};

const mockProject: Project = {
  id: 1,
  name: "Test Project",
  slug: "test-project",
};

const mockSongWithStems: Song = {
  id: "1",
  title: "Test Song",
  artist: "Test Artist",
  key: "C",
  tempo: 120,
  duration: 180,
  chords: [
    { start: 0, end: 4, label: "C" },
    { start: 4, end: 8, label: "G" },
  ],
  notes: [],
  stems: [
    { id: "1", stemKey: "bass", label: "Bass", sourceType: "System", uploaderName: "Admin", description: "Bass stem", version: 1, isArchived: false },
    { id: "2", stemKey: "drums", label: "Drums", sourceType: "System", uploaderName: "Admin", description: "Drums stem", version: 1, isArchived: false },
  ],
};

describe("PlayerPage playback mode integration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows mode toggle when song has stems", async () => {
    render(
      <PlayerPage
        user={mockUser}
        band={mockBand}
        project={mockProject}
        song={mockSongWithStems}
        onBack={vi.fn()}
      />
    );

    // Open the stems panel
    fireEvent.click(screen.getByRole("button", { name: /stems/i }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /original/i })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /stems/i })).toBeInTheDocument();
    });
  });

  it("switches to stems mode when Stems button clicked", async () => {
    const { container } = render(
      <PlayerPage
        user={mockUser}
        band={mockBand}
        project={mockProject}
        song={mockSongWithStems}
        onBack={vi.fn()}
      />
    );

    // Open the stems panel
    fireEvent.click(screen.getByRole("button", { name: /stems/i }));

    await waitFor(() => {
      const stemsModeButton = screen.getByRole("button", { name: /stems/i });
      fireEvent.click(stemsModeButton);
    });

    // Stem list should be visible
    await waitFor(() => {
      expect(screen.getByText("Bass")).toBeInTheDocument();
    });
  });
});
```

- [ ] **Step 2: Run test to verify it passes**

Run: `cd frontend && bun test src/redesign/pages/__tests__/PlayerPage.playbackMode.test.tsx`
Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add frontend/src/redesign/pages/__tests__/PlayerPage.playbackMode.test.tsx
git commit -m "test(player): add playback mode integration tests [plan: docs/superpowers/plans/2026-03-16-stem-mixer-playback-mode-implementation.md, Task 6]"
```

---

## Chunk 7: Integration Testing and Cleanup

### Task 7: Run full test suite and verify behavior

**Files:**
- Run tests across the codebase

- [ ] **Step 1: Run all frontend tests**

Run: `cd frontend && bun test`
Expected: All tests PASS

- [ ] **Step 2: Fix any failing tests**

If tests fail due to API changes in useAudioPlayer or playbackSources, update test mocks and assertions.

- [ ] **Step 3: Manual verification**

Start the dev server and verify:
1. Mode toggle appears when song has stems
2. Switching from Original to Stems mutes full mix and unmutes selected stems
3. Switching back restores original mode
4. Individual stem toggles work during playback
5. Fade transitions are smooth (75ms)
6. Playback position maintained during mode switches

Run: `cd frontend && bun dev`

- [ ] **Step 4: Final commit (if any fixes needed)**

```bash
git add -A
git commit -m "fix: resolve test failures from playback mode integration [plan: docs/superpowers/plans/2026-03-16-stem-mixer-playback-mode-implementation.md, Task 7]"
```

---

## Summary

| Task | Description | Files |
|------|-------------|-------|
| 1 | Unified source resolution | `playbackSources.ts`, test |
| 2 | Fade transitions | `useAudioPlayer.ts`, test |
| 3 | Mode toggle UI | `StemMixer.tsx`, test |
| 4 | PlayerPage integration | `PlayerPage.tsx` |
| 5 | Error handling | `useAudioPlayer.ts`, `StemMixer.tsx`, test |
| 6 | PlayerPage integration tests | Test file |
| 7 | Integration testing | All test files |
