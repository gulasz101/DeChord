import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { StemMixerPanel } from "../StemMixerPanel";

describe("StemMixerPanel", () => {
  it("renders playback mode radios and stem checkboxes", () => {
    const html = renderToStaticMarkup(
      <StemMixerPanel
        playbackMode="stems"
        onModeChange={() => {}}
        stems={[
          { stem_key: "drums", relative_path: "stems/1/drums.wav", mime_type: "audio/x-wav", duration: null },
          { stem_key: "vocals", relative_path: "stems/1/vocals.wav", mime_type: "audio/x-wav", duration: null },
        ]}
        enabledByStem={{ drums: true, vocals: true }}
        onToggle={() => {}}
      />,
    );

    expect(html).toContain("Stem Mixer");
    expect(html).toContain("Full Mix");
    expect(html).toContain("Stems");
    expect(html).toContain('type="radio"');
    expect(html).toContain("drums");
    expect(html).toContain("vocals");
    expect(html).toContain('type="checkbox"');
  });
});
