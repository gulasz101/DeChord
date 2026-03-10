import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { NoteEditorModal } from "../NoteEditorModal";

describe("NoteEditorModal", () => {
  it("resets draft values when reopened", () => {
    const onClose = vi.fn();
    const onSave = vi.fn().mockResolvedValue(undefined);
    const { rerender } = render(
      <NoteEditorModal
        open={true}
        mode="time"
        title="Edit Note"
        initialText="Initial note"
        initialToastDurationSec={2}
        onClose={onClose}
        onSave={onSave}
      />,
    );

    fireEvent.change(screen.getByPlaceholderText("Add your reminder..."), { target: { value: "Local draft" } });
    fireEvent.change(screen.getByDisplayValue("2"), { target: { value: "4.2" } });

    rerender(
      <NoteEditorModal
        open={false}
        mode="time"
        title="Edit Note"
        initialText="Initial note"
        initialToastDurationSec={2}
        onClose={onClose}
        onSave={onSave}
      />,
    );
    rerender(
      <NoteEditorModal
        open={true}
        mode="time"
        title="Edit Note"
        initialText="Server value"
        initialToastDurationSec={3.5}
        onClose={onClose}
        onSave={onSave}
      />,
    );

    expect((screen.getByPlaceholderText("Add your reminder...") as HTMLTextAreaElement).value).toBe("Server value");
    expect(screen.getByDisplayValue("3.5")).toBeTruthy();
  });
});
