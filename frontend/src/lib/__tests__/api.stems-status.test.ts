import { describe, expect, it, vi } from "vitest";
import { getStemDownloadUrl, getStemsZipDownloadUrl, listSongStems, uploadAudio } from "../api";

describe("api stems/status contract", () => {
  it("sends process_mode and default tabGenerationQuality on upload analyze request", async () => {
    const originalFetch = globalThis.fetch;
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ job_id: "job123", song_id: 7 }),
    });
    (globalThis as unknown as { fetch: typeof fetch }).fetch = fetchMock as unknown as typeof fetch;

    try {
      const file = new File([new Uint8Array([1, 2, 3])], "demo.mp3", {
        type: "audio/mpeg",
      });
      await uploadAudio(file, "analysis_and_stems");

      expect(fetchMock).toHaveBeenCalledTimes(1);
      const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
      expect(url).toBe("/api/analyze");
      expect(init.method).toBe("POST");
      const form = init.body as FormData;
      expect(form.get("process_mode")).toBe("analysis_and_stems");
      expect(form.get("tabGenerationQuality")).toBe("standard");
    } finally {
      (globalThis as unknown as { fetch: typeof fetch }).fetch = originalFetch;
    }
  });

  it("sends tabGenerationQuality when high accuracy is selected", async () => {
    const originalFetch = globalThis.fetch;
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ job_id: "job123", song_id: 7 }),
    });
    (globalThis as unknown as { fetch: typeof fetch }).fetch = fetchMock as unknown as typeof fetch;

    try {
      const file = new File([new Uint8Array([1, 2, 3])], "demo.mp3", {
        type: "audio/mpeg",
      });
      await uploadAudio(file, "analysis_and_stems", "high_accuracy");

      expect(fetchMock).toHaveBeenCalledTimes(1);
      const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
      expect(url).toBe("/api/analyze");
      expect(init.method).toBe("POST");
      const form = init.body as FormData;
      expect(form.get("process_mode")).toBe("analysis_and_stems");
      expect(form.get("tabGenerationQuality")).toBe("high_accuracy");
    } finally {
      (globalThis as unknown as { fetch: typeof fetch }).fetch = originalFetch;
    }
  });

  it("sends tabGenerationQuality when high accuracy aggressive is selected", async () => {
    const originalFetch = globalThis.fetch;
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ job_id: "job123", song_id: 7 }),
    });
    (globalThis as unknown as { fetch: typeof fetch }).fetch = fetchMock as unknown as typeof fetch;

    try {
      const file = new File([new Uint8Array([1, 2, 3])], "demo.mp3", {
        type: "audio/mpeg",
      });
      await uploadAudio(file, "analysis_and_stems", "high_accuracy_aggressive");

      expect(fetchMock).toHaveBeenCalledTimes(1);
      const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
      expect(url).toBe("/api/analyze");
      expect(init.method).toBe("POST");
      const form = init.body as FormData;
      expect(form.get("process_mode")).toBe("analysis_and_stems");
      expect(form.get("tabGenerationQuality")).toBe("high_accuracy_aggressive");
    } finally {
      (globalThis as unknown as { fetch: typeof fetch }).fetch = originalFetch;
    }
  });

  it("fetches song stems list", async () => {
    const originalFetch = globalThis.fetch;
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        stems: [
          { stem_key: "drums", relative_path: "stems/1/drums.wav", mime_type: "audio/x-wav", duration: null },
        ],
      }),
    });
    (globalThis as unknown as { fetch: typeof fetch }).fetch = fetchMock as unknown as typeof fetch;

    try {
      const res = await listSongStems(42);

      expect(fetchMock).toHaveBeenCalledWith("/api/songs/42/stems");
      expect(res.stems).toHaveLength(1);
      expect(res.stems[0].stem_key).toBe("drums");
    } finally {
      (globalThis as unknown as { fetch: typeof fetch }).fetch = originalFetch;
    }
  });

  it("builds per-stem and zip download urls", () => {
    expect(getStemDownloadUrl(7, "bass")).toBe("/api/songs/7/stems/bass/download");
    expect(getStemsZipDownloadUrl(7)).toBe("/api/songs/7/stems/download");
  });
});
