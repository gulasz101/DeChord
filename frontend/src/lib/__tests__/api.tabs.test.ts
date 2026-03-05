import { describe, expect, it, vi } from "vitest";
import { getMidiFileUrl, getSongTabs, getTabDownloadUrl, getTabFileUrl } from "../api";

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
});
