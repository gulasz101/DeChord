import { fireEvent, render, screen } from "@testing-library/react";
import "@testing-library/jest-dom";
import { describe, expect, it, vi } from "vitest";
import { TimelineCommentModal } from "../TimelineCommentModal";
import type { SongNote } from "../../lib/types";

const baseNote: SongNote = {
  id: 1,
  type: "time",
  timestampSec: 90,
  chordIndex: null,
  text: "Great riff here",
  toastDurationSec: 4.0,
  authorName: "Alice",
  authorAvatar: null,
  userId: 7,
  resolved: false,
  parentId: null,
  createdAt: "",
  updatedAt: "",
};

describe("TimelineCommentModal — create mode", () => {
  it("renders with timestamp badge and empty textarea", () => {
    render(
      <TimelineCommentModal
        mode="create"
        timestampSec={90}
        defaultDurationSec={4.5}
        onSave={vi.fn()}
        onClose={vi.fn()}
      />,
    );
    expect(screen.getByText(/@ 1:30/)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/add a comment/i)).toHaveValue("");
    expect(screen.getByLabelText(/show for/i)).toHaveValue(4.5);
  });

  it("calls onSave with text and duration when form is submitted", () => {
    const onSave = vi.fn();
    render(
      <TimelineCommentModal
        mode="create"
        timestampSec={90}
        defaultDurationSec={4.5}
        onSave={onSave}
        onClose={vi.fn()}
      />,
    );
    fireEvent.change(screen.getByPlaceholderText(/add a comment/i), { target: { value: "Nice chord" } });
    fireEvent.change(screen.getByLabelText(/show for/i), { target: { value: "6" } });
    fireEvent.click(screen.getByRole("button", { name: /save/i }));
    expect(onSave).toHaveBeenCalledWith({ text: "Nice chord", toastDurationSec: 6 });
  });

  it("does not call onSave with empty text", () => {
    const onSave = vi.fn();
    render(
      <TimelineCommentModal mode="create" timestampSec={0} defaultDurationSec={4} onSave={onSave} onClose={vi.fn()} />,
    );
    fireEvent.click(screen.getByRole("button", { name: /save/i }));
    expect(onSave).not.toHaveBeenCalled();
  });
});

describe("TimelineCommentModal — edit mode", () => {
  it("pre-fills text and duration from existing note", () => {
    render(
      <TimelineCommentModal
        mode="edit"
        timestampSec={90}
        defaultDurationSec={4}
        note={baseNote}
        onSave={vi.fn()}
        onDelete={vi.fn()}
        onClose={vi.fn()}
      />,
    );
    expect(screen.getByDisplayValue("Great riff here")).toBeInTheDocument();
    expect(screen.getByLabelText(/show for/i)).toHaveValue(4);
  });

  it("shows a Delete button in edit mode", () => {
    render(
      <TimelineCommentModal
        mode="edit"
        timestampSec={90}
        defaultDurationSec={4}
        note={baseNote}
        onSave={vi.fn()}
        onDelete={vi.fn()}
        onClose={vi.fn()}
      />,
    );
    expect(screen.getByRole("button", { name: /delete/i })).toBeInTheDocument();
  });

  it("calls onDelete when Delete is confirmed", () => {
    const onDelete = vi.fn();
    render(
      <TimelineCommentModal
        mode="edit"
        timestampSec={90}
        defaultDurationSec={4}
        note={baseNote}
        onSave={vi.fn()}
        onDelete={onDelete}
        onClose={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /delete/i }));
    // Confirmation step
    fireEvent.click(screen.getByRole("button", { name: /confirm/i }));
    expect(onDelete).toHaveBeenCalledWith(1);
  });
});

describe("TimelineCommentModal — reply mode", () => {
  it("shows parent comment preview, hides duration field, and calls onReply on submit", () => {
    const onReply = vi.fn();
    render(
      <TimelineCommentModal
        mode="reply"
        timestampSec={90}
        defaultDurationSec={4}
        note={baseNote}
        onSave={vi.fn()}
        onReply={onReply}
        onClose={vi.fn()}
      />,
    );
    expect(screen.getByText(/Great riff here/)).toBeInTheDocument(); // parent preview
    expect(screen.queryByLabelText(/show for/i)).not.toBeInTheDocument(); // no duration
    expect(screen.getByRole("button", { name: /reply/i })).toBeInTheDocument();
    // Submit
    fireEvent.change(screen.getByPlaceholderText(/add a comment/i), { target: { value: "Good point" } });
    fireEvent.click(screen.getByRole("button", { name: /reply/i }));
    expect(onReply).toHaveBeenCalledWith("Good point");
  });
});