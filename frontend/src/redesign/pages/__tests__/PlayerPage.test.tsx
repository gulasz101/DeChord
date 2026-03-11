import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { Band, Project, Song, User } from "../../lib/types";

const transportStore = vi.hoisted(() => {
  const listeners = new Set<() => void>();

  const baseState = {
    currentTime: 0,
    duration: 120,
    playing: false,
    volume: 0.8,
    playbackRate: 1,
    loop: null as { start: number; end: number } | null,
  };

  let state = { ...baseState };

  const emit = () => {
    listeners.forEach((listener) => listener());
  };

  const update = (partial: Partial<typeof baseState>) => {
    state = { ...state, ...partial };
    emit();
  };

  const togglePlay = vi.fn(() => {
    update({ playing: !state.playing });
  });
  const seek = vi.fn((time: number) => {
    update({ currentTime: time });
  });
  const seekRelative = vi.fn((delta: number) => {
    update({ currentTime: Math.max(0, state.currentTime + delta) });
  });
  const setPlaybackRate = vi.fn((rate: number) => {
    update({ playbackRate: rate });
  });
  const setVolume = vi.fn((volume: number) => {
    update({ volume });
  });
  const setLoop = vi.fn((loop: { start: number; end: number } | null) => {
    update({ loop });
  });

  return {
    getSnapshot: () => state,
    subscribe: (listener: () => void) => {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    update,
    reset: () => {
      state = { ...baseState };
      togglePlay.mockClear();
      seek.mockClear();
      seekRelative.mockClear();
      setPlaybackRate.mockClear();
      setVolume.mockClear();
      setLoop.mockClear();
    },
    togglePlay,
    seek,
    seekRelative,
    setPlaybackRate,
    setVolume,
    setLoop,
  };
});

const tabViewerPanelSpy = vi.hoisted(() => vi.fn());

vi.mock("../../../hooks/useAudioPlayer", async () => {
  const ReactModule = await import("react");

  return {
    useAudioPlayer: () => {
      const snapshot = ReactModule.useSyncExternalStore(
        transportStore.subscribe,
        transportStore.getSnapshot,
        transportStore.getSnapshot,
      );

      return {
        ...snapshot,
        play: vi.fn(),
        pause: vi.fn(),
        togglePlay: transportStore.togglePlay,
        seek: transportStore.seek,
        seekRelative: transportStore.seekRelative,
        setPlaybackRate: transportStore.setPlaybackRate,
        setVolume: transportStore.setVolume,
        setLoop: transportStore.setLoop,
      };
    },
  };
});

vi.mock("../../components/TransportBar", () => ({
  TransportBar: (props: {
    currentTime: number;
    playing: boolean;
    onTogglePlay: () => void;
  }) => (
    <div>
      <button type="button" onClick={props.onTogglePlay}>Play</button>
      <span>{props.currentTime.toFixed(1)}s</span>
      <span>{props.playing ? "playing" : "paused"}</span>
    </div>
  ),
}));

vi.mock("../../components/ChordTimeline", () => ({
  ChordTimeline: (props: {
    currentIndex: number;
    currentTime: number;
  }) => (
    <div>
      <span data-testid="current-chord-index">{props.currentIndex}</span>
      <span data-testid="current-chord-time">{props.currentTime.toFixed(1)}</span>
    </div>
  ),
}));

vi.mock("../../components/TabViewerPanel", () => ({
  TabViewerPanel: (props: { tabSourceUrl: string | null; currentTime: number; isPlaying: boolean }) => {
    tabViewerPanelSpy(props);
    return <div data-testid="tab-viewer-props">{JSON.stringify(props)}</div>;
  },
}));

vi.mock("../../components/Fretboard", () => ({ Fretboard: () => <div data-testid="fretboard" /> }));
vi.mock("../../components/StemMixer", () => ({ StemMixer: () => <div data-testid="stem-mixer" /> }));

import { PlayerPage } from "../PlayerPage";

const user: User = {
  id: "7",
  name: "Wojtek",
  email: "wojtek@example.com",
  instrument: "Bass",
  avatar: "WG",
};

const song: Song = {
  id: "30",
  title: "La grenade",
  artist: "Clara Luciani",
  key: "Dm",
  tempo: 120,
  duration: 120,
  status: "ready",
  chords: [
    { start: 0, end: 6, label: "Dm", section: "Verse" },
    { start: 6, end: 12, label: "Bb", section: "Verse" },
    { start: 12, end: 18, label: "F", section: "Verse" },
    { start: 18, end: 24, label: "C", section: "Verse" },
  ],
  stems: [],
  tab: {
    sourceStemKey: "bass",
    sourceDisplayName: "Bass stem",
    sourceType: "System",
    status: "ready",
    generatorVersion: "v1",
    updatedAt: "2026-03-10T12:00:00Z",
  },
  notes: [],
  updatedAt: "2026-03-10T12:00:00Z",
};

const songWithPlaybackPrefs: Song = {
  ...song,
  playbackPrefs: {
    speedPercent: 75,
    volume: 0.4,
    loopStartIndex: 1,
    loopEndIndex: 2,
  },
};

const songWithoutPlaybackPrefs: Song = {
  ...song,
  id: "31",
  title: "Nue",
  tab: null,
  playbackPrefs: null,
};

const project: Project = {
  id: "9",
  name: "Setlist",
  description: "Tour songs",
  songs: [song],
  recentActivity: [],
  unreadCount: 0,
};

const band: Band = {
  id: "4",
  name: "DeChord",
  members: [],
  projects: [project],
  avatarColor: "#7c3aed",
};

describe("PlayerPage", () => {
  afterEach(() => {
    transportStore.reset();
    tabViewerPanelSpy.mockClear();
  });

  it("drives chords, transport, and tabs from one real currentTime source", () => {
    render(<PlayerPage user={user} band={band} project={project} song={song} onBack={() => {}} />);

    fireEvent.click(screen.getByRole("button", { name: "Play" }));

    expect(transportStore.togglePlay).toHaveBeenCalledTimes(1);

    act(() => {
      transportStore.update({ currentTime: 18.5 });
    });

    expect(screen.getByText("18.5s")).toBeTruthy();
    expect(screen.getByTestId("current-chord-index").textContent).toBe("3");
    expect(tabViewerPanelSpy).toHaveBeenLastCalledWith({
      tabSourceUrl: "/api/songs/30/tabs/file",
      currentTime: 18.5,
      isPlaying: true,
    });
  });

  it("resets playback prefs to backend defaults when the next song has no prefs", () => {
    const { rerender } = render(
      <PlayerPage user={user} band={band} project={project} song={songWithPlaybackPrefs} onBack={() => {}} />,
    );

    expect(transportStore.getSnapshot()).toMatchObject({
      playbackRate: 0.75,
      volume: 0.4,
      loop: { start: 6, end: 18 },
    });

    rerender(
      <PlayerPage user={user} band={band} project={project} song={songWithoutPlaybackPrefs} onBack={() => {}} />,
    );

    expect(transportStore.getSnapshot()).toMatchObject({
      playbackRate: 1,
      volume: 1,
      loop: null,
    });
  });
});
