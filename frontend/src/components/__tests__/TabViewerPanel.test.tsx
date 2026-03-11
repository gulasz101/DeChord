import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

const alphaTabState = vi.hoisted(() => {
  const instances: Array<{
    timePosition: number;
    scrollToCursor: ReturnType<typeof vi.fn>;
    destroy: ReturnType<typeof vi.fn>;
    renderFinished: { on: (cb: () => void) => void };
  }> = [];
  const settings: unknown[] = [];

  class AlphaTabApi {
    timePosition = 0;
    scrollToCursor = vi.fn();
    destroy = vi.fn();
    renderFinished = {
      on: (cb: () => void) => {
        cb();
      },
    };

    constructor(_container: HTMLElement, config: unknown) {
      settings.push(config);
      instances.push(this);
    }
  }

  return { AlphaTabApi, instances, settings };
});

vi.mock("@coderline/alphatab", () => ({
  AlphaTabApi: alphaTabState.AlphaTabApi,
}));

import { TabViewerPanel } from "../TabViewerPanel";
import { createTabViewerSettings, findCurrentBarIndex, getDisplayWindowForBar } from "../tabViewer";

afterEach(() => {
  alphaTabState.instances.length = 0;
  alphaTabState.settings.length = 0;
});

describe("TabViewerPanel", () => {
  it("shows fallback message when tab url is unavailable", () => {
    render(<TabViewerPanel tabSourceUrl={null} currentTime={0} isPlaying={false} />);
    expect(screen.getByText("Tabs are not available for this song yet.")).toBeTruthy();
  });

  it("loads a real tab asset url and follows the shared transport clock", async () => {
    const { rerender } = render(
      <TabViewerPanel tabSourceUrl="/api/songs/2/tabs/file" currentTime={0} isPlaying={false} />,
    );
    expect(screen.getByText("Tab Viewer")).toBeTruthy();
    const hostClass = screen.getByTestId("tab-viewer-scrollhost").className;
    expect(hostClass).toContain("overflow-x-auto");
    expect(hostClass).toContain("bg-white");

    await waitFor(() => {
      expect(alphaTabState.settings).toHaveLength(1);
    });

    expect(alphaTabState.settings[0]).toMatchObject({ file: "/api/songs/2/tabs/file" });
    expect(alphaTabState.instances[0]?.timePosition).toBe(0);

    rerender(
      <TabViewerPanel tabSourceUrl="/api/songs/2/tabs/file" currentTime={12.5} isPlaying={true} />,
    );

    await waitFor(() => {
      expect(alphaTabState.instances[0]?.timePosition).toBe(12500);
    });
    expect(alphaTabState.instances[0]?.scrollToCursor).toHaveBeenCalled();
  });

  it("maps playback ticks to the active bar", () => {
    const starts = [0, 480, 960, 1440];
    expect(findCurrentBarIndex(starts, 0)).toBe(0);
    expect(findCurrentBarIndex(starts, 479)).toBe(0);
    expect(findCurrentBarIndex(starts, 480)).toBe(1);
    expect(findCurrentBarIndex(starts, 1500)).toBe(3);
  });

  it("returns a 4-bar forward-looking display window", () => {
    expect(getDisplayWindowForBar(0, 12)).toEqual({ startBar: 1, barCount: 4 });
    expect(getDisplayWindowForBar(5, 12)).toEqual({ startBar: 6, barCount: 4 });
    expect(getDisplayWindowForBar(10, 12)).toEqual({ startBar: 11, barCount: 2 });
    expect(getDisplayWindowForBar(20, 12)).toEqual({ startBar: 12, barCount: 1 });
  });

  it("configures alphaTab to render tab-only view", () => {
    const settings = createTabViewerSettings("/api/songs/2/tabs/file", "html,body");
    expect(settings.display.staveProfile).toBe("Tab");
    expect(settings.display.layoutMode).toBe("Horizontal");
    expect(settings.display.barCount).toBe(-1);
    expect(settings.display.scale).toBe(1.35);
    expect(settings.player.scrollMode).toBe("Continuous");
    expect(settings.player.enableCursor).toBe(true);
    expect(settings.player.enableAnimatedBeatCursor).toBe(true);
    expect(settings.player.enableElementHighlighting).toBe(true);
    expect(settings.core.smuflFontSources instanceof Map).toBe(true);
  });
});
