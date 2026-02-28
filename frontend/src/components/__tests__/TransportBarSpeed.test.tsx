import { describe, it, expect } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { TransportBar } from "../TransportBar";

describe("TransportBar speed options", () => {
  it("includes 40% and 200% speed options", () => {
    const html = renderToStaticMarkup(
      <TransportBar
        currentTime={0}
        duration={120}
        playing={false}
        volume={1}
        speedPercent={100}
        noteMarkers={[]}
        loopActive={false}
        onTogglePlay={() => {}}
        onSeek={() => {}}
        onSeekRelative={() => {}}
        onProgressClick={() => {}}
        onVolumeChange={() => {}}
        onSpeedChange={() => {}}
        onClearLoop={() => {}}
      />,
    );

    expect(html).toContain(">40%<");
    expect(html).toContain(">200%<");
  });
});
