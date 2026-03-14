import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import "@testing-library/jest-dom";
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
    duration: number;
    playing: boolean;
    volume: number;
    speedPercent: number;
    loopActive: boolean;
    loopLabel?: string;
    noteMarkers: Array<{ id: number; timestampSec: number; userId: number | null; authorName?: string | null; text?: string; toastDurationSec?: number | null }>;
    currentUserId: number | null;
    onTogglePlay: () => void;
    onSeek: (time: number) => void;
    onSeekRelative: (delta: number) => void;
    onVolumeChange: (v: number) => void;
    onSpeedChange: (s: number) => void;
    onClearLoop: () => void;
    onCommentLaneClick: (timestampSec: number) => void;
    onMarkerClick: (noteId: number, timestampSec: number) => void;
  }) => {
    return (
      <div data-testid="transport-bar">
        <button type="button" onClick={props.onTogglePlay}>Play</button>
        <span>{props.currentTime.toFixed(1)}s</span>
        <span>{props.playing ? "playing" : "paused"}</span>
        <div
          data-testid="comment-lane"
          onClick={(e) => {
            const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
            const clickX = e.clientX - rect.left;
            const ratio = Math.max(0, Math.min(1, clickX / rect.width));
            const timestampSec = ratio * props.duration;
            props.onCommentLaneClick(timestampSec);
          }}
          style={{ position: "relative", height: 12, background: "#333" }}
        />
        {props.noteMarkers.map((marker) => (
          <button
            key={marker.id}
            type="button"
            data-testid={`comment-marker-${marker.id}`}
            onClick={() => props.onMarkerClick(marker.id, marker.timestampSec)}
          >
            Marker {marker.id}
          </button>
        ))}
      </div>
    );
  },
}));

vi.mock("../../components/TimelineCommentModal", () => ({
  TimelineCommentModal: (props: {
    mode: "create" | "edit" | "reply";
    timestampSec: number;
    defaultDurationSec: number;
    note?: import("../../lib/types").SongNote;
    onSave: (payload: { text: string; toastDurationSec: number }) => void;
    onReply?: (text: string) => void;
    onDelete?: (noteId: number) => void;
    onClose: () => void;
  }) => (
    <div data-testid="timeline-comment-modal">
      <span>{props.mode === "create" ? "Add Comment" : props.mode === "edit" ? "Edit Comment" : "Reply"}</span>
      <span>@ {Math.floor(props.timestampSec / 60)}:{String(Math.floor(props.timestampSec % 60)).padStart(2, "0")}</span>
      {props.note && <span data-testid="note-text">{props.note.text}</span>}
      <textarea
        aria-label="comment text"
        value={props.mode === "edit" && props.note ? props.note.text : ""}
        readOnly
      />
      <input
        type="number"
        aria-label="show for (seconds)"
        value={props.defaultDurationSec}
        readOnly
      />
      <button type="button" onClick={() => props.onSave({ text: props.note?.text ?? "test", toastDurationSec: props.defaultDurationSec })}>Save</button>
      {props.mode === "reply" && props.onReply && (
        <button type="button" onClick={() => props.onReply("reply text")}>Reply</button>
      )}
      {props.mode === "edit" && props.onDelete && props.note && (
        <button type="button" onClick={() => props.onDelete(props.note!.id)}>Delete</button>
      )}
      <button type="button" onClick={props.onClose}>Close</button>
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

const baseProps = {
  user,
  band,
  project,
  onBack: () => {},
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

  it("creates a time note from the current transport and a chord note from the current chord", async () => {
    const onCreateNote = vi.fn();
    const playerSong: Song = {
      ...song,
      chords: [
        { start: 0, end: 8, label: "C", section: "Verse" },
        { start: 8, end: 16, label: "F", section: "Verse" },
        { start: 16, end: 24, label: "G", section: "Verse" },
      ],
    };

    transportStore.update({ currentTime: 18.5 });

    render(
      <PlayerPage
        user={user}
        band={band}
        project={project}
        song={playerSong}
        onBack={() => {}}
        onCreateNote={onCreateNote}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /comments/i }));
    fireEvent.change(screen.getByLabelText(/note text/i), { target: { value: "Bass pickup drifts" } });
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /note at current time/i }));
      await Promise.resolve();
    });

    await waitFor(() => {
      expect(onCreateNote).toHaveBeenCalledWith({
        type: "time",
        text: "Bass pickup drifts",
        timestampSec: 18.5,
      });
    });

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /note on current chord/i }));
      await Promise.resolve();
    });

    await waitFor(() => {
      expect(onCreateNote).toHaveBeenLastCalledWith({
        type: "chord",
        text: "Bass pickup drifts",
        chordIndex: 2,
        timestampSec: 16,
      });
    });
  });

  it("exposes player note edit resolve reopen and delete actions", async () => {
    const onEditNote = vi.fn();
    const onResolveNote = vi.fn();
    const onDeleteNote = vi.fn();
    const notedSong: Song = {
      ...song,
      notes: [
        {
          id: 11,
          type: "time",
          timestampSec: 9.5,
          chordIndex: null,
          text: "Verse entry drifts",
          toastDurationSec: null,
          authorName: "Wojtek",
          authorAvatar: "WG",
          resolved: false,
          createdAt: "2026-03-10T10:00:00Z",
          updatedAt: "2026-03-10T10:00:00Z",
        },
        {
          id: 12,
          type: "chord",
          timestampSec: null,
          chordIndex: 1,
          text: "Lock the chorus push",
          toastDurationSec: null,
          authorName: "Wojtek",
          authorAvatar: "WG",
          resolved: true,
          createdAt: "2026-03-10T10:05:00Z",
          updatedAt: "2026-03-10T10:08:00Z",
        },
      ],
    };

    render(
      <PlayerPage
        user={user}
        band={band}
        project={project}
        song={notedSong}
        onBack={() => {}}
        onEditNote={onEditNote}
        onResolveNote={onResolveNote}
        onDeleteNote={onDeleteNote}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /comments/i }));
    fireEvent.click(screen.getByRole("button", { name: /edit note 11/i }));
    fireEvent.change(screen.getByLabelText(/edit note text/i), { target: { value: "Verse entry is rushing" } });
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /save note 11/i }));
      await Promise.resolve();
    });

    await waitFor(() => {
      expect(onEditNote).toHaveBeenCalledWith(11, { text: "Verse entry is rushing" });
    });

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /resolve note 11/i }));
      await Promise.resolve();
    });
    await waitFor(() => {
      expect(onResolveNote).toHaveBeenCalledWith(11, true);
    });

    fireEvent.click(screen.getByRole("button", { name: /show resolved/i }));
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /reopen note 12/i }));
      await Promise.resolve();
    });
    await waitFor(() => {
      expect(onResolveNote).toHaveBeenCalledWith(12, false);
    });

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /delete note 12/i }));
      await Promise.resolve();
    });
    await waitFor(() => {
      expect(onDeleteNote).toHaveBeenCalledWith(12);
    });
  });

  it("suppresses note mutation actions when no handlers are wired", () => {
    const notedSong: Song = {
      ...song,
      notes: [
        {
          id: 11,
          type: "time",
          timestampSec: 9.5,
          chordIndex: null,
          text: "Verse entry drifts",
          toastDurationSec: null,
          authorName: "Wojtek",
          authorAvatar: "WG",
          resolved: false,
          createdAt: "2026-03-10T10:00:00Z",
          updatedAt: "2026-03-10T10:00:00Z",
        },
      ],
    };

    render(
      <PlayerPage
        user={user}
        band={band}
        project={project}
        song={notedSong}
        onBack={() => {}}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /comments/i }));

    expect((screen.getByRole("button", { name: /note at current time/i }) as HTMLButtonElement).disabled).toBe(true);
    expect((screen.getByRole("button", { name: /note on current chord/i }) as HTMLButtonElement).disabled).toBe(true);
    expect(screen.queryByRole("button", { name: /edit note 11/i })).toBeNull();
    expect(screen.queryByRole("button", { name: /resolve note 11/i })).toBeNull();
    expect(screen.queryByRole("button", { name: /delete note 11/i })).toBeNull();
  });

  it("chord-type note creation passes timestampSec = chord start time", async () => {
    const onCreateNote = vi.fn();
    const playerSong: Song = {
      ...song,
      chords: [
        { start: 0, end: 5, label: "Am" },
        { start: 5, end: 10, label: "G" },
      ],
      notes: [],
    };

    render(
      <PlayerPage
        user={user}
        band={band}
        project={project}
        song={playerSong}
        onBack={() => {}}
        onCreateNote={onCreateNote}
      />,
    );

    act(() => {
      transportStore.update({ currentTime: 6 });
    });

    fireEvent.click(screen.getByRole("button", { name: /comments/i }));
    fireEvent.change(screen.getByLabelText(/note text/i), { target: { value: "G chord note" } });
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /note on current chord/i }));
      await Promise.resolve();
    });

    await waitFor(() => {
      expect(onCreateNote).toHaveBeenCalledWith(
        expect.objectContaining({
          type: "chord",
          chordIndex: 1,
          timestampSec: 5,
        }),
      );
    });
  });

  it("clicking empty comment lane opens create modal with correct timestamp", async () => {
    render(<PlayerPage {...baseProps} song={makeSong()} />);
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
        { ...noteDefaults, id: 5, type: "time", timestampSec: 30, text: "My note", userId: 1, toastDurationSec: 4 },
      ],
    });
    render(<PlayerPage {...baseProps} song={song} currentUserId={1} />);
    const markerButton = screen.getByTestId("comment-marker-5");
    fireEvent.click(markerButton);
    const modal = await screen.findByTestId("timeline-comment-modal");
    expect(modal).toHaveTextContent(/edit comment/i);
    expect(screen.getByDisplayValue("My note")).toBeInTheDocument();
  });

  it("clicking another user's marker opens reply modal", async () => {
    const song = makeSong({
      notes: [
        { ...noteDefaults, id: 6, type: "time", timestampSec: 30, text: "Their note", userId: 99, toastDurationSec: 4 },
      ],
    });
    render(<PlayerPage {...baseProps} song={song} currentUserId={1} />);
    fireEvent.click(screen.getByTestId("comment-marker-6"));
    const modal = await screen.findByTestId("timeline-comment-modal");
    expect(modal.firstChild?.textContent).toMatch(/^Reply/);
    expect(screen.getByText("Their note")).toBeInTheDocument(); // parent preview
  });

  it("default duration in create modal = time remaining in clicked chord", async () => {
    const song = makeSong({
      chords: [
        { start: 0, end: 10, label: "Am" },
        { start: 10, end: 18, label: "G" },
      ],
      duration: 18,
      notes: [],
    });
    transportStore.update({ duration: 18 });
    const { container } = render(<PlayerPage {...baseProps} song={song} />);
    const lane = container.querySelector('[data-testid="comment-lane"]') as HTMLElement;
    lane.getBoundingClientRect = () => ({ left: 0, width: 180, top: 0, right: 180, bottom: 12, height: 12, x: 0, y: 0, toJSON: () => "" });
    // Click at pixel 120 → ts = (120/180)*18 = 12s — inside G chord (10–18), remaining = 6s
    fireEvent.click(lane, { clientX: 120 });
    await screen.findByText(/add comment/i);
    expect(screen.getByLabelText(/show for/i)).toHaveValue(6);
  });

it("default duration falls back to 4s when click is past all chords", async () => {
  const song = makeSong({ chords: [{ start: 0, end: 5, label: "Am" }], duration: 120, notes: [] });
  const { container } = render(<PlayerPage {...baseProps} song={song} />);
  const lane = container.querySelector('[data-testid="comment-lane"]') as HTMLElement;
  lane.getBoundingClientRect = () => ({ left: 0, width: 120, top: 0, right: 120, bottom: 12, height: 12, x: 0, y: 0, toJSON: () => "" });
  // Click at pixel 60 → ts = 60s — past the only chord (ends at 5s)
  fireEvent.click(lane, { clientX: 60 });
  await screen.findByText(/add comment/i);
  expect(screen.getByLabelText(/show for/i)).toHaveValue(4);
});

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

describe("PlayerPage — toast authorName forwarding", () => {
  it("includes authorName in active toast when note fires", async () => {
    const song = makeSong({
      notes: [
        {
          ...noteDefaults,
          id: 42,
          type: "time",
          text: "bend up here",
          authorName: "Wojciech",
          timestampSec: 0,
          toastDurationSec: 5,
          resolved: false,
          userId: 1,
        },
      ],
    });

    render(<PlayerPage {...baseProps} song={song} currentUserId={1} />);

    act(() => {
      transportStore.update({ currentTime: 0.1 });
    });

    expect(await screen.findByTestId("toast-42")).toBeInTheDocument();
    expect(screen.getByText("Wojciech")).toBeInTheDocument();
  });

  it("removes toast from DOM after toastDurationSec + exit animation (350ms)", async () => {
    try {
      vi.useFakeTimers();
      const song = makeSong({
        notes: [
          {
            ...noteDefaults,
            id: 99,
            type: "time",
            text: "fade me out",
            authorName: "Anna",
            timestampSec: 0,
            toastDurationSec: 1,
            resolved: false,
            userId: 2,
          },
        ],
      });

      render(<PlayerPage {...baseProps} song={song} currentUserId={1} />);

      act(() => {
        transportStore.update({ currentTime: 0.1 });
      });
      expect(screen.getByTestId("toast-99")).toBeInTheDocument();

      act(() => {
        transportStore.update({ currentTime: 1.5 });
      });

      act(() => {
        vi.advanceTimersByTime(1000 + 350 + 50);
      });

      expect(screen.queryByTestId("toast-99")).not.toBeInTheDocument();
    } finally {
      vi.useRealTimers();
    }
  });
});
});
