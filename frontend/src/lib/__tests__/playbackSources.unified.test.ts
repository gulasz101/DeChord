import { describe, it, expect } from "vitest";
import { resolvePlaybackSources } from "../playbackSources";

describe("resolvePlaybackSources unified", () => {
  it("always includes full_mix as first source", () => {
    const result = resolvePlaybackSources({
      songId: 1,
      stems: [
        { stemKey: "bass", relativePath: "bass.wav", mimeType: null, duration: null },
        { stemKey: "drums", relativePath: "drums.wav", mimeType: null, duration: null },
      ],
      enabledBySourceKey: { __full_mix__: true, bass: false, drums: false },
    });

    expect(result.sources).toHaveLength(3);
    expect(result.sources[0].key).toBe("__full_mix__");
    expect(result.sources[0].enabled).toBe(true);
    expect(result.sources[1].key).toBe("bass");
    expect(result.sources[2].key).toBe("drums");
  });

  it("returns only full_mix when no stems", () => {
    const result = resolvePlaybackSources({
      songId: 1,
      stems: [],
      enabledBySourceKey: { __full_mix__: true },
    });

    expect(result.sources).toHaveLength(1);
    expect(result.sources[0].key).toBe("__full_mix__");
  });

  it("respects enabledBySourceKey for all sources", () => {
    const result = resolvePlaybackSources({
      songId: 1,
      stems: [{ stemKey: "bass", relativePath: "bass.wav", mimeType: null, duration: null }],
      enabledBySourceKey: { __full_mix__: false, bass: true },
    });

    expect(result.sources[0].enabled).toBe(false);
    expect(result.sources[1].enabled).toBe(true);
  });

  it("returns empty array for null songId", () => {
    const result = resolvePlaybackSources({
      songId: null,
      stems: [],
      enabledBySourceKey: {},
    });

    expect(result.sources).toHaveLength(0);
  });
});