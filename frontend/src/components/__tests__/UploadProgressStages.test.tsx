import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { DropZone } from "../DropZone";

describe("DropZone upload progress stages", () => {
  it("renders overall and stage progress with stage label", () => {
    const html = renderToStaticMarkup(
      <DropZone
        onFile={() => {}}
        loading
        progressText="Splitting stems..."
        progressPct={67}
        stageProgressPct={42}
        stage="splitting_stems"
      />,
    );

    expect(html).toContain("Splitting stems...");
    expect(html).toContain("67%");
    expect(html).toContain("42%");
    expect(html).toContain("splitting_stems");
  });
});
