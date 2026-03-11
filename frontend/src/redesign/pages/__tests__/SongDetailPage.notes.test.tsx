import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { SongDetailPage } from "../SongDetailPage";
import type { Band, Project, Song, User } from "../../lib/types";

const user: User = {
  id: "u1",
  name: "Guest Musician",
  email: "guest@dechord.local",
  instrument: "Bass",
  avatar: "GM",
};

const baseSong: Song = {
  id: "30",
  title: "The Trooper",
  artist: "Unknown Artist",
  key: "Em",
  tempo: 160,
  duration: 120,
  status: "ready",
  chords: [
    { start: 0, end: 2, label: "Em" },
    { start: 2, end: 4, label: "G" },
  ],
  stems: [],
  notes: [
    {
      id: 11,
      type: "chord",
      chordIndex: 0,
      timestampSec: null,
      text: "Lock verse entry",
      toastDurationSec: null,
      authorName: "Wojtek",
      authorAvatar: "WG",
      resolved: false,
      createdAt: "2026-03-10T10:00:00Z",
      updatedAt: "2026-03-10T10:00:00Z",
    },
    {
      id: 12,
      type: "time",
      chordIndex: null,
      timestampSec: 42,
      text: "Old resolved note",
      toastDurationSec: null,
      authorName: "Wojtek",
      authorAvatar: "WG",
      resolved: true,
      createdAt: "2026-03-10T09:00:00Z",
      updatedAt: "2026-03-10T09:05:00Z",
    },
  ],
  updatedAt: "2026-03-10T10:00:00Z",
};

const project: Project = {
  id: "20",
  name: "Default Project",
  description: "",
  songs: [baseSong],
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

describe("SongDetailPage note workflows", () => {
  it("creates manual timestamp notes, chord notes, and note mutations from song detail", async () => {
    const onCreateNote = vi.fn().mockResolvedValue(undefined);
    const onEditNote = vi.fn().mockResolvedValue(undefined);
    const onResolveNote = vi.fn().mockResolvedValue(undefined);
    const onDeleteNote = vi.fn().mockResolvedValue(undefined);

    render(
      <SongDetailPage
        user={user}
        band={band}
        project={project}
        song={baseSong}
        onOpenPlayer={() => {}}
        onBack={() => {}}
        onCreateNote={onCreateNote}
        onEditNote={onEditNote}
        onResolveNote={onResolveNote}
        onDeleteNote={onDeleteNote}
      />,
    );

    expect(screen.getByText("Lock verse entry")).toBeTruthy();
    expect(screen.queryByText("Old resolved note")).toBeNull();

    fireEvent.change(screen.getByLabelText(/note text/i), { target: { value: "Bass pickup is late" } });
    fireEvent.click(screen.getByLabelText(/time note/i));
    fireEvent.change(screen.getByLabelText(/timestamp/i), { target: { value: "01:18" } });
    fireEvent.click(screen.getByRole("button", { name: /add time note/i }));

    await waitFor(() => {
      expect(onCreateNote).toHaveBeenCalledWith({
        type: "time",
        text: "Bass pickup is late",
        timestampSec: 78,
      });
    });

    fireEvent.change(screen.getByLabelText(/note text/i), { target: { value: "Verse entrance is late" } });
    fireEvent.click(screen.getByLabelText(/chord note/i));
    fireEvent.click(screen.getByRole("button", { name: /add chord note/i }));

    await waitFor(() => {
      expect(onCreateNote).toHaveBeenNthCalledWith(2, {
        type: "chord",
        text: "Verse entrance is late",
        chordIndex: 0,
      });
    });

    fireEvent.click(screen.getByRole("button", { name: /edit note 11/i }));
    const editInput = screen.getByLabelText(/edit note text/i);
    fireEvent.change(editInput, { target: { value: "Verse entry is rushing" } });
    fireEvent.click(screen.getByRole("button", { name: /save note 11/i }));

    await waitFor(() => {
      expect(onEditNote).toHaveBeenCalledWith(11, { text: "Verse entry is rushing" });
    });

    fireEvent.click(screen.getByRole("button", { name: /resolve note 11/i }));
    await waitFor(() => {
      expect(onResolveNote).toHaveBeenCalledWith(11, true);
    });

    fireEvent.click(screen.getByText(/show resolved/i));
    expect(screen.getByText("Old resolved note")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: /delete note 11/i }));
    await waitFor(() => {
      expect(onDeleteNote).toHaveBeenCalledWith(11);
    });
  });

  it("accepts numeric seconds and rejects invalid timestamps", async () => {
    const onCreateNote = vi.fn().mockResolvedValue(undefined);

    render(
      <SongDetailPage
        user={user}
        band={band}
        project={project}
        song={{ ...baseSong, notes: [] }}
        onOpenPlayer={() => {}}
        onBack={() => {}}
        onCreateNote={onCreateNote}
      />,
    );

    fireEvent.change(screen.getByLabelText(/note text/i), { target: { value: "Hold this pocket" } });
    fireEvent.click(screen.getByLabelText(/time note/i));
    fireEvent.change(screen.getByLabelText(/timestamp/i), { target: { value: "18.5" } });
    fireEvent.click(screen.getByRole("button", { name: /add time note/i }));

    await waitFor(() => {
      expect(onCreateNote).toHaveBeenCalledWith({
        type: "time",
        text: "Hold this pocket",
        timestampSec: 18.5,
      });
    });

    fireEvent.change(screen.getByLabelText(/note text/i), { target: { value: "Broken timestamp" } });
    fireEvent.change(screen.getByLabelText(/timestamp/i), { target: { value: "1:xx" } });
    fireEvent.click(screen.getByRole("button", { name: /add time note/i }));

    await waitFor(() => {
      expect(onCreateNote).toHaveBeenCalledTimes(1);
      expect(screen.getByText(/enter timestamp as mm:ss or seconds/i)).toBeTruthy();
    });
  });

  it("renders unknown note author metadata neutrally instead of using the current user avatar", () => {
    render(
      <SongDetailPage
        user={user}
        band={band}
        project={project}
        song={{
          ...baseSong,
          notes: [
            {
              id: 21,
              type: "time",
              chordIndex: null,
              timestampSec: 12,
              text: "Unknown author note",
              toastDurationSec: null,
              authorName: null,
              authorAvatar: null,
              resolved: false,
              createdAt: "2026-03-10T11:00:00Z",
              updatedAt: "2026-03-10T11:00:00Z",
            },
          ],
        }}
        onOpenPlayer={() => {}}
        onBack={() => {}}
      />,
    );

    expect(screen.getByText("Unknown")).toBeTruthy();
    expect(screen.getByText("?")).toBeTruthy();
  });

  it("keeps chord-note composer honest when no chords are available", async () => {
    const onCreateNote = vi.fn().mockResolvedValue(undefined);

    render(
      <SongDetailPage
        user={user}
        band={band}
        project={project}
        song={{ ...baseSong, chords: [], notes: [] }}
        onOpenPlayer={() => {}}
        onBack={() => {}}
        onCreateNote={onCreateNote}
      />,
    );

    fireEvent.click(screen.getByLabelText(/chord note/i));

    expect(screen.getByText(/no chords available for chord notes/i)).toBeTruthy();

    fireEvent.change(screen.getByLabelText(/note text/i), { target: { value: "No target chord" } });
    fireEvent.click(screen.getByRole("button", { name: /add chord note/i }));

    await waitFor(() => {
      expect(onCreateNote).not.toHaveBeenCalled();
      expect(screen.getByText(/no chords available for chord note/i)).toBeTruthy();
    });
  });

  it("reopens a resolved note from the resolved section", async () => {
    const onResolveNote = vi.fn().mockResolvedValue(undefined);

    render(
      <SongDetailPage
        user={user}
        band={band}
        project={project}
        song={baseSong}
        onOpenPlayer={() => {}}
        onBack={() => {}}
        onResolveNote={onResolveNote}
      />,
    );

    fireEvent.click(screen.getByText(/show resolved/i));
    fireEvent.click(screen.getByRole("button", { name: /reopen note 12/i }));

    await waitFor(() => {
      expect(onResolveNote).toHaveBeenCalledWith(12, false);
      expect(screen.getByText(/note reopened\./i)).toBeTruthy();
    });
  });
});
