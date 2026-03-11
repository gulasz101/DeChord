import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { TransportBar } from "../TransportBar";

describe("TransportBar transport contract", () => {
  it("uses the shared transport prop names for play, seek, rate, and volume controls", () => {
    const togglePlay = vi.fn();
    const seek = vi.fn();
    const seekRelative = vi.fn();
    const setPlaybackRate = vi.fn();
    const setVolume = vi.fn();

    render(
      <TransportBar
        currentTime={15}
        duration={120}
        playing={false}
        volume={1}
        playbackRate={1}
        timeNoteMarkers={[]}
        loopActive={false}
        togglePlay={togglePlay}
        seek={seek}
        onSeekDragStart={() => {}}
        onSeekDragEnd={() => {}}
        seekRelative={seekRelative}
        onNoteLaneClick={() => {}}
        onNoteMarkerClick={() => {}}
        setVolume={setVolume}
        setPlaybackRate={setPlaybackRate}
        onClearLoop={() => {}}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "▶" }));
    fireEvent.click(screen.getByTitle("Back 10s"));
    fireEvent.change(screen.getByRole("combobox"), { target: { value: "80" } });
    fireEvent.change(screen.getAllByRole("slider")[1], { target: { value: "0.6" } });
    fireEvent.change(screen.getAllByRole("slider")[0], { target: { value: "30" } });

    expect(togglePlay).toHaveBeenCalledTimes(1);
    expect(seekRelative).toHaveBeenCalledWith(-10);
    expect(setPlaybackRate).toHaveBeenCalledWith(0.8);
    expect(setVolume).toHaveBeenCalledWith(0.6);
    expect(seek).toHaveBeenCalledWith(30);
  });

  it("fails loudly when a required transport handler is missing", () => {
    expect(() => {
      render(
      <TransportBar
        currentTime={15}
        duration={120}
        playing={false}
        volume={1}
        playbackRate={1}
        timeNoteMarkers={[]}
        loopActive={false}
        togglePlay={undefined as never}
          seek={() => {}}
          onSeekDragStart={() => {}}
          onSeekDragEnd={() => {}}
          seekRelative={() => {}}
          onNoteLaneClick={() => {}}
          onNoteMarkerClick={() => {}}
          setVolume={() => {}}
          setPlaybackRate={() => {}}
          onClearLoop={() => {}}
        />,
      );
    }).toThrow("togglePlay");
  });
});
