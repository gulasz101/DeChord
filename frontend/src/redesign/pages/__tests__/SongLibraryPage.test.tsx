import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { SongLibraryPage } from "../SongLibraryPage";
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
  chords: [],
  stems: [],
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

describe("SongLibraryPage", () => {
  it("uploads a selected file with process mode and tab quality", async () => {
    const onUploadSong = vi.fn();

    render(
      <SongLibraryPage
        user={user}
        band={band}
        project={project}
        onSelectSong={() => {}}
        onBack={() => {}}
        onUploadSong={onUploadSong}
      />,
    );

    fireEvent.click(screen.getByText("+ Upload Song"));
    fireEvent.change(screen.getByLabelText("Process Mode"), { target: { value: "analysis_only" } });
    fireEvent.change(screen.getByLabelText("Tab Quality"), { target: { value: "high_accuracy" } });

    const file = new File([new Uint8Array([1, 2, 3])], "demo.mp3", { type: "audio/mpeg" });
    await fireEvent.change(screen.getByLabelText("Upload Song File"), { target: { files: [file] } });

    fireEvent.click(screen.getByRole("button", { name: /start upload/i }));

    expect(onUploadSong).toHaveBeenCalledWith(file, "analysis_only", "high_accuracy");
  });

  it("renders progress, warning, and error states in the upload card", () => {
    render(
      <SongLibraryPage
        user={user}
        band={band}
        project={project}
        onSelectSong={() => {}}
        onBack={() => {}}
        onUploadSong={() => {}}
        uploadLoading
        uploadStatus={{ message: "Splitting stems...", progress_pct: 48, stage_progress_pct: 12 }}
        uploadWarning="Stem splitting failed: lameenc missing"
        uploadError="Upload failed"
      />,
    );

    fireEvent.click(screen.getByText("+ Upload Song"));

    expect(screen.getByText("Splitting stems...")).toBeTruthy();
    expect(screen.getByText(/48% complete/)).toBeTruthy();
    expect(screen.getByText(/Stage 12%/)).toBeTruthy();
    expect(screen.getByText("Stem splitting failed: lameenc missing")).toBeTruthy();
    expect(screen.getByText("Upload failed")).toBeTruthy();
  });
});
