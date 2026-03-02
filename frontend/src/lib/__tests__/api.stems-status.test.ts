import { afterEach, describe, expect, it, vi } from "vitest";
import { listSongStems, uploadAudio } from "../api";

describe("api stems/status contract", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("sends process_mode on upload analyze request", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ job_id: "job123", song_id: 7 }),
    });
    vi.stubGlobal("fetch", fetchMock);

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
  });

  it("fetches song stems list", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        stems: [
          { stem_key: "drums", relative_path: "stems/1/drums.wav", mime_type: "audio/x-wav", duration: null },
        ],
      }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const res = await listSongStems(42);

    expect(fetchMock).toHaveBeenCalledWith("/api/songs/42/stems");
    expect(res.stems).toHaveLength(1);
    expect(res.stems[0].stem_key).toBe("drums");
  });
});
