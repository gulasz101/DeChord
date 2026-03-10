import { describe, expect, it, vi } from "vitest";
import { getMidiFileUrl, getSongTabs, getTabDownloadUrl, getTabFileUrl, regenerateSongTabs } from "../api";

describe("api tab artifact urls", () => {
  it("builds midi file endpoint url", () => {
    expect(getMidiFileUrl(7)).toBe("/api/songs/7/midi/file");
  });

  it("builds tab file endpoint url", () => {
    expect(getTabFileUrl(7)).toBe("/api/songs/7/tabs/file");
  });

  it("builds tab download endpoint url", () => {
    expect(getTabDownloadUrl(7)).toBe("/api/songs/7/tabs/download");
  });

  it("fetches song tab metadata", async () => {
    const originalFetch = globalThis.fetch;
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ tab: null }),
    });
    (globalThis as unknown as { fetch: typeof fetch }).fetch = fetchMock as unknown as typeof fetch;

    try {
      const res = await getSongTabs(9);
      expect(fetchMock).toHaveBeenCalledWith("/api/songs/9/tabs");
      expect(res.tab).toBeNull();
    } finally {
      (globalThis as unknown as { fetch: typeof fetch }).fetch = originalFetch;
    }
  });

  it("posts selected source stem when regenerating song tabs", async () => {
    const originalFetch = globalThis.fetch;
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        tab: {
          id: 11,
          source_stem_key: "bass",
          source_midi_id: 9,
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
    });
    (globalThis as unknown as { fetch: typeof fetch }).fetch = fetchMock as unknown as typeof fetch;

    try {
      const res = await regenerateSongTabs(7, { source_stem_key: "bass" });

      expect(fetchMock).toHaveBeenCalledWith("/api/songs/7/tabs/regenerate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ source_stem_key: "bass" }),
      });
      expect(res.tab?.source_stem_key).toBe("bass");
    } finally {
      (globalThis as unknown as { fetch: typeof fetch }).fetch = originalFetch;
    }
  });
});
