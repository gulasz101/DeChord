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
      type: "general",
      chordIndex: null,
      timestampSec: null,
      text: "Lock verse entry",
      toastDurationSec: null,
      authorName: "Wojtek",
      authorAvatar: "WG",
      resolved: false,
      parentId: null,
      createdAt: "2026-03-10T10:00:00Z",
      updatedAt: "2026-03-10T10:00:00Z",
    },
    {
      id: 12,
      type: "general",
      chordIndex: null,
      timestampSec: null,
      text: "Old resolved note",
      toastDurationSec: null,
      authorName: "Wojtek",
      authorAvatar: "WG",
      resolved: true,
      parentId: null,
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
  it("creates general comments, replies, and handles note mutations from song detail", async () => {
    const onCreateNote = vi.fn().mockResolvedValue(undefined);
    const onCreateReply = vi.fn().mockResolvedValue(undefined);
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
        onCreateReply={onCreateReply}
        onEditNote={onEditNote}
        onResolveNote={onResolveNote}
        onDeleteNote={onDeleteNote}
      />,
    );

    expect(screen.getByText("Lock verse entry")).toBeTruthy();
    expect(screen.queryByText("Old resolved note")).toBeNull();

    fireEvent.change(screen.getByLabelText(/note text/i), { target: { value: "Bass pickup is late" } });
    fireEvent.click(screen.getByRole("button", { name: /add comment/i }));

    await waitFor(() => {
      expect(onCreateNote).toHaveBeenCalledWith({
        type: "general",
        text: "Bass pickup is late",
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

  it("creates replies to existing comments", async () => {
    const onCreateReply = vi.fn().mockResolvedValue(undefined);

    render(
      <SongDetailPage
        user={user}
        band={band}
        project={project}
        song={baseSong}
        onOpenPlayer={() => {}}
        onBack={() => {}}
        onCreateReply={onCreateReply}
      />,
    );

    expect(screen.getByText("Lock verse entry")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: /reply/i }));

    const replyInput = screen.getByLabelText(/reply text/i);
    fireEvent.change(replyInput, { target: { value: "My reply" } });
    fireEvent.click(screen.getByRole("button", { name: /post reply/i }));

    await waitFor(() => {
      expect(onCreateReply).toHaveBeenCalledWith(11, "My reply");
    });
  });

  it("reopens a resolved note from the resolved section", async () => {
    const onResolveNote = vi.fn().mockResolvedValue(undefined);

    const songWithResolved: Song = {
      ...baseSong,
      notes: [
        {
          id: 12,
          type: "general",
          chordIndex: null,
          timestampSec: null,
          text: "Old resolved note",
          toastDurationSec: null,
          authorName: "Wojtek",
          authorAvatar: "WG",
          resolved: true,
          createdAt: "2026-03-10T09:00:00Z",
          updatedAt: "2026-03-10T09:05:00Z",
        },
      ],
    };

    render(
      <SongDetailPage
        user={user}
        band={band}
        project={project}
        song={songWithResolved}
        onOpenPlayer={() => {}}
        onBack={() => {}}
        onResolveNote={onResolveNote}
      />,
    );

    expect(screen.queryByText("Old resolved note")).toBeNull();

    fireEvent.click(screen.getByText(/show resolved/i));
    expect(screen.getByText("Old resolved note")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: /reopen note 12/i }));
    await waitFor(() => {
      expect(onResolveNote).toHaveBeenCalledWith(12, false);
    });
  });
});
