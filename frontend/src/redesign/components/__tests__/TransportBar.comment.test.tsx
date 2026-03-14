import { fireEvent, render, screen } from "@testing-library/react";
import "@testing-library/jest-dom";
import { describe, expect, it, vi } from "vitest";
import { TransportBar } from "../TransportBar";
import type { NoteMarker } from "../../lib/types";

const baseProps = {
  currentTime: 30,
  duration: 120,
  playing: false,
  volume: 0.8,
  speedPercent: 100,
  loopActive: false,
  noteMarkers: [],
  currentUserId: null,
  onTogglePlay: vi.fn(),
  onSeek: vi.fn(),
  onSeekRelative: vi.fn(),
  onVolumeChange: vi.fn(),
  onSpeedChange: vi.fn(),
  onClearLoop: vi.fn(),
  onCommentLaneClick: vi.fn(),
  onMarkerClick: vi.fn(),
};

describe("TransportBar CommentLane", () => {
  it("fires onCommentLaneClick with correct timestamp when clicking empty lane", () => {
    const onCommentLaneClick = vi.fn();
    render(<TransportBar {...baseProps} onCommentLaneClick={onCommentLaneClick} />);
    const lane = screen.getByTestId("comment-lane");
    // Simulate click at 50% of lane width → 0.5 * 120 = 60s
    Object.defineProperty(lane, "getBoundingClientRect", {
      value: () => ({ left: 0, width: 200, top: 0, right: 200, bottom: 12, height: 12 }),
    });
    fireEvent.click(lane, { clientX: 100 }); // 50% → 60s
    expect(onCommentLaneClick).toHaveBeenCalledWith(expect.closeTo(60, 0));
  });

  it("fires onMarkerClick when clicking a dot, not onCommentLaneClick", () => {
    const onMarkerClick = vi.fn();
    const onCommentLaneClick = vi.fn();
    const markers = [{ id: 42, timestampSec: 30, userId: 7 }];
    render(
      <TransportBar
        {...baseProps}
        noteMarkers={markers}
        onMarkerClick={onMarkerClick}
        onCommentLaneClick={onCommentLaneClick}
      />,
    );
    fireEvent.click(screen.getByTestId("comment-marker-42"));
    expect(onMarkerClick).toHaveBeenCalledWith(42, 30);
    expect(onCommentLaneClick).not.toHaveBeenCalled();
  });

  it("shows hover tooltip with author and text on dot hover", async () => {
    const markers: NoteMarker[] = [
      { id: 1, timestampSec: 30, userId: 5, authorName: "Sarah K.", text: "Watch this", toastDurationSec: 4.2 },
    ];
    render(<TransportBar {...baseProps} noteMarkers={markers} />);
    const dot = screen.getByTestId("comment-marker-1");
    fireEvent.mouseEnter(dot);
    expect(await screen.findByText("Sarah K.")).toBeInTheDocument();
    expect(screen.getByText("Watch this")).toBeInTheDocument();
  });

  it("renders own dot with solid style and other dot with outline style", () => {
    const markers: NoteMarker[] = [
      { id: 1, timestampSec: 10, userId: 99 },  // own
      { id: 2, timestampSec: 40, userId: 5 },   // other
    ];
    render(<TransportBar {...baseProps} currentUserId={99} noteMarkers={markers} />);
    expect(screen.getByTestId("comment-marker-1")).toHaveAttribute("data-own", "true");
    expect(screen.getByTestId("comment-marker-2")).toHaveAttribute("data-own", "false");
  });
});