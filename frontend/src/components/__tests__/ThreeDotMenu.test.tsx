import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ThreeDotMenu } from "../ThreeDotMenu";

describe("ThreeDotMenu", () => {
  it("renders a ⋮ trigger button", () => {
    render(<ThreeDotMenu items={[]} />);
    expect(screen.getByRole("button", { name: "More options" })).toBeTruthy();
  });

  it("shows menu items on click", () => {
    render(
      <ThreeDotMenu
        items={[{ label: "Rename", onClick: vi.fn() }]}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "More options" }));
    expect(screen.getByRole("menuitem", { name: "Rename" })).toBeTruthy();
  });

  it("calls onClick and closes menu when item clicked", () => {
    const handler = vi.fn();
    render(
      <ThreeDotMenu
        items={[{ label: "Archive", onClick: handler }]}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "More options" }));
    fireEvent.click(screen.getByRole("menuitem", { name: "Archive" }));
    expect(handler).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole("menuitem")).toBeNull();
  });

  it("closes on Escape key", () => {
    render(
      <ThreeDotMenu items={[{ label: "Rename", onClick: vi.fn() }]} />,
    );
    fireEvent.click(screen.getByRole("button", { name: "More options" }));
    expect(screen.getByRole("menuitem")).toBeTruthy();
    fireEvent.keyDown(document, { key: "Escape" });
    expect(screen.queryByRole("menuitem")).toBeNull();
  });
});
