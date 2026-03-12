import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ProjectHomePage } from "../ProjectHomePage";
import type { Band, Project, User } from "../../lib/types";

const user: User = {
  id: "1",
  name: "Wojtek",
  email: "wojtek@example.com",
  instrument: "Bass",
  avatar: "W",
};

const project: Project = {
  id: "9",
  name: "Collab",
  description: "Truthful collab state",
  songs: [],
  recentActivity: [],
  unreadCount: 0,
};

const band: Band = {
  id: "3",
  name: "Demo Band",
  members: [],
  projects: [project],
  avatarColor: "#7c3aed",
};

describe("ProjectHomePage collaboration rendering", () => {
  it("renders truthful members, unread badges, activity, and placeholder presence copy", () => {
    render(
      <ProjectHomePage
        user={user}
        band={{
          ...band,
          members: [
            { id: "1", name: "Wojtek", role: "owner", avatar: "W", presenceState: "not_live" },
            { id: "2", name: "Alicja", role: "member", avatar: "A", presenceState: "not_live" },
          ],
          projects: [{ ...project, unreadCount: 2 }],
        }}
        project={{
          ...project,
          unreadCount: 2,
          recentActivity: [
            {
              id: "evt-1",
              type: "comment",
              authorName: "Alicja",
              authorAvatar: "A",
              message: "left a note",
              timestamp: "2026-03-10T10:00:00Z",
              songTitle: "Demo",
            },
          ],
        }}
        onSelectProject={() => {}}
        onOpenSongs={() => {}}
        onBack={() => {}}
      />,
    );

    const ownerRow = screen.getByLabelText("band-member-1");
    const memberRow = screen.getByLabelText("band-member-2");
    const projectButton = screen.getByRole("button", { name: /collab/i });

    expect(within(ownerRow).getByText("Wojtek")).toBeTruthy();
    expect(within(ownerRow).getByText(/^owner$/i)).toBeTruthy();
    expect(within(memberRow).getByText("Alicja")).toBeTruthy();
    expect(within(memberRow).getByText(/^member$/i)).toBeTruthy();
    expect(screen.getByText(/presence updates are not live yet/i)).toBeTruthy();
    expect(within(projectButton).getByLabelText("project-unread-count").textContent).toBe("2");
    expect(screen.getByText(/left a note/i)).toBeTruthy();
    expect(screen.queryByLabelText(/member-live-presence/i)).toBeNull();
  });
});
