import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { DropZone } from "../DropZone";
import { SongLibraryPanel } from "../SongLibraryPanel";

describe("DropZone upload mode", () => {
  it("renders both upload mode options", () => {
    const html = renderToStaticMarkup(
      <DropZone onFile={() => {}} />,
    );

    expect(html).toContain("Analyze chords only");
    expect(html).toContain("Analyze + split stems");
    expect(html).toContain('name="process-mode"');
    expect(html).not.toContain("Tab accuracy");
    expect(html).not.toContain("Standard (faster)");
    expect(html).not.toContain("High accuracy (slower)");
    expect(html).not.toContain("High accuracy aggressive (slowest)");
  });

  it("renders upload mode options in Song Library upload flow", () => {
    const html = renderToStaticMarkup(
      <SongLibraryPanel
        songs={[]}
        selectedSongId={null}
        onSelect={() => {}}
        onUpload={() => {}}
      />,
    );

    expect(html).toContain("Analyze chords only");
    expect(html).toContain("Analyze + split stems");
    expect(html).toContain('name="library-process-mode"');
    expect(html).not.toContain("Tab accuracy");
    expect(html).not.toContain("Standard (faster)");
    expect(html).not.toContain("High accuracy (slower)");
    expect(html).not.toContain("High accuracy aggressive (slowest)");
  });
});
