import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { TabViewerPanel } from "../TabViewerPanel";

describe("TabViewerPanel", () => {
  it("shows fallback message when tab url is unavailable", () => {
    render(<TabViewerPanel tabSourceUrl={null} currentTime={0} />);
    expect(screen.getByText("Tabs are not available for this song yet.")).toBeTruthy();
  });

  it("renders panel and syncs with playback time", () => {
    const onSyncTime = vi.fn();
    const { rerender } = render(
      <TabViewerPanel tabSourceUrl="/api/songs/2/tabs/file" currentTime={0} onSyncTime={onSyncTime} />,
    );
    expect(screen.getByText("Tab Viewer")).toBeTruthy();

    rerender(<TabViewerPanel tabSourceUrl="/api/songs/2/tabs/file" currentTime={12.5} onSyncTime={onSyncTime} />);
    expect(onSyncTime).toHaveBeenCalledWith(12.5);
  });
});
