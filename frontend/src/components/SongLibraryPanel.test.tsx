import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { SongLibraryPanel } from "./SongLibraryPanel";

describe("SongLibraryPanel", () => {
  const defaultProps = {
    songs: [],
    selectedSongId: null,
    projectId: 1,
    onSelect: vi.fn(),
    onUpload: vi.fn(),
    onSongsChange: vi.fn(),
  };

  it("opens file picker when Upload button is clicked", async () => {
    render(<SongLibraryPanel {...defaultProps} />);
    const uploadBtn = screen.getByText("Upload");
    // Find the hidden file input in the component
    const fileInput = document.querySelector(
      "input[type='file']",
    ) as HTMLInputElement;
    const clickSpy = vi.spyOn(fileInput, "click");
    fireEvent.click(uploadBtn);
    expect(clickSpy).toHaveBeenCalled();
  });
});
