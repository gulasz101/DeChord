import { describe, expect, it, vi } from "vitest";
import { getSongTabs, listSongStems, uploadSongStem } from "../api";
import type { SongTabMeta, StemInfo } from "../types";

type IsRequired<T, K extends keyof T> = {} extends Pick<T, K> ? false : true;

const stemMimeTypeRequired: IsRequired<StemInfo, "mime_type"> = true;
const stemDurationRequired: IsRequired<StemInfo, "duration"> = true;
const tabSourceMidiIdRequired: IsRequired<SongTabMeta, "source_midi_id"> = true;
const tabTuningRequired: IsRequired<SongTabMeta, "tuning"> = true;
const tabStringsRequired: IsRequired<SongTabMeta, "strings"> = true;
const tabErrorMessageRequired: IsRequired<SongTabMeta, "error_message"> = true;
const tabCreatedAtRequired: IsRequired<SongTabMeta, "created_at"> = true;

void stemMimeTypeRequired;
void stemDurationRequired;
void tabSourceMidiIdRequired;
void tabTuningRequired;
void tabStringsRequired;
void tabErrorMessageRequired;
void tabCreatedAtRequired;

describe("song detail asset api", () => {
  it("returns stem provenance metadata", async () => {
    const originalFetch = globalThis.fetch;
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        stems: [
          {
            id: 10,
            stem_key: "bass",
            source_type: "user",
            display_name: "Bass DI",
            version_label: "manual-2",
            is_archived: false,
            uploaded_by_name: "Groove Bassline",
            relative_path: "stems/30/bass.wav",
            mime_type: "audio/wav",
            duration: 42,
            created_at: "2026-03-10T10:00:00Z",
          },
        ],
      }),
    });
    (globalThis as unknown as { fetch: typeof fetch }).fetch = fetchMock as unknown as typeof fetch;

    try {
      await expect(listSongStems(30)).resolves.toMatchObject({
        stems: [expect.objectContaining({ source_type: "user", uploaded_by_name: "Groove Bassline" })],
      });
    } finally {
      (globalThis as unknown as { fetch: typeof fetch }).fetch = originalFetch;
    }
  });

  it("uploads a song-scoped stem with form data", async () => {
    const originalFetch = globalThis.fetch;
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ stems: [] }) });
    (globalThis as unknown as { fetch: typeof fetch }).fetch = fetchMock as unknown as typeof fetch;

    try {
      await uploadSongStem(30, {
        stemKey: "bass",
        file: new File(["bass"], "bass.wav", { type: "audio/wav" }),
      });

      expect(fetchMock).toHaveBeenCalledTimes(1);
      const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
      expect(url).toBe("/api/songs/30/stems/upload");
      expect(init.method).toBe("POST");
      const form = init.body as FormData;
      expect(form.get("stem_key")).toBe("bass");
      expect(form.get("file")).toBeInstanceOf(File);
    } finally {
      (globalThis as unknown as { fetch: typeof fetch }).fetch = originalFetch;
    }
  });

  it("returns current tab provenance metadata", async () => {
    const originalFetch = globalThis.fetch;
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        tab: {
          id: 99,
          source_stem_key: "bass",
          source_type: "user",
          source_display_name: "Bass DI",
          source_midi_id: 31,
          tab_format: "alphatex",
          tuning: "E1,A1,D2,G2",
          strings: 4,
          generator_version: "v2-rhythm-grid",
          status: "complete",
          error_message: null,
          created_at: "2026-03-10T10:00:00Z",
          updated_at: "2026-03-10T10:05:00Z",
        },
      }),
    });
    (globalThis as unknown as { fetch: typeof fetch }).fetch = fetchMock as unknown as typeof fetch;

    try {
      await expect(getSongTabs(30)).resolves.toMatchObject({
        tab: expect.objectContaining({ source_stem_key: "bass", source_display_name: "Bass DI" }),
      });
    } finally {
      (globalThis as unknown as { fetch: typeof fetch }).fetch = originalFetch;
    }
  });
});
