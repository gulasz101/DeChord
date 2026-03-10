import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { SongDetailPage } from "../SongDetailPage";
import type { Band, Project, Song, User } from "../../lib/types";

const user: User = {
  id: "u1",
  name: "Guest Musician",
  email: "guest@dechord.local",
  instrument: "Bass",
  avatar: "GM",
};

const song: Song = {
  id: "30",
  title: "The Trooper",
  artist: "Unknown Artist",
  key: "Em",
  tempo: 160,
  duration: 48,
  status: "ready",
  chords: [{ start: 0, end: 2, label: "Em" }],
  stems: [
    {
      id: "bass-1",
      stemKey: "bass",
      label: "Bass",
      uploaderName: "System",
      sourceType: "System",
      description: "stems/30/bass.wav",
      version: 1,
      isArchived: false,
      createdAt: "2026-03-09",
    },
  ],
  notes: [],
  updatedAt: "2026-03-09",
};

const project: Project = {
  id: "20",
  name: "Default Project",
  description: "",
  songs: [song],
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

describe("SongDetailPage", () => {
  it("wires per-stem and all-stems download actions", () => {
    const onDownloadStem = vi.fn();
    const onDownloadAllStems = vi.fn();

    render(
      <SongDetailPage
        user={user}
        band={band}
        project={project}
        song={song}
        onOpenPlayer={() => {}}
        onBack={() => {}}
        onDownloadStem={onDownloadStem}
        onDownloadAllStems={onDownloadAllStems}
      />,
    );

    const downloadButtons = screen.getAllByText("Download");
    fireEvent.click(downloadButtons[0]);
    expect(onDownloadStem).toHaveBeenCalledWith("bass");

    fireEvent.click(screen.getByText("Download All Stems"));
    expect(onDownloadAllStems).toHaveBeenCalledTimes(1);
  });
});
