import { describe, expect, it } from "vitest";
import { resolvePlaybackSources } from "../playbackSources";

describe("resolvePlaybackSources mode routing", () => {
  const stems = [
    { stem_key: "drums", relative_path: "stems/5/drums.wav", mime_type: "audio/x-wav", duration: null },
    { stem_key: "vocals", relative_path: "stems/5/vocals.wav", mime_type: "audio/x-wav", duration: null },
  ];

  it("uses only full mix when playback mode is full_mix", () => {
    const resolved = resolvePlaybackSources({
      songId: 5,
      playbackMode: "full_mix",
      stems,
      enabledByStem: { drums: true, vocals: true },
    });

    expect(resolved.audioSrc).toBe("/api/audio/5");
    expect(resolved.stemSources).toHaveLength(0);
    expect(resolved.usingStems).toBe(false);
  });

  it("uses selected stems when playback mode is stems", () => {
    const resolved = resolvePlaybackSources({
      songId: 5,
      playbackMode: "stems",
      stems,
      enabledByStem: { drums: true, vocals: false },
    });

    expect(resolved.stemSources).toHaveLength(1);
    expect(resolved.stemSources[0].key).toBe("drums");
    expect(resolved.usingStems).toBe(true);
  });

  it("falls back to full mix when no stem is selected in stems mode", () => {
    const resolved = resolvePlaybackSources({
      songId: 5,
      playbackMode: "stems",
      stems,
      enabledByStem: { drums: false, vocals: false },
    });

    expect(resolved.audioSrc).toBe("/api/audio/5");
    expect(resolved.stemSources).toHaveLength(0);
    expect(resolved.usingStems).toBe(false);
  });
});
