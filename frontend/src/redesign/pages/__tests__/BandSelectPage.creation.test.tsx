import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { BandSelectPage } from "../BandSelectPage";
import type { Band, User } from "../../lib/types";

const user: User = {
  id: "1",
  name: "Alice",
  email: "alice@example.com",
  instrument: "Bass",
  avatar: "A",
};

const band: Band = {
  id: "1",
  name: "Shredders",
  avatarColor: "#7c3aed",
  projects: [],
  members: [],
};

describe("BandSelectPage — additional band creation", () => {
  it("does NOT render the ghost card when no bands exist", () => {
    render(
      <BandSelectPage user={user} bands={[]} onSelectBand={() => {}} onSignOut={() => {}} />,
    );
    expect(screen.queryByText(/create new band/i)).toBeNull();
  });

  it("renders ghost card when at least one band exists", () => {
    render(
      <BandSelectPage user={user} bands={[band]} onSelectBand={() => {}} onSignOut={() => {}} />,
    );
    expect(screen.getByText(/create new band/i)).toBeTruthy();
  });

  it("clicking the ghost card shows the inline creation form", () => {
    render(
      <BandSelectPage user={user} bands={[band]} onSelectBand={() => {}} onSignOut={() => {}} />,
    );
    fireEvent.click(screen.getByText(/create new band/i));
    expect(screen.getByLabelText("Band Name")).toBeTruthy();
  });

  it("Cancel hides the form and restores the ghost card", () => {
    render(
      <BandSelectPage user={user} bands={[band]} onSelectBand={() => {}} onSignOut={() => {}} />,
    );
    fireEvent.click(screen.getByText(/create new band/i));
    fireEvent.click(screen.getByText(/cancel/i));
    expect(screen.queryByLabelText("Band Name")).toBeNull();
    expect(screen.getByText(/create new band/i)).toBeTruthy();
  });

  it("submitting the form calls onCreateBand with the trimmed name", async () => {
    const onCreateBand = vi.fn().mockResolvedValue(undefined);
    render(
      <BandSelectPage
        user={user}
        bands={[band]}
        onSelectBand={() => {}}
        onSignOut={() => {}}
        onCreateBand={onCreateBand}
      />,
    );
    fireEvent.click(screen.getByText(/create new band/i));
    fireEvent.change(screen.getByLabelText("Band Name"), { target: { value: "  New Band  " } });
    fireEvent.click(screen.getByRole("button", { name: /save band/i }));
    await waitFor(() => expect(onCreateBand).toHaveBeenCalledWith({ name: "New Band" }));
  });

  it("Enter key in the name input submits the form", async () => {
    const onCreateBand = vi.fn().mockResolvedValue(undefined);
    render(
      <BandSelectPage
        user={user}
        bands={[band]}
        onSelectBand={() => {}}
        onSignOut={() => {}}
        onCreateBand={onCreateBand}
      />,
    );
    fireEvent.click(screen.getByText(/create new band/i));
    fireEvent.change(screen.getByLabelText("Band Name"), { target: { value: "New Band" } });
    fireEvent.keyDown(screen.getByLabelText("Band Name"), { key: "Enter" });
    await waitFor(() => expect(onCreateBand).toHaveBeenCalledWith({ name: "New Band" }));
  });

  it("Save Band button is disabled while a save is in flight", () => {
    let resolveCreate!: () => void;
    const onCreateBand = vi.fn().mockReturnValue(
      new Promise<void>((r) => { resolveCreate = r; }),
    );
    render(
      <BandSelectPage
        user={user}
        bands={[band]}
        onSelectBand={() => {}}
        onSignOut={() => {}}
        onCreateBand={onCreateBand}
      />,
    );
    fireEvent.click(screen.getByText(/create new band/i));
    fireEvent.change(screen.getByLabelText("Band Name"), { target: { value: "New Band" } });
    fireEvent.click(screen.getByRole("button", { name: /save band/i }));
    const saveButton = screen.getByRole("button", { name: /save band/i }) as HTMLButtonElement;
    expect(saveButton.disabled).toBe(true);
    resolveCreate();
  });

  it("form stays open when onCreateBand rejects (error silently swallowed)", async () => {
    const onCreateBand = vi.fn().mockRejectedValue(new Error("Network error"));
    render(
      <BandSelectPage
        user={user}
        bands={[band]}
        onSelectBand={() => {}}
        onSignOut={() => {}}
        onCreateBand={onCreateBand}
      />,
    );
    fireEvent.click(screen.getByText(/create new band/i));
    fireEvent.change(screen.getByLabelText("Band Name"), { target: { value: "New Band" } });
    fireEvent.click(screen.getByRole("button", { name: /save band/i }));
    await waitFor(() => expect(onCreateBand).toHaveBeenCalled());
    expect(screen.getByLabelText("Band Name")).toBeTruthy();
  });
});