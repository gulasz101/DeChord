import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { DropZone } from "../DropZone";

describe("DropZone upload mode", () => {
  it("renders both upload mode options", () => {
    const html = renderToStaticMarkup(
      <DropZone onFile={() => {}} />,
    );

    expect(html).toContain("Analyze chords only");
    expect(html).toContain("Analyze + split stems");
    expect(html).toContain('name="process-mode"');
  });
});
