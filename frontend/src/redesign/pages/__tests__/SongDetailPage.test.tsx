import { describe, expect, it, vi } from "vitest";
import "@testing-library/jest-dom";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { SongDetailPage } from "../SongDetailPage";
import type { Band, Project, Song, SongNote, User } from "../../lib/types";

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

  const noteParent: SongNote = {
    id: 10, type: "general", timestampSec: null, chordIndex: null,
    text: "Top-level comment", toastDurationSec: null,
    authorName: "Mike R.", authorAvatar: "MR", resolved: false,
    parentId: null, createdAt: "2026-03-01T10:00:00Z", updatedAt: "2026-03-01T10:00:00Z",
  };
  const noteReply: SongNote = {
    id: 11, type: "general", timestampSec: null, chordIndex: null,
    text: "Reply to Mike", toastDurationSec: null,
    authorName: "Jake T.", authorAvatar: "JT", resolved: false,
    parentId: 10, createdAt: "2026-03-01T11:00:00Z", updatedAt: "2026-03-01T11:00:00Z",
  };
  const songWithNotes: Song = { ...song, notes: [noteParent, noteReply] };

  describe("comment form — simplified (no timestamp)", () => {
    it("does not render timestamp input or note type radios", () => {
      render(
        <SongDetailPage
          user={user} band={band} project={project} song={song}
          onOpenPlayer={() => {}} onBack={() => {}}
        />,
      );
      expect(screen.queryByLabelText("Timestamp")).toBeNull();
      expect(screen.queryByLabelText("Time Note")).toBeNull();
      expect(screen.queryByLabelText("Chord Note")).toBeNull();
    });

    it("submits a general note with just the text", async () => {
      const onCreateNote = vi.fn().mockResolvedValue(undefined);
      render(
        <SongDetailPage
          user={user} band={band} project={project} song={song}
          onOpenPlayer={() => {}} onBack={() => {}}
          onCreateNote={onCreateNote}
        />,
      );
      fireEvent.change(screen.getByLabelText("Note Text"), {
        target: { value: "Great groove" },
      });
      fireEvent.click(screen.getByText("Add Comment"));
      await waitFor(() => {
        expect(onCreateNote).toHaveBeenCalledWith({ type: "general", text: "Great groove" });
      });
    });
  });

  describe("comment threading", () => {
    it("renders top-level comments", () => {
      render(
        <SongDetailPage
          user={user} band={band} project={project} song={songWithNotes}
          onOpenPlayer={() => {}} onBack={() => {}}
        />,
      );
      expect(screen.getByText("Top-level comment")).toBeInTheDocument();
    });

    it("renders replies indented under their parent", () => {
      render(
        <SongDetailPage
          user={user} band={band} project={project} song={songWithNotes}
          onOpenPlayer={() => {}} onBack={() => {}}
        />,
      );
      expect(screen.getByText("Reply to Mike")).toBeInTheDocument();
    });

    it("shows Reply button on top-level comments", () => {
      render(
        <SongDetailPage
          user={user} band={band} project={project} song={songWithNotes}
          onOpenPlayer={() => {}} onBack={() => {}}
        />,
      );
      expect(screen.getAllByText("Reply").length).toBeGreaterThan(0);
    });

    it("opens inline reply form on Reply click", () => {
      render(
        <SongDetailPage
          user={user} band={band} project={project} song={songWithNotes}
          onOpenPlayer={() => {}} onBack={() => {}}
        />,
      );
      fireEvent.click(screen.getAllByText("Reply")[0]);
      expect(screen.getByLabelText("Reply Text")).toBeInTheDocument();
    });

    it("calls onCreateReply with parentId and text", async () => {
      const onCreateReply = vi.fn().mockResolvedValue(undefined);
      render(
        <SongDetailPage
          user={user} band={band} project={project} song={songWithNotes}
          onOpenPlayer={() => {}} onBack={() => {}}
          onCreateReply={onCreateReply}
        />,
      );
      fireEvent.click(screen.getAllByText("Reply")[0]);
      fireEvent.change(screen.getByLabelText("Reply Text"), {
        target: { value: "My reply" },
      });
      fireEvent.click(screen.getByText("Post Reply"));
      await waitFor(() => {
        expect(onCreateReply).toHaveBeenCalledWith(10, "My reply");
      });
    });

    it("replies do not show Resolve button", () => {
      render(
        <SongDetailPage
          user={user} band={band} project={project} song={songWithNotes}
          onOpenPlayer={() => {}} onBack={() => {}}
        />,
      );
      expect(screen.getAllByText("Resolve").length).toBe(1);
    });
  });

  it("opens stems generation panel and confirms through callback", async () => {
    const onGenerateStems = vi.fn().mockResolvedValue(undefined);

    render(
      <SongDetailPage
        user={user}
        band={band}
        project={project}
        song={song}
        onOpenPlayer={() => {}}
        onBack={() => {}}
        onGenerateStems={onGenerateStems}
      />,
    );

    fireEvent.click(screen.getByText("Generate Stems"));
    expect(screen.getByText(/regenerates system stems from the original uploaded mix/i)).toBeTruthy();

    fireEvent.click(screen.getByText("Confirm Stem Generation"));
    expect(onGenerateStems).toHaveBeenCalledTimes(1);

    await waitFor(() => {
      expect(screen.getAllByText("Stems regenerated.").length).toBeGreaterThan(0);
    });
  });

  it("defaults bass tab generation to bass stem and submits selected source", async () => {
    const onGenerateBassTab = vi.fn().mockResolvedValue(undefined);

    render(
      <SongDetailPage
        user={user}
        band={band}
        project={project}
        song={{
          ...song,
          stems: [
            ...song.stems,
            {
              id: "guitar-1",
              stemKey: "guitar",
              label: "Guitar",
              uploaderName: "System",
              sourceType: "System",
              description: "stems/30/guitar.wav",
              version: 1,
              isArchived: false,
              createdAt: "2026-03-09",
            },
          ],
        }}
        onOpenPlayer={() => {}}
        onBack={() => {}}
        onGenerateBassTab={onGenerateBassTab}
      />,
    );

    fireEvent.click(screen.getByText("Generate Bass Tab"));
    const bassOption = screen.getByLabelText("Bass");
    expect((bassOption as HTMLInputElement).checked).toBe(true);

    fireEvent.click(screen.getByText("Confirm Tab Generation"));
    expect(onGenerateBassTab).toHaveBeenCalledWith("bass");

    await waitFor(() => {
      expect(screen.getAllByText("Bass tab regenerated from Bass.").length).toBeGreaterThan(0);
    });
  });

  it("shows current stem provenance, uploads a stem, and renders current tab provenance", async () => {
    const onUploadStem = vi.fn().mockResolvedValue(undefined);

    render(
      <SongDetailPage
        user={user}
        band={band}
        project={project}
        song={{
          ...song,
          stems: [
            {
              id: "bass-user",
              stemKey: "bass",
              label: "Bass DI",
              uploaderName: "Groove Bassline",
              sourceType: "User",
              description: "Uploaded 2026-03-10",
              version: 2,
              isArchived: false,
              createdAt: "2026-03-10T10:00:00Z",
            },
          ],
          tab: {
            sourceStemKey: "bass",
            sourceDisplayName: "Bass DI",
            sourceType: "User",
            status: "complete",
            generatorVersion: "v2-rhythm-grid",
            updatedAt: "2026-03-10T10:05:00Z",
          },
        }}
        onOpenPlayer={() => {}}
        onBack={() => {}}
        onUploadStem={onUploadStem}
      />,
    );

    expect(screen.getByText("Bass DI")).toBeTruthy();
    expect(screen.getAllByText("User")[0]).toBeTruthy();
    expect(screen.getByText(/Current bass tab/i)).toBeTruthy();
    expect(screen.getByText(/Generated from Bass DI/i)).toBeTruthy();

    fireEvent.click(screen.getByText("Generate Stems"));
    expect(screen.getByText(/regenerates system stems from the original uploaded mix/i)).toBeTruthy();

    fireEvent.click(screen.getByText("Upload Stem"));
    expect(screen.queryByText(/regenerates system stems from the original uploaded mix/i)).toBeNull();

    fireEvent.change(screen.getByLabelText("Stem Role"), { target: { value: "bass" } });
    fireEvent.change(screen.getByLabelText("Stem File"), {
      target: { files: [new File(["bass"], "bass.wav", { type: "audio/wav" })] },
    });
    fireEvent.click(screen.getByText("Confirm Stem Upload"));

    await waitFor(() => {
      expect(onUploadStem).toHaveBeenCalledWith(
        expect.objectContaining({
          stemKey: "bass",
          file: expect.any(File),
        }),
      );
    });

    await waitFor(() => {
      expect(screen.getAllByText("Stem uploaded.").length).toBeGreaterThan(0);
    });
  });

  it("shows honest tab empty state and action errors when no tab metadata exists", async () => {
    const onUploadStem = vi.fn().mockRejectedValue(new Error("Upload failed"));

    render(
      <SongDetailPage
        user={user}
        band={band}
        project={project}
        song={{
          ...song,
          tab: null,
        }}
        onOpenPlayer={() => {}}
        onBack={() => {}}
        onUploadStem={onUploadStem}
      />,
    );

    expect(screen.getByText(/No generated bass tab yet/i)).toBeTruthy();
    expect(screen.getByText(/Tab provenance will appear after a successful tab generation run/i)).toBeTruthy();

    fireEvent.click(screen.getByText("Upload Stem"));
    fireEvent.change(screen.getByLabelText("Stem Role"), { target: { value: "bass" } });
    fireEvent.change(screen.getByLabelText("Stem File"), {
      target: { files: [new File(["bass"], "bass.wav", { type: "audio/wav" })] },
    });
    fireEvent.click(screen.getByText("Confirm Stem Upload"));

    await waitFor(() => {
      expect(screen.getAllByText("Upload failed").length).toBeGreaterThan(0);
    });
  });

  it("requires reselecting a file after the upload panel is closed and reopened", async () => {
    const onUploadStem = vi.fn().mockResolvedValue(undefined);

    render(
      <SongDetailPage
        user={user}
        band={band}
        project={project}
        song={song}
        onOpenPlayer={() => {}}
        onBack={() => {}}
        onUploadStem={onUploadStem}
      />,
    );

    fireEvent.click(screen.getByText("Upload Stem"));
    fireEvent.change(screen.getByLabelText("Stem File"), {
      target: { files: [new File(["bass"], "bass.wav", { type: "audio/wav" })] },
    });
    fireEvent.click(screen.getByText("Cancel"));

    fireEvent.click(screen.getByText("Upload Stem"));
    fireEvent.click(screen.getByText("Confirm Stem Upload"));

    await waitFor(() => {
      expect(screen.getAllByText("Select a stem file").length).toBeGreaterThan(0);
    });
    expect(onUploadStem).not.toHaveBeenCalled();

    fireEvent.click(screen.getByText("Upload Stem"));
    fireEvent.click(screen.getByText("Upload Stem"));
    fireEvent.click(screen.getByText("Confirm Stem Upload"));

    await waitFor(() => {
      expect(screen.getAllByText("Select a stem file").length).toBeGreaterThan(0);
    });
    expect(onUploadStem).not.toHaveBeenCalled();
  });
});
