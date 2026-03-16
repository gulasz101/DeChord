import { describe, it, expect } from "vitest";

describe("environment check", () => {
  it("should have document defined", () => {
    expect(document).toBeDefined();
  });
});