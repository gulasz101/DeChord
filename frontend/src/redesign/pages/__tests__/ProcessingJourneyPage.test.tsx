import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ProcessingJourneyPage } from "../ProcessingJourneyPage";
import type { Band, Project } from "../../lib/types";

const project: Project = {
  id: "20",
  name: "Default Project",
  description: "",
  songs: [],
  recentActivity: [],
  unreadCount: 0,
};

const band: Band = {
  id: "10",
  name: "Default Band",
  avatarColor: "#7c3aed",
  members: [],
  projects: [project],
};

describe("ProcessingJourneyPage", () => {
  it("renders an honest processing timeline with visible stage history", () => {
    render(
      <ProcessingJourneyPage
        band={band}
        project={project}
        journey={{
          songTitle: "La grenade",
          uploadFilename: "Clara Luciani - La grenade.mp3",
          status: "processing",
          stage: "splitting_stems",
          progressPct: 45,
          stageHistory: ["queued", "analyzing_chords", "splitting_stems"],
          message: "Splitting stems...",
          error: null,
        }}
        onBack={() => {}}
        onRetryRefresh={() => {}}
      />,
    );

    expect(screen.getByRole("heading", { name: "La grenade" })).toBeTruthy();
    expect(screen.getByText("Clara Luciani - La grenade.mp3")).toBeTruthy();
    expect(screen.getByText("Splitting stems...")).toBeTruthy();
    expect(screen.getByText("45% complete")).toBeTruthy();
    expect(screen.getByText("queued")).toBeTruthy();
    expect(screen.getByText("analyzing_chords")).toBeTruthy();
    expect(screen.getAllByText("splitting_stems").length).toBeGreaterThan(0);
    expect(screen.getByText("Current stage")).toBeTruthy();
  });

  it("renders failure recovery actions when the journey errors", () => {
    const onBack = vi.fn();
    const onRetryRefresh = vi.fn();

    render(
      <ProcessingJourneyPage
        band={band}
        project={project}
        journey={{
          songTitle: "La grenade",
          uploadFilename: "Clara Luciani - La grenade.mp3",
          status: "error",
          stage: "error",
          progressPct: 100,
          stageHistory: ["queued", "splitting_stems", "error"],
          message: "Processing failed",
          error: "Job not found after reset",
        }}
        onBack={onBack}
        onRetryRefresh={onRetryRefresh}
      />,
    );

    expect(screen.getByText("Job not found after reset")).toBeTruthy();

    const backToLibraryButtons = screen.getAllByRole("button", { name: /Back to Library/i });
    const retryRefreshAction = screen.getByRole("button", { name: "Retry Refresh" });

    expect(backToLibraryButtons).toHaveLength(1);
    const [backToLibraryAction] = backToLibraryButtons;

    fireEvent.click(backToLibraryAction);
    fireEvent.click(retryRefreshAction);

    expect(onBack).toHaveBeenCalledTimes(1);
    expect(onRetryRefresh).toHaveBeenCalledTimes(1);
  });
});
