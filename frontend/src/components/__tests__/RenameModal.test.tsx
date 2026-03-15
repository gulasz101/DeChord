import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { RenameModal } from "../RenameModal";

describe("RenameModal", () => {
  it("renders with current name pre-filled", () => {
    render(
      <RenameModal
        label="Band Name"
        currentName="My Band"
        onSave={vi.fn()}
        onClose={vi.fn()}
      />,
    );
    expect((screen.getByRole("textbox") as HTMLInputElement).value).toBe("My Band");
  });

  it("calls onSave with new name when Save is clicked", async () => {
    const onSave = vi.fn().mockResolvedValue(undefined);
    render(
      <RenameModal
        label="Band Name"
        currentName="My Band"
        onSave={onSave}
        onClose={vi.fn()}
      />,
    );
    fireEvent.change(screen.getByRole("textbox"), { target: { value: "New Band" } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => {
      expect(onSave).toHaveBeenCalledWith("New Band");
    });
  });

  it("calls onClose when Cancel is clicked", () => {
    const onClose = vi.fn();
    render(
      <RenameModal
        label="Band Name"
        currentName="My Band"
        onSave={vi.fn()}
        onClose={onClose}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("shows original filename when provided", () => {
    render(
      <RenameModal
        label="Song Title"
        currentName="My Song"
        originalFilename="original-file.mp3"
        onSave={vi.fn()}
        onClose={vi.fn()}
      />,
    );
    expect(screen.getByText(/original filename/i)).toBeTruthy();
    expect(screen.getByText("original-file.mp3")).toBeTruthy();
  });

  it("closes on Escape key", () => {
    const onClose = vi.fn();
    render(
      <RenameModal
        label="Band Name"
        currentName="My Band"
        onSave={vi.fn()}
        onClose={onClose}
      />,
    );
    fireEvent.keyDown(screen.getByRole("textbox"), { key: "Escape" });
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("closes without saving when name is unchanged", () => {
    const onSave = vi.fn();
    const onClose = vi.fn();
    render(
      <RenameModal
        label="Band Name"
        currentName="My Band"
        onSave={onSave}
        onClose={onClose}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(onSave).not.toHaveBeenCalled();
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
