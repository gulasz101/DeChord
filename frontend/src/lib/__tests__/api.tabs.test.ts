import { describe, expect, it } from "vitest";
import { getMidiFileUrl, getTabFileUrl } from "../api";

describe("api tab artifact urls", () => {
  it("builds midi file endpoint url", () => {
    expect(getMidiFileUrl(7)).toBe("/api/songs/7/midi/file");
  });

  it("builds tab file endpoint url", () => {
    expect(getTabFileUrl(7)).toBe("/api/songs/7/tabs/file");
  });
});
