import { render, screen } from "@testing-library/react";
import "@testing-library/jest-dom";
import { describe, expect, it } from "vitest";
import { ToastCueLayer } from "../ToastCueLayer";

const baseToasts = [
  { id: 1, text: "try the bass lower", authorName: "Wojciech" },
  { id: 2, text: "tension resolves to Dm", authorName: "Anna" },
];

describe("ToastCueLayer", () => {
  it("renders all toasts with their text", () => {
    render(<ToastCueLayer toasts={baseToasts} exitingIds={new Set()} />);
    expect(screen.getByText("try the bass lower")).toBeInTheDocument();
    expect(screen.getByText("tension resolves to Dm")).toBeInTheDocument();
  });

  it("renders author names", () => {
    render(<ToastCueLayer toasts={baseToasts} exitingIds={new Set()} />);
    expect(screen.getByText("Wojciech")).toBeInTheDocument();
    expect(screen.getByText("Anna")).toBeInTheDocument();
  });

  it("applies data-testid per toast id", () => {
    render(<ToastCueLayer toasts={baseToasts} exitingIds={new Set()} />);
    expect(screen.getByTestId("toast-1")).toBeInTheDocument();
    expect(screen.getByTestId("toast-2")).toBeInTheDocument();
  });

  it("applies toast-exiting class to toasts in exitingIds", () => {
    render(<ToastCueLayer toasts={baseToasts} exitingIds={new Set([1])} />);
    expect(screen.getByTestId("toast-1").className).toMatch(/toast-exiting/);
    expect(screen.getByTestId("toast-2").className).not.toMatch(/toast-exiting/);
  });

  it("container has pointer-events-none so it never blocks player clicks", () => {
    const { container } = render(
      <ToastCueLayer toasts={baseToasts} exitingIds={new Set()} />
    );
    const wrapper = container.firstChild as HTMLElement;
    expect(wrapper.className).toMatch(/pointer-events-none/);
  });

  it("assigns a deterministic gradient class based on author name", () => {
    render(<ToastCueLayer toasts={[{ id: 1, text: "x", authorName: "Wojciech" }]} exitingIds={new Set()} />);
    // "Wojciech" hash: sum of char codes % 8 — must be stable across renders
    const toast = screen.getByTestId("toast-1");
    // gradient class follows pattern toast-gradient-{0-7}
    expect(toast.className).toMatch(/toast-gradient-\d/);
  });
});
