import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "../App";
import { resolvePlaybackSources } from "../lib/playbackSources";

const { claimIdentityMock } = vi.hoisted(() => ({
  claimIdentityMock: vi.fn().mockResolvedValue({
    user: {
      id: 1,
      display_name: "Groove Bassline",
      fingerprint_token: "fp-1",
      username: "bassbot",
      is_claimed: true,
    },
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
    listBands: vi.fn().mockResolvedValue({
      bands: [{ id: 10, name: "Default Band", owner_user_id: 1, created_at: "2026-03-09", project_count: 1 }],
    }),
    listBandProjects: vi.fn().mockResolvedValue({
      projects: [{ id: 20, band_id: 10, name: "Default Project", description: "", created_at: "2026-03-09", song_count: 1 }],
    }),
    listProjectSongs: vi.fn().mockResolvedValue({
      songs: [{ id: 30, project_id: 20, title: "The Trooper", original_filename: "demo.mp3", created_at: "2026-03-09", key: "Em", tempo: 160, duration: 48 }],
    }),
    getSong: vi.fn().mockResolvedValue({
      song: { id: 30, title: "The Trooper", original_filename: "demo.mp3", mime_type: "audio/mpeg", created_at: "2026-03-09" },
      analysis: { key: "Em", tempo: 160, duration: 48, chords: [] },
      notes: [],
      playback_prefs: { speed_percent: 100, volume: 1, loop_start_index: null, loop_end_index: null },
    }),
    listSongStems: vi.fn().mockResolvedValue({ stems: [] }),
    claimIdentity: claimIdentityMock,
  };
});

describe("App integration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
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
});
