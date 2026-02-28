import { describe, it, expect } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { Fretboard } from "../Fretboard";

describe("Fretboard", () => {
  it("renders both current and next chord labels", () => {
    const html = renderToStaticMarkup(<Fretboard chordLabel="C" nextChordLabel="G" />);
    expect(html).toContain("C");
    expect(html).toContain("G");
  });
});
