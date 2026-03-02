import { describe, expect, it } from "vitest";
import { deriveStemWarning } from "../lib/uploadWarnings";

describe("upload warning integration", () => {
  it("returns warning when stems split failed with explicit error", () => {
    const warning = deriveStemWarning({
      stems_status: "failed",
      stems_error: "Stem runtime dependency missing: lameenc",
    });

    expect(warning).toContain("Stem splitting failed");
    expect(warning).toContain("lameenc");
  });

  it("returns no warning when stems are complete", () => {
    const warning = deriveStemWarning({
      stems_status: "complete",
      stems_error: null,
    });

    expect(warning).toBeNull();
  });
});
