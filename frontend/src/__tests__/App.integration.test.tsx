import { describe, it, expect } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import App from "../App";

describe("App integration", () => {
  it("shows drop zone prompt before analysis", () => {
    const html = renderToStaticMarkup(<App />);
    expect(html).toContain("Drop audio file here or click to browse");
  });
});
