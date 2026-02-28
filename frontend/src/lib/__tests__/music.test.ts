import { describe, it, expect } from "vitest";
import {
  noteNameToIndex,
  parseChordLabel,
  getChordNotes,
  getFretboardPositions,
} from "../music";

describe("noteNameToIndex", () => {
  it("returns correct index for C", () => {
    expect(noteNameToIndex("C")).toBe(0);
  });
  it("returns correct index for A", () => {
    expect(noteNameToIndex("A")).toBe(9);
  });
  it("handles sharps", () => {
    expect(noteNameToIndex("F#")).toBe(6);
  });
  it("handles flats by converting to sharps", () => {
    expect(noteNameToIndex("Bb")).toBe(10);
  });
});

describe("parseChordLabel", () => {
  it("parses major chord", () => {
    expect(parseChordLabel("C")).toEqual({ root: 0, quality: "" });
  });
  it("parses minor chord", () => {
    expect(parseChordLabel("Am")).toEqual({ root: 9, quality: "m" });
  });
  it("returns null for N (no chord)", () => {
    expect(parseChordLabel("N")).toBeNull();
  });
  it("parses seventh chord", () => {
    expect(parseChordLabel("G7")).toEqual({ root: 7, quality: "7" });
  });
});

describe("getChordNotes", () => {
  it("returns correct notes for C major", () => {
    // C=0, E=4, G=7
    expect(getChordNotes("C")).toEqual([0, 4, 7]);
  });
  it("returns correct notes for Am", () => {
    // A=9, C=0, E=4
    expect(getChordNotes("Am")).toEqual([9, 0, 4]);
  });
  it("returns empty for N", () => {
    expect(getChordNotes("N")).toEqual([]);
  });
});

describe("getFretboardPositions", () => {
  it("returns positions for Am chord", () => {
    const positions = getFretboardPositions("Am");
    expect(positions.length).toBeGreaterThan(0);
    // All positions should be A, C, or E notes
    for (const pos of positions) {
      expect(["A", "C", "E"]).toContain(pos.note);
    }
  });
  it("includes open E string for E chord", () => {
    const positions = getFretboardPositions("E");
    const openE = positions.find((p) => p.string === 0 && p.fret === 0);
    expect(openE).toBeDefined();
    expect(openE!.note).toBe("E");
  });
});
