import { afterEach, describe, expect, it, vi } from "vitest";
import {
  createBand,
  createProject,
  createSongNote,
  deleteSongNote,
  regenerateSongStems,
  resolveSongNote,
  listBandMembers,
  listBands,
  listBandProjects,
  listProjectSongs,
  getProjectActivity,
  setApiIdentityUserId,
  updateSongNote,
  uploadSongStem,
} from "../api";

afterEach(() => {
  setApiIdentityUserId(null);
});

describe("api bands/projects/songs contract", () => {
  it("fetches bands", async () => {
    const originalFetch = globalThis.fetch;
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ bands: [{ id: 1, name: "Default Band", owner_user_id: 1, created_at: "2026-03-09", project_count: 1 }] }),
    });
    (globalThis as unknown as { fetch: typeof fetch }).fetch = fetchMock as unknown as typeof fetch;

    try {
      const res = await listBands();
      expect(fetchMock).toHaveBeenCalledWith("/api/bands");
      expect(res.bands[0].name).toBe("Default Band");
    } finally {
      (globalThis as unknown as { fetch: typeof fetch }).fetch = originalFetch;
    }
  });

  it("fetches projects for a band", async () => {
    const originalFetch = globalThis.fetch;
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ projects: [{ id: 5, band_id: 1, name: "Default Project", description: null, created_at: "2026-03-09", song_count: 2, unread_count: 0 }] }),
    });
    (globalThis as unknown as { fetch: typeof fetch }).fetch = fetchMock as unknown as typeof fetch;

    try {
      const res = await listBandProjects(1);
      expect(fetchMock).toHaveBeenCalledWith("/api/bands/1/projects");
      expect(res.projects[0].band_id).toBe(1);
    } finally {
      (globalThis as unknown as { fetch: typeof fetch }).fetch = originalFetch;
    }
  });

  it("attaches the acting-user header to collaboration requests", async () => {
    const originalFetch = globalThis.fetch;
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        members: [],
      }),
    });
    (globalThis as unknown as { fetch: typeof fetch }).fetch = fetchMock as unknown as typeof fetch;

    try {
      setApiIdentityUserId(12);

      await listBandMembers(5);
      await getProjectActivity(9);

      expect(fetchMock).toHaveBeenNthCalledWith(
        1,
        "/api/bands/5/members",
        expect.objectContaining({ headers: expect.objectContaining({ "X-DeChord-User-Id": "12" }) }),
      );
      expect(fetchMock).toHaveBeenNthCalledWith(
        2,
        "/api/projects/9/activity",
        expect.objectContaining({ headers: expect.objectContaining({ "X-DeChord-User-Id": "12" }) }),
      );
    } finally {
      (globalThis as unknown as { fetch: typeof fetch }).fetch = originalFetch;
    }
  });

  it("attaches the acting-user header to collaboration writes", async () => {
    const originalFetch = globalThis.fetch;
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ project: { id: 11 } }),
    });
    (globalThis as unknown as { fetch: typeof fetch }).fetch = fetchMock as unknown as typeof fetch;

    try {
      setApiIdentityUserId(12);

      await createBand({ name: "My Band" });
      await uploadSongStem(7, { stemKey: "bass", file: new File(["stem"], "bass.wav", { type: "audio/wav" }) });
      await regenerateSongStems(7);
      await createSongNote(7, { type: "time", text: "Pocket", timestamp_sec: 8, toast_duration_sec: 4 });
      await updateSongNote(9, { text: "Tighter", toast_duration_sec: 6 });
      await resolveSongNote(9, true);
      await deleteSongNote(9);

      expect(fetchMock).toHaveBeenNthCalledWith(
        1,
        "/api/bands",
        expect.objectContaining({ headers: expect.objectContaining({ "X-DeChord-User-Id": "12" }) }),
      );
      expect(fetchMock).toHaveBeenNthCalledWith(
        2,
        "/api/songs/7/stems/upload",
        expect.objectContaining({ headers: expect.objectContaining({ "X-DeChord-User-Id": "12" }) }),
      );
      expect(fetchMock).toHaveBeenNthCalledWith(
        3,
        "/api/songs/7/stems/regenerate",
        expect.objectContaining({ headers: expect.objectContaining({ "X-DeChord-User-Id": "12" }) }),
      );
      expect(fetchMock).toHaveBeenNthCalledWith(
        4,
        "/api/songs/7/notes",
        expect.objectContaining({ headers: expect.objectContaining({ "X-DeChord-User-Id": "12" }) }),
      );
      expect(fetchMock).toHaveBeenNthCalledWith(
        5,
        "/api/notes/9",
        expect.objectContaining({ headers: expect.objectContaining({ "X-DeChord-User-Id": "12" }) }),
      );
      expect(fetchMock).toHaveBeenNthCalledWith(
        6,
        "/api/notes/9/resolve",
        expect.objectContaining({ headers: expect.objectContaining({ "X-DeChord-User-Id": "12" }) }),
      );
      expect(fetchMock).toHaveBeenNthCalledWith(
        7,
        "/api/notes/9",
        expect.objectContaining({ headers: expect.objectContaining({ "X-DeChord-User-Id": "12" }) }),
      );
    } finally {
      (globalThis as unknown as { fetch: typeof fetch }).fetch = originalFetch;
    }
  });

  it("fetches songs for a project", async () => {
    const originalFetch = globalThis.fetch;
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ songs: [{ id: 8, project_id: 5, title: "The Trooper", original_filename: "trooper.mp3", created_at: "2026-03-09", key: "Em", tempo: 160, duration: 48 }] }),
    });
    (globalThis as unknown as { fetch: typeof fetch }).fetch = fetchMock as unknown as typeof fetch;

    try {
      const res = await listProjectSongs(5);
      expect(fetchMock).toHaveBeenCalledWith("/api/projects/5/songs");
      expect(res.songs[0].project_id).toBe(5);
    } finally {
      (globalThis as unknown as { fetch: typeof fetch }).fetch = originalFetch;
    }
  });

  it("creates a band", async () => {
    const originalFetch = globalThis.fetch;
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ band: { id: 11, name: "My Band", owner_user_id: 1, created_at: "2026-03-10", project_count: 0 } }),
    });
    (globalThis as unknown as { fetch: typeof fetch }).fetch = fetchMock as unknown as typeof fetch;

    try {
      const res = await createBand({ name: "My Band" });
      expect(fetchMock).toHaveBeenCalledWith("/api/bands", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: "My Band" }),
      });
      expect(res.band.id).toBe(11);
    } finally {
      (globalThis as unknown as { fetch: typeof fetch }).fetch = originalFetch;
    }
  });

  it("creates a project under a band", async () => {
    const originalFetch = globalThis.fetch;
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ project: { id: 22, band_id: 11, name: "Album Prep", description: "Spring set", created_at: "2026-03-10", song_count: 0 } }),
    });
    (globalThis as unknown as { fetch: typeof fetch }).fetch = fetchMock as unknown as typeof fetch;

    try {
      const res = await createProject(11, { name: "Album Prep", description: "Spring set" });
      expect(fetchMock).toHaveBeenCalledWith("/api/bands/11/projects", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: "Album Prep", description: "Spring set" }),
      });
      expect(res.project.band_id).toBe(11);
    } finally {
      (globalThis as unknown as { fetch: typeof fetch }).fetch = originalFetch;
    }
  });
});
