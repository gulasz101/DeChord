# Stem Mixer Playback Mode Design

**Date:** 2026-03-16
**Status:** Draft

## Summary

Enable seamless switching between original song and stem playback during playback, with individual stem mute/unmute controls that work without interrupting playback.

## Requirements

1. **Mode switching** - User can switch between "Original" (full mix) and "Stems" mode during playback without interruption
2. **Stem toggling** - Individual stems can be muted/unmuted during playback with smooth fade transitions
3. **Instant response** - All mode and stem changes take effect immediately without stopping playback
4. **State preservation** - Stem selection state persists when switching modes

## Architecture

### Core Concept

Treat the full mix song file as a special stem with key `__full_mix__`. The mixer panel controls which "stems" are enabled, and the playback engine plays whatever is enabled.

### Components

**resolvePlaybackSources** - Always returns full mix as first source plus stems:
```typescript
function resolvePlaybackSources({ songId, stems, enabledBySourceKey }) {
  const sources = [
    { key: "__full_mix__", url: getAudioUrl(songId), enabled: enabledBySourceKey["__full_mix__"] ?? true },
    ...stems.map(stem => ({
      key: stem.stemKey,
      url: getStemAudioUrl(songId, stem.stemKey),
      enabled: enabledBySourceKey[stem.stemKey] ?? false,
    }))
  ];
  return { sources };
}
```

**useAudioPlayer** - Unified source handling with fade transitions:
- Accepts unified `sources: SourceConfig[]` instead of separate `src` + `stemSources`
- When `enabled` changes on any source, applies 75ms fade via volume ramp
- All audios stay loaded and in sync

**StemMixer** - New playback mode toggle in header:
- Radio buttons: "Original" / "Stems"
- Stem list visible only in stems mode
- Preserves stem selection when switching modes

## State Management

### PlayerPage State

```typescript
// New state
const [playbackMode, setPlaybackMode] = useState<"original" | "stems">("original");

// Existing state (unchanged)
const [activeStemKeys, setActiveStemKeys] = useState<Set<string>>(...);
const [selectedVersions, setSelectedVersions] = useState<Record<string, string>>(...);
```

### Derived State

```typescript
const enabledBySourceKey = useMemo(() => {
  if (playbackMode === "original") {
    // Only full mix enabled
    return { "__full_mix__": true, ...Object.fromEntries(stems.map(s => [s.stemKey, false])) };
  }
  // Stems mode: full mix muted, stems follow activeStemKeys
  return {
    "__full_mix__": false,
    ...Object.fromEntries(stems.map(s => [s.stemKey, activeStemKeys.has(s.stemKey)]))
  };
}, [playbackMode, activeStemKeys, stems]);
```

## UI Design

### StemMixer Layout

```
┌─────────────────────────────────────┐
│  Playback Mode                      │
│  ┌──────────┐ ┌──────────┐          │
│  │ ◉ Orig   │ │ ○ Stems  │          │
│  └──────────┘ └──────────┘          │
├─────────────────────────────────────┤
│  Stems                    2/4 active│  ← only visible in stems mode
│  ┌─────────────────────────────────┐│
│  │ ✓ Bass          System by Admin ││
│  │ ✓ Drums         System by Admin ││
│  │ ○ Vocals        System by Admin ││
│  │ ○ Guitar        System by Admin ││
│  └─────────────────────────────────┘│
└─────────────────────────────────────┘
```

### StemMixer Props

```typescript
interface StemMixerProps {
  // New
  playbackMode: "original" | "stems";
  onPlaybackModeChange: (mode: "original" | "stems") => void;
  hasStems: boolean;

  // Existing
  stems: StemInfo[];
  activeStemKeys: Set<string>;
  selectedVersions: Record<string, string>;
  onToggleStem: (stemKey: string) => void;
  onSelectVersion: (stemKey: string, stemId: string) => void;
}
```

## Fade Transition Implementation

### useAudioPlayer Changes

```typescript
// Track fade animation per audio
const fadeRafRef = useRef<Map<string, number>>(new Map());

// When enabled flags change, trigger fades
useEffect(() => {
  const audios = audioRefs.current;

  sources.forEach((source, idx) => {
    const audio = audios[idx];
    if (!audio) return;

    const currentEnabled = audio.volume > 0.01;
    const targetEnabled = source.enabled;

    if (currentEnabled !== targetEnabled) {
      fadeAudio(audio, source.key, targetEnabled, volume);
    }
  });
}, [sources.map(s => s.enabled).join(","), volume]);

function fadeAudio(
  audio: HTMLAudioElement,
  key: string,
  targetEnabled: boolean,
  targetVolume: number
) {
  // Cancel any existing fade for this audio
  const existingRaf = fadeRafRef.current.get(key);
  if (existingRaf) cancelAnimationFrame(existingRaf);

  const startVol = audio.volume;
  const endVol = targetEnabled ? targetVolume : 0;
  const duration = 75; // ms
  const startTime = performance.now();

  function tick(now: number) {
    const elapsed = now - startTime;
    const progress = Math.min(1, elapsed / duration);
    const eased = easeOutQuad(progress);

    audio.volume = startVol + (endVol - startVol) * eased;

    if (progress < 1) {
      fadeRafRef.current.set(key, requestAnimationFrame(tick));
    }
  }

  fadeRafRef.current.set(key, requestAnimationFrame(tick));
}

function easeOutQuad(t: number) {
  return 1 - (1 - t) * (1 - t);
}
```

### Fade Parameters

- **Duration:** 75ms (quick but smooth)
- **Easing:** easeOutQuad for natural feel
- **Behavior:** Independent fades per audio element, no blocking

## Error Handling

### No Stems Available

```typescript
// StemMixer - hide mode toggle entirely
{hasStems && (
  <div className="mode-toggle">...</div>
)}

// resolvePlaybackSources - return only full_mix
if (stems.length === 0) {
  return { sources: [{ key: "__full_mix__", url: getAudioUrl(songId), enabled: true }] };
}
```

### Audio Load Failure

```typescript
// useAudioPlayer - track load state per source
const [loadErrors, setLoadErrors] = useState<Set<string>>(new Set());

audio.addEventListener("error", () => {
  setLoadErrors(prev => new Set([...prev, source.key]));
});

// StemMixer - show warning indicator
{loadErrors.has(stem.stemKey) && (
  <span className="text-amber-500">⚠ Failed to load</span>
)}
```

### Edge Cases

1. **Switching mode mid-seek** - All audios seek together, no special handling
2. **Null songId** - Return empty sources array (already handled)
3. **Rapid stem toggling** - Fades compound naturally from current volume, no queueing needed

## Files to Modify

1. `frontend/src/lib/playbackSources.ts` - Unify source resolution
2. `frontend/src/hooks/useAudioPlayer.ts` - Add fade transitions, unified source handling
3. `frontend/src/redesign/components/StemMixer.tsx` - Add mode toggle UI
4. `frontend/src/redesign/pages/PlayerPage.tsx` - Add playbackMode state, update derived state

## Testing Considerations

- Verify fade timing with `performance.now()` assertions
- Test mode switching during active playback
- Test rapid stem toggle sequences
- Verify memory cleanup on component unmount
- Test with songs that have no stems
