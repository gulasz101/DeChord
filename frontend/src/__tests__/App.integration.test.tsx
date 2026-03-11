import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "../App";
import { resolvePlaybackSources } from "../lib/playbackSources";

const {
  claimIdentityMock,
  uploadAudioMock,
  getJobStatusMock,
  getResultMock,
  regenerateSongStemsMock,
  regenerateSongTabsMock,
  getSongMock,
  listSongStemsMock,
  listBandsMock,
  listBandProjectsMock,
  listProjectSongsMock,
  createBandMock,
  createProjectMock,
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
  listSongStemsMock: vi.fn().mockResolvedValue({
    stems: [{ stem_key: "bass", relative_path: "stems/30/bass.wav", mime_type: "audio/x-wav", duration: 48 }],
  }),
  listBandsMock: vi.fn().mockResolvedValue({
    bands: [{ id: 10, name: "Default Band", owner_user_id: 1, created_at: "2026-03-09", project_count: 1 }],
  }),
  listBandProjectsMock: vi.fn().mockResolvedValue({
    projects: [{ id: 20, band_id: 10, name: "Default Project", description: "", created_at: "2026-03-09", song_count: 1 }],
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
    listBandProjects: listBandProjectsMock,
    listProjectSongs: listProjectSongsMock,
    getJobStatus: getJobStatusMock,
    getResult: getResultMock,
    getSong: getSongMock,
    listSongStems: listSongStemsMock,
    claimIdentity: claimIdentityMock,
    uploadAudio: uploadAudioMock,
    regenerateSongStems: regenerateSongStemsMock,
    regenerateSongTabs: regenerateSongTabsMock,
    createBand: createBandMock,
    createProject: createProjectMock,
  };
});

describe("App integration", () => {
  beforeEach(() => {
    claimIdentityMock.mockReset();
    uploadAudioMock.mockReset();
    getJobStatusMock.mockReset();
    getResultMock.mockReset();
    regenerateSongStemsMock.mockReset();
    regenerateSongTabsMock.mockReset();
    getSongMock.mockReset();
    listSongStemsMock.mockReset();
    listBandsMock.mockReset();
    listBandProjectsMock.mockReset();
    listProjectSongsMock.mockReset();
    createBandMock.mockReset();
    createProjectMock.mockReset();
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
    listBandsMock.mockResolvedValue({
      bands: [{ id: 10, name: "Default Band", owner_user_id: 1, created_at: "2026-03-09", project_count: 1 }],
    });
    listBandProjectsMock.mockResolvedValue({
      projects: [{ id: 20, band_id: 10, name: "Default Project", description: "", created_at: "2026-03-09", song_count: 1 }],
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
      projects: [{ id: 21, band_id: 11, name: "Debut", description: "", created_at: "2026-03-10", song_count: 0 }],
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
      notes: [],
      playback_prefs: { speed_percent: 100, volume: 1, loop_start_index: null, loop_end_index: null },
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
});
