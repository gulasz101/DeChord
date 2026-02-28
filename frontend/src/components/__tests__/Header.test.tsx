import { describe, it, expect } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { Header } from "../Header";

describe("Header", () => {
  it("renders app title", () => {
    const html = renderToStaticMarkup(<Header />);
    expect(html).toContain("DeChord");
  });

  it("renders key, tempo, and filename when provided", () => {
    const html = renderToStaticMarkup(
      <Header songKey="C major" tempo={120} fileName="song" />,
    );
    expect(html).toContain("C major | 120 BPM");
    expect(html).toContain("song");
  });
});
