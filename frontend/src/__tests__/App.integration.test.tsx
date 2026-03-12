import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "../App";
import { resolveSongNote } from "../lib/api";
import { resolvePlaybackSources } from "../lib/playbackSources";

const {
  claimIdentityMock,
  uploadAudioMock,
  uploadSongStemMock,
  getJobStatusMock,
  getResultMock,
  regenerateSongStemsMock,
  regenerateSongTabsMock,
  getSongMock,
  getSongTabsMock,
  listSongStemsMock,
  listBandsMock,
  listBandMembersMock,
  listBandProjectsMock,
  getProjectActivityMock,
  listProjectSongsMock,
  createBandMock,
  createProjectMock,
  createSongNoteMock,
  updateSongNoteMock,
  resolveSongNoteMock,
  deleteSongNoteMock,
  playerPagePropsSpy,
} = vi.hoisted(() => ({
  claimIdentityMock: vi.fn().mockResolvedValue({
    user: {
      id: 1,
      display_name: "Groove Bassline",
      fingerprint_token: "fp-1",
      username: "bassbot",
      is_claimed: true,
    },
  }),
  uploadAudioMock: vi.fn().mockResolvedValue({
    job_id: "job-77",
    song_id: 77,
  }),
  uploadSongStemMock: vi.fn().mockResolvedValue({
    stems: [{ stem_key: "bass", relative_path: "stems/30/bass-di.wav", mime_type: "audio/x-wav", duration: 48 }],
  }),
  getJobStatusMock: vi.fn().mockResolvedValue({
    status: "complete",
    stage: "complete",
    progress_pct: 100,
    stage_history: ["queued", "complete"],
    message: "Completed",
  }),
  getResultMock: vi.fn().mockResolvedValue({
    song_id: 77,
    key: "Em",
    tempo: 120,
    duration: 42,
    chords: [],
  }),
  regenerateSongStemsMock: vi.fn().mockResolvedValue({
    stems: [{ stem_key: "bass", relative_path: "stems/30/bass.wav", mime_type: "audio/x-wav", duration: 48 }],
  }),
  regenerateSongTabsMock: vi.fn().mockResolvedValue({
    tab: {
      id: 1,
      source_stem_key: "bass",
      source_midi_id: 1,
      tab_format: "alphatex",
      tuning: "E1,A1,D2,G2",
      strings: 4,
      generator_version: "v2-rhythm-grid",
      status: "complete",
      error_message: null,
      created_at: "2026-03-10",
      updated_at: "2026-03-10",
    },
  }),
  getSongMock: vi.fn().mockResolvedValue({
    song: { id: 30, title: "The Trooper", original_filename: "demo.mp3", mime_type: "audio/mpeg", created_at: "2026-03-09" },
    analysis: { key: "Em", tempo: 160, duration: 48, chords: [] },
    notes: [],
    playback_prefs: { speed_percent: 100, volume: 1, loop_start_index: null, loop_end_index: null },
  }),
  getSongTabsMock: vi.fn().mockResolvedValue({
    tab: {
      id: 1,
      source_stem_key: "bass",
      source_midi_id: 1,
      source_type: "user",
      source_display_name: "Bass DI",
      tab_format: "alphatex",
      tuning: "E1,A1,D2,G2",
      strings: 4,
      generator_version: "v2-rhythm-grid",
      status: "complete",
      error_message: null,
      created_at: "2026-03-10",
      updated_at: "2026-03-10",
    },
  }),
  listSongStemsMock: vi.fn().mockResolvedValue({
    stems: [{ stem_key: "bass", relative_path: "stems/30/bass.wav", mime_type: "audio/x-wav", duration: 48 }],
  }),
  listBandsMock: vi.fn().mockResolvedValue({
    bands: [{ id: 10, name: "Default Band", owner_user_id: 1, created_at: "2026-03-09", project_count: 1 }],
  }),
  listBandMembersMock: vi.fn().mockResolvedValue({
    members: [{ id: "1", name: "Groove Bassline", role: "owner", avatar: "GB", presenceState: "not_live" }],
  }),
  listBandProjectsMock: vi.fn().mockResolvedValue({
    projects: [{ id: 20, band_id: 10, name: "Default Project", description: "", created_at: "2026-03-09", song_count: 1, unread_count: 0 }],
  }),
  getProjectActivityMock: vi.fn().mockResolvedValue({
    activity: [],
    unread_count: 0,
    presence_state: "not_live",
  }),
  listProjectSongsMock: vi.fn().mockResolvedValue({
    songs: [{ id: 30, project_id: 20, title: "The Trooper", original_filename: "demo.mp3", created_at: "2026-03-09", key: "Em", tempo: 160, duration: 48 }],
  }),
  createBandMock: vi.fn().mockResolvedValue({
    band: { id: 11, name: "My Band", owner_user_id: 1, created_at: "2026-03-10", project_count: 0 },
  }),
  createProjectMock: vi.fn().mockResolvedValue({
    project: { id: 21, band_id: 11, name: "Debut", description: "", created_at: "2026-03-10", song_count: 0 },
  }),
  createSongNoteMock: vi.fn().mockResolvedValue({ id: 301, type: "time", text: "Created", timestamp_sec: 78, chord_index: null, toast_duration_sec: null, resolved: false, author_name: "Wojtek", author_avatar: "WG", created_at: "2026-03-10T10:00:00Z", updated_at: "2026-03-10T10:00:00Z" }),
  updateSongNoteMock: vi.fn().mockResolvedValue({ id: 301, text: "Edited", toast_duration_sec: null }),
  resolveSongNoteMock: vi.fn().mockResolvedValue({ id: 301, resolved: true }),
  deleteSongNoteMock: vi.fn().mockResolvedValue(undefined),
  playerPagePropsSpy: vi.fn(),
}));

vi.mock("../redesign/pages/PlayerPage", () => ({
  PlayerPage: ({
    song,
    onCreateNote,
    onEditNote,
    onResolveNote,
    onDeleteNote,
  }: {
    song: {
      id: string;
      stems: Array<unknown>;
      chords: Array<unknown>;
      tab?: { sourceStemKey?: string | null } | null;
      notes?: Array<{ id: number; text: string; resolved: boolean }>;
    };
    onCreateNote?: (payload: { type: "time" | "chord"; text: string; timestampSec?: number; chordIndex?: number; toastDurationSec?: number }) => Promise<void> | void;
    onEditNote?: (noteId: number, payload: { text: string; toastDurationSec?: number }) => Promise<void> | void;
    onResolveNote?: (noteId: number, resolved: boolean) => Promise<void> | void;
    onDeleteNote?: (noteId: number) => Promise<void> | void;
  }) => {
    playerPagePropsSpy(song);
    const openNotes = song.notes?.filter((note) => !note.resolved) ?? [];
    const resolvedNotes = song.notes?.filter((note) => note.resolved) ?? [];
    return (
      <div>
        <div
          data-testid="player-page"
          data-song-id={song.id}
          data-stem-count={String(song.stems.length)}
          data-chord-count={String(song.chords.length)}
          data-tab-source-stem-key={song.tab?.sourceStemKey ?? ""}
        />
        <span>Player open notes: {openNotes.length}</span>
        <span>Player resolved notes: {resolvedNotes.length}</span>
        {song.notes?.map((note) => <span key={note.id}>{note.text}</span>)}
        <button type="button" onClick={() => void onCreateNote?.({ type: "time", text: "Player time note", timestampSec: 18.5 })}>
          Mock player create note
        </button>
        <button type="button" onClick={() => void onEditNote?.(11, { text: "Player note edited" })}>
          Mock player edit note
        </button>
        <button type="button" onClick={() => void onCreateNote?.({ type: "time", text: "Player timed toast note", timestampSec: 21, toastDurationSec: 5 })}>
          Mock player create toast note
        </button>
        <button type="button" onClick={() => void onEditNote?.(11, { text: "Player note with toast", toastDurationSec: 7 })}>
          Mock player edit toast note
        </button>
        <button type="button" onClick={() => void onResolveNote?.(11, true)}>
          Mock player resolve note
        </button>
        <button type="button" onClick={() => void onDeleteNote?.(11)}>
          Mock player delete note
        </button>
      </div>
    );
  },
}));

vi.mock("../lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../lib/api")>();
  return {
    ...actual,
    resolveIdentity: vi.fn().mockResolvedValue({
      user: {
        id: 1,
        display_name: "Groove Bassline",
        fingerprint_token: "fp-1",
        username: null,
        is_claimed: false,
      },
    }),
    listBands: listBandsMock,
    listBandMembers: listBandMembersMock,
    listBandProjects: listBandProjectsMock,
    getProjectActivity: getProjectActivityMock,
    listProjectSongs: listProjectSongsMock,
    getJobStatus: getJobStatusMock,
    getResult: getResultMock,
    getSong: getSongMock,
    getSongTabs: getSongTabsMock,
    listSongStems: listSongStemsMock,
    claimIdentity: claimIdentityMock,
    uploadAudio: uploadAudioMock,
    uploadSongStem: uploadSongStemMock,
    regenerateSongStems: regenerateSongStemsMock,
    regenerateSongTabs: regenerateSongTabsMock,
    createBand: createBandMock,
    createProject: createProjectMock,
    createSongNote: createSongNoteMock,
    updateSongNote: updateSongNoteMock,
    resolveSongNote: resolveSongNoteMock,
    deleteSongNote: deleteSongNoteMock,
  };
});

describe("App integration", () => {
  beforeEach(() => {
    claimIdentityMock.mockReset();
    uploadAudioMock.mockReset();
    uploadSongStemMock.mockReset();
    getJobStatusMock.mockReset();
    getResultMock.mockReset();
    regenerateSongStemsMock.mockReset();
    regenerateSongTabsMock.mockReset();
    getSongMock.mockReset();
    getSongTabsMock.mockReset();
    listSongStemsMock.mockReset();
    listBandsMock.mockReset();
    listBandMembersMock.mockReset();
    listBandProjectsMock.mockReset();
    getProjectActivityMock.mockReset();
    listProjectSongsMock.mockReset();
    createBandMock.mockReset();
    createProjectMock.mockReset();
    createSongNoteMock.mockReset();
    updateSongNoteMock.mockReset();
    resolveSongNoteMock.mockReset();
    deleteSongNoteMock.mockReset();
    playerPagePropsSpy.mockReset();
    vi.useRealTimers();
    claimIdentityMock.mockResolvedValue({
      user: {
        id: 1,
        display_name: "Groove Bassline",
        fingerprint_token: "fp-1",
        username: "bassbot",
        is_claimed: true,
      },
    });
    uploadAudioMock.mockResolvedValue({
      job_id: "job-77",
      song_id: 77,
    });
    uploadSongStemMock.mockResolvedValue({
      stems: [{ stem_key: "bass", relative_path: "stems/30/bass-di.wav", mime_type: "audio/x-wav", duration: 48 }],
    });
    listBandsMock.mockResolvedValue({
      bands: [{ id: 10, name: "Default Band", owner_user_id: 1, created_at: "2026-03-09", project_count: 1 }],
    });
    listBandMembersMock.mockResolvedValue({
      members: [{ id: "1", name: "Groove Bassline", role: "owner", avatar: "GB", presenceState: "not_live" }],
    });
    listBandProjectsMock.mockResolvedValue({
      projects: [{ id: 20, band_id: 10, name: "Default Project", description: "", created_at: "2026-03-09", song_count: 1, unread_count: 0 }],
    });
    getProjectActivityMock.mockResolvedValue({
      activity: [],
      unread_count: 0,
      presence_state: "not_live",
    });
    listProjectSongsMock.mockResolvedValue({
      songs: [{ id: 30, project_id: 20, title: "The Trooper", original_filename: "demo.mp3", created_at: "2026-03-09", key: "Em", tempo: 160, duration: 48 }],
    });
    getSongMock.mockResolvedValue({
      song: { id: 30, title: "The Trooper", original_filename: "demo.mp3", mime_type: "audio/mpeg", created_at: "2026-03-09" },
      analysis: { key: "Em", tempo: 160, duration: 48, chords: [] },
      notes: [],
      playback_prefs: { speed_percent: 100, volume: 1, loop_start_index: null, loop_end_index: null },
    });
    getSongTabsMock.mockResolvedValue({
      tab: {
        id: 1,
        source_stem_key: "bass",
        source_midi_id: 1,
        source_type: "user",
        source_display_name: "Bass DI",
        tab_format: "alphatex",
        tuning: "E1,A1,D2,G2",
        strings: 4,
        generator_version: "v2-rhythm-grid",
        status: "complete",
        error_message: null,
        created_at: "2026-03-10",
        updated_at: "2026-03-10",
      },
    });
    listSongStemsMock.mockResolvedValue({
      stems: [{ stem_key: "bass", relative_path: "stems/30/bass.wav", mime_type: "audio/x-wav", duration: 48 }],
    });
    getJobStatusMock.mockResolvedValue({
      status: "complete",
      stage: "complete",
      progress_pct: 100,
      stage_history: ["queued", "complete"],
      message: "Completed",
    });
    getResultMock.mockResolvedValue({
      song_id: 77,
      key: "Em",
      tempo: 120,
      duration: 42,
      chords: [],
    });
    regenerateSongStemsMock.mockResolvedValue({
      stems: [{ stem_key: "bass", relative_path: "stems/30/bass.wav", mime_type: "audio/x-wav", duration: 48 }],
    });
    regenerateSongTabsMock.mockResolvedValue({
      tab: {
        id: 1,
        source_stem_key: "bass",
        source_midi_id: 1,
        tab_format: "alphatex",
        tuning: "E1,A1,D2,G2",
        strings: 4,
        generator_version: "v2-rhythm-grid",
        status: "complete",
        error_message: null,
        created_at: "2026-03-10",
        updated_at: "2026-03-10",
      },
    });
    createBandMock.mockResolvedValue({
      band: { id: 11, name: "My Band", owner_user_id: 1, created_at: "2026-03-10", project_count: 0 },
    });
    createProjectMock.mockResolvedValue({
      project: { id: 21, band_id: 11, name: "Debut", description: "", created_at: "2026-03-10", song_count: 0 },
    });
    createSongNoteMock.mockResolvedValue({ id: 301, type: "time", text: "Created", timestamp_sec: 78, chord_index: null, toast_duration_sec: null, resolved: false, author_name: "Wojtek", author_avatar: "WG", created_at: "2026-03-10T10:00:00Z", updated_at: "2026-03-10T10:00:00Z" });
    updateSongNoteMock.mockResolvedValue({ id: 301, text: "Edited", toast_duration_sec: null });
    resolveSongNoteMock.mockResolvedValue({ id: 301, resolved: true });
    deleteSongNoteMock.mockResolvedValue(undefined);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders opus landing shell", () => {
    const html = renderToStaticMarkup(<App />);
    expect(html).toContain("Get Started Free");
    expect(html).toContain("DeChord");
  });

  it("navigates from landing to bands", async () => {
    render(<App />);

    fireEvent.click(screen.getByText("Get Started Free"));

    await waitFor(() => {
      expect(screen.getByText("Your Bands")).toBeTruthy();
      expect(screen.getByText("Default Band")).toBeTruthy();
    });
  });

  it("hydrates real members, unread counts, and project activity for project home", async () => {
    listBandsMock.mockResolvedValueOnce({
      bands: [{ id: 3, name: "Demo Band", owner_user_id: 1, created_at: "2026-03-10", project_count: 1 }],
    });
    listBandMembersMock.mockResolvedValueOnce({
      members: [
        { id: "1", name: "Wojtek", role: "owner", avatar: "W", presenceState: "not_live" },
        { id: "2", name: "Alicja", role: "member", avatar: "A", presenceState: "not_live" },
      ],
    });
    listBandProjectsMock.mockResolvedValueOnce({
      projects: [{ id: 9, band_id: 3, name: "Collab", description: "", created_at: "2026-03-10", song_count: 1, unread_count: 2 }],
    });
    listProjectSongsMock.mockResolvedValueOnce({
      songs: [{ id: 30, project_id: 9, title: "Demo", original_filename: "demo.mp3", created_at: "2026-03-10", key: "Em", tempo: 120, duration: 20 }],
    });
    getProjectActivityMock.mockResolvedValueOnce({
      activity: [{ id: 1, event_type: "note_created", message: "left a note", author_name: "Alicja", author_avatar: "A", timestamp: "2026-03-10T10:00:00Z", song_title: "Demo", song_id: 30 }],
      unread_count: 2,
      presence_state: "not_live",
    });

    render(<App />);

    fireEvent.click(screen.getByText("Get Started Free"));

    await waitFor(() => {
      expect(screen.getByText("Demo Band")).toBeTruthy();
    });

    fireEvent.click(screen.getByText("Demo Band"));

    await waitFor(() => {
      expect(screen.getAllByText("Alicja").length).toBeGreaterThan(0);
      expect(screen.getAllByText("2").length).toBeGreaterThan(0);
      expect(screen.getByText(/left a note/i)).toBeTruthy();
      expect(screen.getByText(/in Demo/i)).toBeTruthy();
    });
  });

  it("shows honest empty state instead of mock bands when backend is empty", async () => {
    listBandsMock.mockResolvedValueOnce({ bands: [] });

    render(<App />);
    fireEvent.click(screen.getByText("Get Started Free"));

    await waitFor(() => {
      expect(screen.getByText("Create Your First Band")).toBeTruthy();
    });
    expect(screen.queryByText("The Rust Belt")).toBeNull();
    expect(screen.queryByText("The Trooper")).toBeNull();
  });

  it("creates a band from the inline empty-state panel", async () => {
    listBandsMock.mockResolvedValueOnce({ bands: [] }).mockResolvedValueOnce({
      bands: [{ id: 11, name: "My Band", owner_user_id: 1, created_at: "2026-03-10", project_count: 0 }],
    });
    listBandProjectsMock.mockResolvedValueOnce({ projects: [] });

    render(<App />);
    fireEvent.click(screen.getByText("Get Started Free"));

    await waitFor(() => {
      expect(screen.getByText("Create Your First Band")).toBeTruthy();
    });

    fireEvent.click(screen.getByText("Create Band"));
    fireEvent.change(screen.getByLabelText("Band Name"), { target: { value: "My Band" } });
    fireEvent.click(screen.getByText("Save Band"));

    await waitFor(() => {
      expect(createBandMock).toHaveBeenCalledWith({ name: "My Band" });
    });
  });

  it("creates a project from the inline empty-project panel", async () => {
    listBandsMock.mockResolvedValueOnce({
      bands: [{ id: 11, name: "My Band", owner_user_id: 1, created_at: "2026-03-10", project_count: 0 }],
    });
    listBandProjectsMock.mockResolvedValueOnce({ projects: [] }).mockResolvedValueOnce({
      projects: [{ id: 21, band_id: 11, name: "Debut", description: "", created_at: "2026-03-10", song_count: 0, unread_count: 0 }],
    });
    listProjectSongsMock.mockResolvedValueOnce({ songs: [] });

    render(<App />);
    fireEvent.click(screen.getByText("Get Started Free"));

    await waitFor(() => {
      expect(screen.getByText("My Band")).toBeTruthy();
    });

    fireEvent.click(screen.getByText("My Band"));

    await waitFor(() => {
      expect(screen.getByText("Create Your First Project")).toBeTruthy();
    });

    fireEvent.click(screen.getByText("Create Project"));
    fireEvent.change(screen.getByLabelText("Project Name"), { target: { value: "Debut" } });
    fireEvent.click(screen.getByText("Save Project"));

    await waitFor(() => {
      expect(createProjectMock).toHaveBeenCalledWith(11, { name: "Debut", description: "" });
    });
  });

  it("uploads a song into the selected project", async () => {
    listProjectSongsMock.mockResolvedValueOnce({ songs: [] }).mockResolvedValueOnce({
      songs: [{ id: 77, project_id: 20, title: "New Song", original_filename: "new-song.mp3", created_at: "2026-03-10", key: null, tempo: null, duration: null }],
    });

    render(<App />);

    fireEvent.click(screen.getByText("Get Started Free"));
    await waitFor(() => {
      expect(screen.getByText("Default Band")).toBeTruthy();
    });

    fireEvent.click(screen.getByText("Default Band"));
    await waitFor(() => {
      expect(screen.getByText("Song Library →")).toBeTruthy();
    });

    fireEvent.click(screen.getByText("Song Library →"));
    await waitFor(() => {
      expect(screen.getByText("+ Upload Song")).toBeTruthy();
    });

    fireEvent.click(screen.getByText("+ Upload Song"));
    const file = new File(["bass"], "new-song.mp3", { type: "audio/mpeg" });
    fireEvent.change(screen.getByLabelText("Song File"), { target: { files: [file] } });
    fireEvent.click(screen.getByText("Start Upload"));

    await waitFor(() => {
      expect(uploadAudioMock).toHaveBeenCalledWith(file, "analysis_and_stems", "standard", 20);
    });
  });

  it("navigates from upload to processing journey to song detail", async () => {
    vi.useFakeTimers();
    listProjectSongsMock.mockResolvedValueOnce({ songs: [] }).mockResolvedValue({
      songs: [{ id: 77, project_id: 20, title: "New Song", original_filename: "new-song.mp3", created_at: "2026-03-10", key: "Em", tempo: 120, duration: 42 }],
    });
    getSongMock.mockResolvedValueOnce({
      song: { id: 77, title: "New Song", original_filename: "new-song.mp3", mime_type: "audio/mpeg", created_at: "2026-03-10" },
      analysis: { key: "Em", tempo: 120, duration: 42, chords: [] },
      notes: [{ id: 91, type: "time", timestamp_sec: 12.5, chord_index: null, text: "Bring the bass forward" }],
      playback_prefs: { speed_percent: 100, volume: 1, loop_start_index: null, loop_end_index: null },
    });
    getSongTabsMock.mockResolvedValueOnce({
      tab: {
        id: 4,
        source_stem_key: "bass",
        source_midi_id: 8,
        source_type: "user",
        source_display_name: "Uploaded Bass Stem",
        tab_format: "alphatex",
        tuning: "E1,A1,D2,G2",
        strings: 4,
        generator_version: "v2-rhythm-grid",
        status: "complete",
        error_message: null,
        created_at: "2026-03-10",
        updated_at: "2026-03-10",
      },
    });
    listSongStemsMock.mockResolvedValueOnce({
      stems: [{ stem_key: "bass", relative_path: "stems/77/bass.wav", mime_type: "audio/x-wav", duration: 42 }],
    });
    getJobStatusMock
      .mockResolvedValueOnce({ status: "queued", stage: "queued", progress_pct: 0, stage_history: ["queued"], message: "Queued" })
      .mockResolvedValueOnce({ status: "processing", stage: "splitting_stems", progress_pct: 45, stage_history: ["queued", "splitting_stems"], message: "Splitting stems..." })
      .mockResolvedValueOnce({ status: "processing", progress_pct: 55 })
      .mockResolvedValueOnce({ status: "complete", stage: "complete", progress_pct: 100, stage_history: ["queued", "splitting_stems", "complete"], message: "Completed" });
    getResultMock.mockResolvedValueOnce({ song_id: 77, key: "Em", tempo: 120, duration: 42, chords: [] });

    render(<App />);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });

    fireEvent.click(screen.getByText("Get Started Free"));
    expect(screen.getByText("Default Band")).toBeTruthy();

    fireEvent.click(screen.getByText("Default Band"));
    expect(screen.getByText("Song Library →")).toBeTruthy();

    fireEvent.click(screen.getByText("Song Library →"));
    expect(screen.getByText("+ Upload Song")).toBeTruthy();

    fireEvent.click(screen.getByText("+ Upload Song"));
    const file = new File(["bass"], "new-song.mp3", { type: "audio/mpeg" });
    fireEvent.change(screen.getByLabelText("Song File"), { target: { files: [file] } });
    fireEvent.change(screen.getByLabelText("Process Mode"), { target: { value: "analysis_only" } });
    fireEvent.change(screen.getByLabelText("Tab Quality"), { target: { value: "high_accuracy" } });
    await act(async () => {
      fireEvent.click(screen.getByText("Start Upload"));
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(() => {
      expect(uploadAudioMock).toHaveBeenCalledWith(file, "analysis_only", "high_accuracy", 20);
    }).not.toThrow();

    expect(screen.queryByText("Processing Journey")).toBeTruthy();
    expect(screen.queryByText("Queued")).toBeTruthy();
    expect(screen.queryAllByText("new-song.mp3").length).toBeGreaterThan(0);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1000);
    });

    expect(screen.queryByText("Splitting stems...")).toBeTruthy();
    expect(screen.queryAllByText("splitting_stems").length).toBeGreaterThan(0);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1000);
    });

    expect(screen.queryByText("Splitting stems...")).toBeTruthy();
    expect(screen.queryAllByText("splitting_stems").length).toBeGreaterThan(0);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1000);
    });

    expect(getResultMock).toHaveBeenCalledWith("job-77");
    expect(screen.getByText("Generate Stems")).toBeTruthy();
    expect(screen.getByText("New Song")).toBeTruthy();
    expect(screen.getByText("Generated from Uploaded Bass Stem.")).toBeTruthy();
    expect(screen.getByText("Bring the bass forward")).toBeTruthy();
    expect(getSongTabsMock).toHaveBeenCalledWith(77);
  });

  it("stops polling and stays in the library after leaving processing journey", async () => {
    vi.useFakeTimers();
    listProjectSongsMock.mockResolvedValueOnce({ songs: [] }).mockResolvedValue({ songs: [] });
    let resolveStatus: ((value: { status: "complete"; stage: "complete"; progress_pct: 100; stage_history: ["queued", "complete"]; message: "Completed" }) => void) | null = null;
    getJobStatusMock.mockReturnValueOnce(
      new Promise((resolve) => {
        resolveStatus = resolve;
      }),
    );

    render(<App />);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });

    fireEvent.click(screen.getByText("Get Started Free"));
    expect(screen.getByText("Default Band")).toBeTruthy();

    fireEvent.click(screen.getByText("Default Band"));
    expect(screen.getByText("Song Library →")).toBeTruthy();

    fireEvent.click(screen.getByText("Song Library →"));
    expect(screen.getByText("+ Upload Song")).toBeTruthy();

    fireEvent.click(screen.getByText("+ Upload Song"));
    const file = new File(["bass"], "new-song.mp3", { type: "audio/mpeg" });
    fireEvent.change(screen.getByLabelText("Song File"), { target: { files: [file] } });
    await act(async () => {
      fireEvent.click(screen.getByText("Start Upload"));
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(screen.getByText("Processing Journey")).toBeTruthy();
    expect(screen.getByText("Queued")).toBeTruthy();

    fireEvent.click(screen.getByText("Back to Library"));
    expect(screen.getByText("Song Library")).toBeTruthy();

    await act(async () => {
      resolveStatus?.({ status: "complete", stage: "complete", progress_pct: 100, stage_history: ["queued", "complete"], message: "Completed" });
      await Promise.resolve();
      await vi.advanceTimersByTimeAsync(5000);
    });

    expect(screen.getByText("Song Library")).toBeTruthy();
    expect(screen.queryByText("Generate Stems")).toBeNull();
    expect(getResultMock).not.toHaveBeenCalled();
    expect(getJobStatusMock).toHaveBeenCalledTimes(1);
  });

  it("triggers claim account flow from bands page", async () => {
    const promptSpy = vi.spyOn(window, "prompt");
    promptSpy.mockReturnValueOnce("bassbot").mockReturnValueOnce("secret-pass");
    render(<App />);

    fireEvent.click(screen.getByText("Get Started Free"));
    await waitFor(() => {
      expect(screen.getByText("Your Bands")).toBeTruthy();
    });

    fireEvent.click(screen.getByText("Claim Account"));
    await waitFor(() => {
      expect(claimIdentityMock).toHaveBeenCalledWith({
        user_id: 1,
        username: "bassbot",
        password: "secret-pass",
      });
    });
    promptSpy.mockRestore();
  });

  it("falls back to single-track playback when no stems", () => {
    const resolved = resolvePlaybackSources({
      songId: 5,
      playbackMode: "stems",
      stems: [],
      enabledByStem: {},
    });

    expect(resolved.usingStems).toBe(false);
    expect(resolved.audioSrc).toBe("/api/audio/5");
    expect(resolved.stemSources).toHaveLength(0);
  });

  it("uses stems playback when stems exist", () => {
    const resolved = resolvePlaybackSources({
      songId: 5,
      playbackMode: "stems",
      stems: [
        { stem_key: "drums", relative_path: "stems/5/drums.wav", mime_type: "audio/x-wav", duration: null },
      ],
      enabledByStem: { drums: true },
    });

    expect(resolved.usingStems).toBe(true);
    expect(resolved.stemSources).toHaveLength(1);
    expect(resolved.stemSources[0].url).toBe("/api/audio/5/stems/drums");
    expect(resolved.audioSrc).toBe("/api/audio/5");
  });

  it("regenerates stems from song detail and refreshes the song route", async () => {
    render(<App />);

    fireEvent.click(screen.getByText("Get Started Free"));
    await waitFor(() => {
      expect(screen.getByText("Your Bands")).toBeTruthy();
    });

    fireEvent.click(screen.getByText("Default Band"));
    await waitFor(() => {
      expect(screen.getByText("Song Library →")).toBeTruthy();
    });

    fireEvent.click(screen.getByText("Song Library →"));
    await waitFor(() => {
      expect(screen.getByText("The Trooper")).toBeTruthy();
    });

    fireEvent.click(screen.getByText("The Trooper"));
    await waitFor(() => {
      expect(screen.getByText("Generate Stems")).toBeTruthy();
    });

    fireEvent.click(screen.getByText("Generate Stems"));
    fireEvent.click(screen.getByText("Confirm Stem Generation"));

    await waitFor(() => {
      expect(regenerateSongStemsMock).toHaveBeenCalledWith(30);
    });
    await waitFor(() => {
      expect(getSongMock.mock.calls.length).toBeGreaterThan(1);
      expect(listSongStemsMock.mock.calls.length).toBeGreaterThan(1);
    });
  });

  it("hydrates uploaded stem provenance from song-detail refresh without changing tab provenance until tab regeneration", async () => {
    getSongTabsMock
      .mockResolvedValueOnce({
        tab: {
          id: 1,
          source_stem_key: "bass",
          source_midi_id: 1,
          source_type: "system",
          source_display_name: "Bass Stem",
          tab_format: "alphatex",
          tuning: "E1,A1,D2,G2",
          strings: 4,
          generator_version: "v2-rhythm-grid",
          status: "complete",
          error_message: null,
          created_at: "2026-03-10",
          updated_at: "2026-03-10",
        },
      })
      .mockResolvedValueOnce({
        tab: {
          id: 2,
          source_stem_key: "bass",
          source_midi_id: 2,
          source_type: "system",
          source_display_name: "Bass Stem",
          tab_format: "alphatex",
          tuning: "E1,A1,D2,G2",
          strings: 4,
          generator_version: "v2-rhythm-grid",
          status: "complete",
          error_message: null,
          created_at: "2026-03-10",
          updated_at: "2026-03-11",
        },
      })
      .mockResolvedValueOnce({
        tab: {
          id: 3,
          source_stem_key: "bass",
          source_midi_id: 3,
          source_type: "system",
          source_display_name: "Regenerated Bass Stem",
          tab_format: "alphatex",
          tuning: "E1,A1,D2,G2",
          strings: 4,
          generator_version: "v2-rhythm-grid",
          status: "complete",
          error_message: null,
          created_at: "2026-03-10",
          updated_at: "2026-03-12",
        },
      });

    listSongStemsMock
      .mockResolvedValueOnce({
        stems: [{ stem_key: "bass", relative_path: "stems/30/bass.wav", mime_type: "audio/x-wav", duration: 48 }],
      })
      .mockResolvedValueOnce({
        stems: [{
          id: 22,
          stem_key: "bass",
          source_type: "user",
          display_name: "Bass DI",
          version_label: "manual-2",
          uploaded_by_name: "Groove Bassline",
          is_archived: false,
          relative_path: "stems/30/bass-di.wav",
          mime_type: "audio/x-wav",
          duration: 48,
          created_at: "2026-03-11T10:00:00Z",
        }],
      })
      .mockResolvedValueOnce({
        stems: [{ stem_key: "bass", relative_path: "stems/30/bass-regenerated.wav", mime_type: "audio/x-wav", duration: 48 }],
      });

    render(<App />);

    fireEvent.click(screen.getByText("Get Started Free"));
    await waitFor(() => {
      expect(screen.getByText("Your Bands")).toBeTruthy();
    });

    fireEvent.click(screen.getByText("Default Band"));
    await waitFor(() => {
      expect(screen.getByText("Song Library →")).toBeTruthy();
    });

    fireEvent.click(screen.getByText("Song Library →"));
    await waitFor(() => {
      expect(screen.getByText("The Trooper")).toBeTruthy();
    });

    fireEvent.click(screen.getByText("The Trooper"));
    await waitFor(() => {
      expect(screen.getByText("Generated from Bass Stem.")).toBeTruthy();
    });

    fireEvent.click(screen.getByText("Upload Stem"));
    const file = new File(["bass"], "bass-di.wav", { type: "audio/wav" });
    fireEvent.change(screen.getByLabelText("Stem File"), { target: { files: [file] } });
    fireEvent.click(screen.getByText("Confirm Stem Upload"));

    await waitFor(() => {
      expect(uploadSongStemMock).toHaveBeenCalledWith(30, { stemKey: "bass", file });
    });
    await waitFor(() => {
      expect(screen.getByText("Bass DI")).toBeTruthy();
      expect(screen.getByText("User")).toBeTruthy();
      expect(screen.getByText("stems/30/bass-di.wav - by Groove Bassline")).toBeTruthy();
      expect(screen.getByText("Generated from Bass Stem.")).toBeTruthy();
      expect(screen.getByText("Provenance: System")).toBeTruthy();
    });

    fireEvent.click(screen.getByText("Generate Bass Tab"));
    fireEvent.click(screen.getByText("Confirm Tab Generation"));

    await waitFor(() => {
      expect(regenerateSongTabsMock).toHaveBeenCalledWith(30, { source_stem_key: "bass" });
    });
    await waitFor(() => {
      expect(screen.getByText("Generated from Regenerated Bass Stem.")).toBeTruthy();
    });

    expect(screen.getByText("The Trooper")).toBeTruthy();
    expect(getSongTabsMock).toHaveBeenCalledTimes(3);
  });

  it("preserves resolved note truth and note metadata when song details hydrate", async () => {
    listBandsMock.mockResolvedValueOnce({
      bands: [{ id: 10, name: "Demo Band", owner_user_id: 1, created_at: "2026-03-09", project_count: 1 }],
    });
    listBandProjectsMock.mockResolvedValueOnce({
      projects: [{ id: 20, band_id: 10, name: "Demo Project", description: "", created_at: "2026-03-09", song_count: 1, unread_count: 0 }],
    });
    listProjectSongsMock.mockResolvedValueOnce({
      songs: [{ id: 30, project_id: 20, title: "Demo Song", original_filename: "demo.mp3", created_at: "2026-03-09", key: "C", tempo: 120, duration: 10 }],
    });
    getSongMock.mockResolvedValue({
      song: { id: 30, title: "Demo Song", original_filename: "demo.mp3", mime_type: "audio/mpeg", created_at: "2026-03-10T00:00:00Z" },
      analysis: { key: "C", tempo: 120, duration: 10, chords: [{ start: 0, end: 2, label: "C" }] },
      notes: [{
        id: 91,
        type: "time",
        timestamp_sec: 4.2,
        chord_index: null,
        text: "Drop the fill",
        toast_duration_sec: 6,
        resolved: true,
        author_name: "Wojtek",
        author_avatar: "WG",
        created_at: "2026-03-10T10:00:00Z",
        updated_at: "2026-03-10T10:05:00Z",
      }],
      playback_prefs: { speed_percent: 100, volume: 1, loop_start_index: null, loop_end_index: null },
    });

    render(<App />);

    fireEvent.click(screen.getByText("Get Started Free"));
    await waitFor(() => {
      expect(screen.getByText("Demo Band")).toBeTruthy();
    });

    fireEvent.click(screen.getByText("Demo Band"));
    await waitFor(() => {
      expect(screen.getByText("Song Library →")).toBeTruthy();
    });

    fireEvent.click(screen.getByText("Song Library →"));
    await waitFor(() => {
      expect(screen.getByText("Demo Song")).toBeTruthy();
    });

    fireEvent.click(screen.getByText("Demo Song"));

    await waitFor(() => {
      expect(screen.getByText(/show resolved/i)).toBeTruthy();
      expect(screen.getByText(/no open comments/i)).toBeTruthy();
    });

    fireEvent.click(screen.getByText(/show resolved/i));

    expect(screen.getByText("Wojtek")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: /open player/i }));

    await waitFor(() => {
      expect(playerPagePropsSpy).toHaveBeenLastCalledWith(
        expect.objectContaining({
          notes: [expect.objectContaining({ id: 91, toastDurationSec: 6 })],
        }),
      );
    });
  });

  it("hydrates the player route from song detail with the latest real song assets", async () => {
    getSongMock.mockResolvedValue({
      song: { id: 30, title: "The Trooper", original_filename: "demo.mp3", mime_type: "audio/mpeg", created_at: "2026-03-09" },
      analysis: {
        key: "Em",
        tempo: 160,
        duration: 48,
        chords: [{ start: 0, end: 4, label: "Em" }],
      },
      notes: [],
      playback_prefs: { speed_percent: 100, volume: 1, loop_start_index: null, loop_end_index: null },
    });
    listSongStemsMock
      .mockResolvedValueOnce({ stems: [] })
      .mockResolvedValueOnce({
        stems: [{ stem_key: "bass", relative_path: "stems/30/bass.wav", mime_type: "audio/x-wav", duration: 48 }],
      });
    getSongTabsMock
      .mockResolvedValueOnce({ tab: null })
      .mockResolvedValueOnce({
        tab: {
          id: 1,
          source_stem_key: "bass",
          source_midi_id: 1,
          source_type: "user",
          source_display_name: "Bass DI",
          tab_format: "alphatex",
          tuning: "E1,A1,D2,G2",
          strings: 4,
          generator_version: "v2-rhythm-grid",
          status: "complete",
          error_message: null,
          created_at: "2026-03-10",
          updated_at: "2026-03-10",
        },
      });

    render(<App />);

    fireEvent.click(screen.getByText("Get Started Free"));
    await waitFor(() => {
      expect(screen.getByText("Your Bands")).toBeTruthy();
    });

    fireEvent.click(screen.getByText("Default Band"));
    await waitFor(() => {
      expect(screen.getByText("Song Library →")).toBeTruthy();
    });

    fireEvent.click(screen.getByText("Song Library →"));
    await waitFor(() => {
      expect(screen.getByText("The Trooper")).toBeTruthy();
    });

    fireEvent.click(screen.getByText("The Trooper"));
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /open player/i })).toBeTruthy();
    });

    fireEvent.click(screen.getByRole("button", { name: /open player/i }));

    await waitFor(() => {
      expect(getSongMock).toHaveBeenCalledTimes(2);
      expect(playerPagePropsSpy).toHaveBeenLastCalledWith(
        expect.objectContaining({
          id: "30",
          chords: [{ start: 0, end: 4, label: "Em" }],
          stems: [expect.objectContaining({ stemKey: "bass" })],
          tab: expect.objectContaining({ sourceStemKey: "bass" }),
        }),
      );
    });

    expect(screen.getByTestId("player-page").getAttribute("data-tab-source-stem-key")).toBe("bass");
    expect(screen.getByTestId("player-page").getAttribute("data-stem-count")).toBe("1");
  });

  it("ignores stale player hydration if song detail is no longer the current route when it resolves", async () => {
    let resolveDeferredSong: ((value: Awaited<ReturnType<typeof getSongMock>>) => void) | null = null;
    const deferredSongDetail = new Promise<Awaited<ReturnType<typeof getSongMock>>>((resolve) => {
      resolveDeferredSong = resolve;
    });

    getSongMock
      .mockResolvedValueOnce({
        song: { id: 30, title: "The Trooper", original_filename: "demo.mp3", mime_type: "audio/mpeg", created_at: "2026-03-09" },
        analysis: {
          key: "Em",
          tempo: 160,
          duration: 48,
          chords: [{ start: 0, end: 4, label: "Em" }],
        },
        notes: [],
        playback_prefs: { speed_percent: 100, volume: 1, loop_start_index: null, loop_end_index: null },
      })
      .mockReturnValueOnce(deferredSongDetail);
    listSongStemsMock
      .mockResolvedValueOnce({ stems: [] })
      .mockResolvedValueOnce({
        stems: [{ stem_key: "bass", relative_path: "stems/30/bass.wav", mime_type: "audio/x-wav", duration: 48 }],
      });
    getSongTabsMock
      .mockResolvedValueOnce({ tab: null })
      .mockResolvedValueOnce({
        tab: {
          id: 1,
          source_stem_key: "bass",
          source_midi_id: 1,
          source_type: "user",
          source_display_name: "Bass DI",
          tab_format: "alphatex",
          tuning: "E1,A1,D2,G2",
          strings: 4,
          generator_version: "v2-rhythm-grid",
          status: "complete",
          error_message: null,
          created_at: "2026-03-10",
          updated_at: "2026-03-10",
        },
      });

    render(<App />);

    fireEvent.click(screen.getByText("Get Started Free"));
    await waitFor(() => {
      expect(screen.getByText("Your Bands")).toBeTruthy();
    });

    fireEvent.click(screen.getByText("Default Band"));
    await waitFor(() => {
      expect(screen.getByText("Song Library →")).toBeTruthy();
    });

    fireEvent.click(screen.getByText("Song Library →"));
    await waitFor(() => {
      expect(screen.getByText("The Trooper")).toBeTruthy();
    });

    fireEvent.click(screen.getByText("The Trooper"));
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /open player/i })).toBeTruthy();
    });

    fireEvent.click(screen.getByRole("button", { name: /open player/i }));
    fireEvent.click(screen.getByText(/song library/i));

    await waitFor(() => {
      expect(screen.getByText("Song Library")).toBeTruthy();
    });

    await act(async () => {
      resolveDeferredSong?.({
        song: { id: 30, title: "The Trooper", original_filename: "demo.mp3", mime_type: "audio/mpeg", created_at: "2026-03-09" },
        analysis: {
          key: "Em",
          tempo: 160,
          duration: 48,
          chords: [{ start: 0, end: 4, label: "Em" }],
        },
        notes: [],
        playback_prefs: { speed_percent: 100, volume: 1, loop_start_index: null, loop_end_index: null },
      });
      await Promise.resolve();
    });

    expect(screen.queryByTestId("player-page")).toBeNull();
    expect(screen.getByText("Song Library")).toBeTruthy();
  });

  it("calls the resolve-note api helper with the truthful backend route", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      json: async () => ({ id: 91, resolved: true }),
    } as Response);

    const actualApi = await vi.importActual<typeof import("../lib/api")>("../lib/api");
    actualApi.setApiIdentityUserId(null);

    await actualApi.resolveSongNote(91, true);

    expect(fetchSpy).toHaveBeenCalledWith(
      "/api/notes/91/resolve",
      expect.objectContaining({
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ resolved: true }),
      }),
    );
  });

  it("routes song-detail note mutations through App and refreshes the active song detail after each success", async () => {
    getSongMock
      .mockResolvedValueOnce({
        song: { id: 30, title: "The Trooper", original_filename: "demo.mp3", mime_type: "audio/mpeg", created_at: "2026-03-09" },
        analysis: { key: "Em", tempo: 160, duration: 48, chords: [{ start: 0, end: 2, label: "Em" }] },
        notes: [
          {
            id: 11,
            type: "chord",
            timestamp_sec: null,
            chord_index: 0,
            text: "Lock verse entry",
            toast_duration_sec: null,
            resolved: false,
            author_name: "Wojtek",
            author_avatar: "WG",
            created_at: "2026-03-10T10:00:00Z",
            updated_at: "2026-03-10T10:00:00Z",
          },
        ],
        playback_prefs: { speed_percent: 100, volume: 1, loop_start_index: null, loop_end_index: null },
      })
      .mockResolvedValueOnce({
        song: { id: 30, title: "The Trooper", original_filename: "demo.mp3", mime_type: "audio/mpeg", created_at: "2026-03-09" },
        analysis: { key: "Em", tempo: 160, duration: 48, chords: [{ start: 0, end: 2, label: "Em" }] },
        notes: [
          {
            id: 11,
            type: "chord",
            timestamp_sec: null,
            chord_index: 0,
            text: "Lock verse entry",
            toast_duration_sec: null,
            resolved: false,
            author_name: "Wojtek",
            author_avatar: "WG",
            created_at: "2026-03-10T10:00:00Z",
            updated_at: "2026-03-10T10:00:00Z",
          },
          {
            id: 301,
            type: "time",
            timestamp_sec: 78,
            chord_index: null,
            text: "Bass pickup is late",
            toast_duration_sec: null,
            resolved: false,
            author_name: "Wojtek",
            author_avatar: "WG",
            created_at: "2026-03-10T10:10:00Z",
            updated_at: "2026-03-10T10:10:00Z",
          },
        ],
        playback_prefs: { speed_percent: 100, volume: 1, loop_start_index: null, loop_end_index: null },
      })
      .mockResolvedValueOnce({
        song: { id: 30, title: "The Trooper", original_filename: "demo.mp3", mime_type: "audio/mpeg", created_at: "2026-03-09" },
        analysis: { key: "Em", tempo: 160, duration: 48, chords: [{ start: 0, end: 2, label: "Em" }] },
        notes: [
          {
            id: 11,
            type: "chord",
            timestamp_sec: null,
            chord_index: 0,
            text: "Verse entry is rushing",
            toast_duration_sec: null,
            resolved: false,
            author_name: "Wojtek",
            author_avatar: "WG",
            created_at: "2026-03-10T10:00:00Z",
            updated_at: "2026-03-10T10:20:00Z",
          },
          {
            id: 301,
            type: "time",
            timestamp_sec: 78,
            chord_index: null,
            text: "Bass pickup is late",
            toast_duration_sec: null,
            resolved: false,
            author_name: "Wojtek",
            author_avatar: "WG",
            created_at: "2026-03-10T10:10:00Z",
            updated_at: "2026-03-10T10:10:00Z",
          },
        ],
        playback_prefs: { speed_percent: 100, volume: 1, loop_start_index: null, loop_end_index: null },
      })
      .mockResolvedValueOnce({
        song: { id: 30, title: "The Trooper", original_filename: "demo.mp3", mime_type: "audio/mpeg", created_at: "2026-03-09" },
        analysis: { key: "Em", tempo: 160, duration: 48, chords: [{ start: 0, end: 2, label: "Em" }] },
        notes: [
          {
            id: 11,
            type: "chord",
            timestamp_sec: null,
            chord_index: 0,
            text: "Verse entry is rushing",
            toast_duration_sec: null,
            resolved: true,
            author_name: "Wojtek",
            author_avatar: "WG",
            created_at: "2026-03-10T10:00:00Z",
            updated_at: "2026-03-10T10:25:00Z",
          },
          {
            id: 301,
            type: "time",
            timestamp_sec: 78,
            chord_index: null,
            text: "Bass pickup is late",
            toast_duration_sec: null,
            resolved: false,
            author_name: "Wojtek",
            author_avatar: "WG",
            created_at: "2026-03-10T10:10:00Z",
            updated_at: "2026-03-10T10:10:00Z",
          },
        ],
        playback_prefs: { speed_percent: 100, volume: 1, loop_start_index: null, loop_end_index: null },
      })
      .mockResolvedValueOnce({
        song: { id: 30, title: "The Trooper", original_filename: "demo.mp3", mime_type: "audio/mpeg", created_at: "2026-03-09" },
        analysis: { key: "Em", tempo: 160, duration: 48, chords: [{ start: 0, end: 2, label: "Em" }] },
        notes: [
          {
            id: 301,
            type: "time",
            timestamp_sec: 78,
            chord_index: null,
            text: "Bass pickup is late",
            toast_duration_sec: null,
            resolved: false,
            author_name: "Wojtek",
            author_avatar: "WG",
            created_at: "2026-03-10T10:10:00Z",
            updated_at: "2026-03-10T10:10:00Z",
          },
        ],
        playback_prefs: { speed_percent: 100, volume: 1, loop_start_index: null, loop_end_index: null },
      });

    render(<App />);

    fireEvent.click(screen.getByText("Get Started Free"));
    await waitFor(() => {
      expect(screen.getByText("Your Bands")).toBeTruthy();
    });

    fireEvent.click(screen.getByText("Default Band"));
    await waitFor(() => {
      expect(screen.getByText("Song Library →")).toBeTruthy();
    });

    fireEvent.click(screen.getByText("Song Library →"));
    await waitFor(() => {
      expect(screen.getByText("The Trooper")).toBeTruthy();
    });

    fireEvent.click(screen.getByText("The Trooper"));
    await waitFor(() => {
      expect(screen.getByText("Lock verse entry")).toBeTruthy();
    });

    fireEvent.change(screen.getByLabelText(/note text/i), { target: { value: "Bass pickup is late" } });
    fireEvent.click(screen.getByLabelText(/time note/i));
    fireEvent.change(screen.getByLabelText(/timestamp/i), { target: { value: "01:18" } });
    fireEvent.click(screen.getByRole("button", { name: /add time note/i }));

    await waitFor(() => {
      expect(createSongNoteMock).toHaveBeenCalledWith(30, {
        type: "time",
        text: "Bass pickup is late",
        timestamp_sec: 78,
      });
    });
    await waitFor(() => {
      expect(screen.getByText("Bass pickup is late")).toBeTruthy();
    });

    fireEvent.click(screen.getByRole("button", { name: /edit note 11/i }));
    const editInput = screen.getByLabelText(/edit note text/i);
    fireEvent.change(editInput, { target: { value: "Verse entry is rushing" } });
    fireEvent.click(screen.getByRole("button", { name: /save note 11/i }));

    await waitFor(() => {
      expect(updateSongNoteMock).toHaveBeenCalledWith(11, { text: "Verse entry is rushing" });
    });
    await waitFor(() => {
      expect(screen.getByText("Verse entry is rushing")).toBeTruthy();
    });

    fireEvent.click(screen.getByRole("button", { name: /resolve note 11/i }));

    await waitFor(() => {
      expect(resolveSongNoteMock).toHaveBeenCalledWith(11, true);
    });
    await waitFor(() => {
      expect(screen.queryByText("Verse entry is rushing")).toBeNull();
      expect(screen.getByText(/show resolved/i)).toBeTruthy();
    });

    fireEvent.click(screen.getByText(/show resolved/i));
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /delete note 11/i })).toBeTruthy();
    });
    fireEvent.click(screen.getByRole("button", { name: /delete note 11/i }));

    await waitFor(() => {
      expect(deleteSongNoteMock).toHaveBeenCalledWith(11);
    });
    await waitFor(() => {
      expect(screen.queryByText("Verse entry is rushing")).toBeNull();
    });

    expect(getSongMock).toHaveBeenCalledTimes(5);
  });

  it("forwards toastDurationSec through player note mutations", async () => {
    getSongMock
      .mockResolvedValueOnce({
        song: { id: 30, title: "The Trooper", original_filename: "demo.mp3", mime_type: "audio/mpeg", created_at: "2026-03-09" },
        analysis: { key: "Em", tempo: 160, duration: 48, chords: [{ start: 0, end: 2, label: "Em" }] },
        notes: [
          {
            id: 11,
            type: "chord",
            timestamp_sec: null,
            chord_index: 0,
            text: "Lock verse entry",
            toast_duration_sec: null,
            resolved: false,
            author_name: "Wojtek",
            author_avatar: "WG",
            created_at: "2026-03-10T10:00:00Z",
            updated_at: "2026-03-10T10:00:00Z",
          },
        ],
        playback_prefs: { speed_percent: 100, volume: 1, loop_start_index: null, loop_end_index: null },
      })
      .mockResolvedValueOnce({
        song: { id: 30, title: "The Trooper", original_filename: "demo.mp3", mime_type: "audio/mpeg", created_at: "2026-03-09" },
        analysis: { key: "Em", tempo: 160, duration: 48, chords: [{ start: 0, end: 2, label: "Em" }] },
        notes: [
          {
            id: 11,
            type: "chord",
            timestamp_sec: null,
            chord_index: 0,
            text: "Player note with toast",
            toast_duration_sec: 7,
            resolved: false,
            author_name: "Wojtek",
            author_avatar: "WG",
            created_at: "2026-03-10T10:00:00Z",
            updated_at: "2026-03-10T10:00:00Z",
          },
          {
            id: 301,
            type: "time",
            timestamp_sec: 21,
            chord_index: null,
            text: "Player timed toast note",
            toast_duration_sec: 5,
            resolved: false,
            author_name: "Wojtek",
            author_avatar: "WG",
            created_at: "2026-03-10T10:10:00Z",
            updated_at: "2026-03-10T10:10:00Z",
          },
        ],
        playback_prefs: { speed_percent: 100, volume: 1, loop_start_index: null, loop_end_index: null },
      })
      .mockResolvedValueOnce({
        song: { id: 30, title: "The Trooper", original_filename: "demo.mp3", mime_type: "audio/mpeg", created_at: "2026-03-09" },
        analysis: { key: "Em", tempo: 160, duration: 48, chords: [{ start: 0, end: 2, label: "Em" }] },
        notes: [
          {
            id: 11,
            type: "chord",
            timestamp_sec: null,
            chord_index: 0,
            text: "Player note with toast",
            toast_duration_sec: 7,
            resolved: false,
            author_name: "Wojtek",
            author_avatar: "WG",
            created_at: "2026-03-10T10:00:00Z",
            updated_at: "2026-03-10T10:00:00Z",
          },
          {
            id: 301,
            type: "time",
            timestamp_sec: 21,
            chord_index: null,
            text: "Player timed toast note",
            toast_duration_sec: 5,
            resolved: false,
            author_name: "Wojtek",
            author_avatar: "WG",
            created_at: "2026-03-10T10:10:00Z",
            updated_at: "2026-03-10T10:10:00Z",
          },
        ],
        playback_prefs: { speed_percent: 100, volume: 1, loop_start_index: null, loop_end_index: null },
      });

    render(<App />);

    fireEvent.click(screen.getByText("Get Started Free"));
    await waitFor(() => {
      expect(screen.getByText("Your Bands")).toBeTruthy();
    });

    fireEvent.click(screen.getByText("Default Band"));
    await waitFor(() => {
      expect(screen.getByText("Song Library →")).toBeTruthy();
    });

    fireEvent.click(screen.getByText("Song Library →"));
    await waitFor(() => {
      expect(screen.getByText("The Trooper")).toBeTruthy();
    });

    fireEvent.click(screen.getByText("The Trooper"));
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /open player/i })).toBeTruthy();
    });

    fireEvent.click(screen.getByRole("button", { name: /open player/i }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /mock player create toast note/i })).toBeTruthy();
    });

    fireEvent.click(screen.getByRole("button", { name: /mock player create toast note/i }));
    fireEvent.click(screen.getByRole("button", { name: /mock player edit toast note/i }));

    await waitFor(() => {
      expect(createSongNoteMock).toHaveBeenCalledWith(30, {
        type: "time",
        text: "Player timed toast note",
        timestamp_sec: 21,
        toast_duration_sec: 5,
      });
    });
    await waitFor(() => {
      expect(updateSongNoteMock).toHaveBeenCalledWith(11, {
        text: "Player note with toast",
        toast_duration_sec: 7,
      });
    });
  });

  it("routes player note mutations through App and refreshes the active player route after each success", async () => {
    getSongMock
      .mockResolvedValueOnce({
        song: { id: 30, title: "The Trooper", original_filename: "demo.mp3", mime_type: "audio/mpeg", created_at: "2026-03-09" },
        analysis: { key: "Em", tempo: 160, duration: 48, chords: [{ start: 0, end: 2, label: "Em" }] },
        notes: [
          {
            id: 11,
            type: "chord",
            timestamp_sec: null,
            chord_index: 0,
            text: "Lock verse entry",
            toast_duration_sec: null,
            resolved: false,
            author_name: "Wojtek",
            author_avatar: "WG",
            created_at: "2026-03-10T10:00:00Z",
            updated_at: "2026-03-10T10:00:00Z",
          },
        ],
        playback_prefs: { speed_percent: 100, volume: 1, loop_start_index: null, loop_end_index: null },
      })
      .mockResolvedValueOnce({
        song: { id: 30, title: "The Trooper", original_filename: "demo.mp3", mime_type: "audio/mpeg", created_at: "2026-03-09" },
        analysis: { key: "Em", tempo: 160, duration: 48, chords: [{ start: 0, end: 2, label: "Em" }] },
        notes: [
          {
            id: 11,
            type: "chord",
            timestamp_sec: null,
            chord_index: 0,
            text: "Lock verse entry",
            toast_duration_sec: null,
            resolved: false,
            author_name: "Wojtek",
            author_avatar: "WG",
            created_at: "2026-03-10T10:00:00Z",
            updated_at: "2026-03-10T10:00:00Z",
          },
        ],
        playback_prefs: { speed_percent: 100, volume: 1, loop_start_index: null, loop_end_index: null },
      })
      .mockResolvedValueOnce({
        song: { id: 30, title: "The Trooper", original_filename: "demo.mp3", mime_type: "audio/mpeg", created_at: "2026-03-09" },
        analysis: { key: "Em", tempo: 160, duration: 48, chords: [{ start: 0, end: 2, label: "Em" }] },
        notes: [
          {
            id: 11,
            type: "chord",
            timestamp_sec: null,
            chord_index: 0,
            text: "Lock verse entry",
            toast_duration_sec: null,
            resolved: false,
            author_name: "Wojtek",
            author_avatar: "WG",
            created_at: "2026-03-10T10:00:00Z",
            updated_at: "2026-03-10T10:00:00Z",
          },
          {
            id: 301,
            type: "time",
            timestamp_sec: 18.5,
            chord_index: null,
            text: "Player time note",
            toast_duration_sec: null,
            resolved: false,
            author_name: "Wojtek",
            author_avatar: "WG",
            created_at: "2026-03-10T10:10:00Z",
            updated_at: "2026-03-10T10:10:00Z",
          },
        ],
        playback_prefs: { speed_percent: 100, volume: 1, loop_start_index: null, loop_end_index: null },
      })
      .mockResolvedValueOnce({
        song: { id: 30, title: "The Trooper", original_filename: "demo.mp3", mime_type: "audio/mpeg", created_at: "2026-03-09" },
        analysis: { key: "Em", tempo: 160, duration: 48, chords: [{ start: 0, end: 2, label: "Em" }] },
        notes: [
          {
            id: 11,
            type: "chord",
            timestamp_sec: null,
            chord_index: 0,
            text: "Player note edited",
            toast_duration_sec: null,
            resolved: false,
            author_name: "Wojtek",
            author_avatar: "WG",
            created_at: "2026-03-10T10:00:00Z",
            updated_at: "2026-03-10T10:20:00Z",
          },
          {
            id: 301,
            type: "time",
            timestamp_sec: 18.5,
            chord_index: null,
            text: "Player time note",
            toast_duration_sec: null,
            resolved: false,
            author_name: "Wojtek",
            author_avatar: "WG",
            created_at: "2026-03-10T10:10:00Z",
            updated_at: "2026-03-10T10:10:00Z",
          },
        ],
        playback_prefs: { speed_percent: 100, volume: 1, loop_start_index: null, loop_end_index: null },
      })
      .mockResolvedValueOnce({
        song: { id: 30, title: "The Trooper", original_filename: "demo.mp3", mime_type: "audio/mpeg", created_at: "2026-03-09" },
        analysis: { key: "Em", tempo: 160, duration: 48, chords: [{ start: 0, end: 2, label: "Em" }] },
        notes: [
          {
            id: 11,
            type: "chord",
            timestamp_sec: null,
            chord_index: 0,
            text: "Player note edited",
            toast_duration_sec: null,
            resolved: true,
            author_name: "Wojtek",
            author_avatar: "WG",
            created_at: "2026-03-10T10:00:00Z",
            updated_at: "2026-03-10T10:25:00Z",
          },
          {
            id: 301,
            type: "time",
            timestamp_sec: 18.5,
            chord_index: null,
            text: "Player time note",
            toast_duration_sec: null,
            resolved: false,
            author_name: "Wojtek",
            author_avatar: "WG",
            created_at: "2026-03-10T10:10:00Z",
            updated_at: "2026-03-10T10:10:00Z",
          },
        ],
        playback_prefs: { speed_percent: 100, volume: 1, loop_start_index: null, loop_end_index: null },
      })
      .mockResolvedValueOnce({
        song: { id: 30, title: "The Trooper", original_filename: "demo.mp3", mime_type: "audio/mpeg", created_at: "2026-03-09" },
        analysis: { key: "Em", tempo: 160, duration: 48, chords: [{ start: 0, end: 2, label: "Em" }] },
        notes: [
          {
            id: 301,
            type: "time",
            timestamp_sec: 18.5,
            chord_index: null,
            text: "Player time note",
            toast_duration_sec: null,
            resolved: false,
            author_name: "Wojtek",
            author_avatar: "WG",
            created_at: "2026-03-10T10:10:00Z",
            updated_at: "2026-03-10T10:10:00Z",
          },
        ],
        playback_prefs: { speed_percent: 100, volume: 1, loop_start_index: null, loop_end_index: null },
      });

    render(<App />);

    fireEvent.click(screen.getByText("Get Started Free"));
    await waitFor(() => {
      expect(screen.getByText("Your Bands")).toBeTruthy();
    });

    fireEvent.click(screen.getByText("Default Band"));
    await waitFor(() => {
      expect(screen.getByText("Song Library →")).toBeTruthy();
    });

    fireEvent.click(screen.getByText("Song Library →"));
    await waitFor(() => {
      expect(screen.getByText("The Trooper")).toBeTruthy();
    });

    fireEvent.click(screen.getByText("The Trooper"));
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /open player/i })).toBeTruthy();
    });

    fireEvent.click(screen.getByRole("button", { name: /open player/i }));

    await waitFor(() => {
      expect(screen.getByText("Player open notes: 1")).toBeTruthy();
      expect(screen.getByText("Player resolved notes: 0")).toBeTruthy();
      expect(screen.getByText("Lock verse entry")).toBeTruthy();
    });

    fireEvent.click(screen.getByRole("button", { name: /mock player create note/i }));

    await waitFor(() => {
      expect(createSongNoteMock).toHaveBeenCalledWith(30, {
        type: "time",
        text: "Player time note",
        timestamp_sec: 18.5,
        chord_index: undefined,
      });
    });
    await waitFor(() => {
      expect(screen.getByText("Player open notes: 2")).toBeTruthy();
      expect(screen.getByText("Player time note")).toBeTruthy();
    });

    fireEvent.click(screen.getByRole("button", { name: /mock player edit note/i }));

    await waitFor(() => {
      expect(updateSongNoteMock).toHaveBeenCalledWith(11, { text: "Player note edited" });
    });
    await waitFor(() => {
      expect(screen.getByText("Player note edited")).toBeTruthy();
    });

    fireEvent.click(screen.getByRole("button", { name: /mock player resolve note/i }));

    await waitFor(() => {
      expect(resolveSongNoteMock).toHaveBeenCalledWith(11, true);
    });
    await waitFor(() => {
      expect(screen.getByText("Player open notes: 1")).toBeTruthy();
      expect(screen.getByText("Player resolved notes: 1")).toBeTruthy();
    });

    fireEvent.click(screen.getByRole("button", { name: /mock player delete note/i }));

    await waitFor(() => {
      expect(deleteSongNoteMock).toHaveBeenCalledWith(11);
    });
    await waitFor(() => {
      expect(screen.getByText("Player open notes: 1")).toBeTruthy();
      expect(screen.getByText("Player resolved notes: 0")).toBeTruthy();
      expect(screen.queryByText("Player note edited")).toBeNull();
    });

    expect(getSongMock).toHaveBeenCalledTimes(6);
  });
});
