// @vitest-environment node
import { describe, expect, it } from "vitest";

import config from "./vite.config";

describe("vite dev proxy", () => {
  it("routes /api traffic to portless backend host", () => {
    const target = (config.server?.proxy as Record<string, { target: string }>)?.["/api"]?.target;
    expect(target).toBe("http://api.dechord.localhost");
  });

  it("excludes alphaTab from dep optimizer to keep worker/font assets resolvable", () => {
    const excluded = config.optimizeDeps?.exclude ?? [];
    expect(excluded).toContain("@coderline/alphatab");
  });
});
