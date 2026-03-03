import { describe, it, expect } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import App from "../App";
import { resolvePlaybackSources } from "../lib/playbackSources";

describe("App integration", () => {
  it("shows drop zone prompt before analysis", () => {
    const html = renderToStaticMarkup(<App />);
    expect(html).toContain("Drop audio file here or click to browse");
    expect(html).toContain("Show Tabs");
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
