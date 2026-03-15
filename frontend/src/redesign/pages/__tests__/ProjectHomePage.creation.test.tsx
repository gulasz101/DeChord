import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ProjectHomePage } from "../ProjectHomePage";
import type { Band, Project, User } from "../../lib/types";

const user: User = {
  id: "1",
  name: "Alice",
  email: "alice@example.com",
  instrument: "Bass",
  avatar: "A",
};

const project: Project = {
  id: "9",
  name: "Album Prep",
  description: "First album",
  songs: [],
  recentActivity: [],
  unreadCount: 0,
};

const band: Band = {
  id: "3",
  name: "Shredders",
  members: [],
  projects: [project],
  avatarColor: "#7c3aed",
};

describe("ProjectHomePage — project creation modal", () => {
  it("modal is not visible by default", () => {
    render(
      <ProjectHomePage
        user={user}
        band={band}
        project={project}
        onSelectProject={() => {}}
        onOpenSongs={() => {}}
        onBack={() => {}}
      />,
    );
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("clicking New renders the modal", () => {
    render(
      <ProjectHomePage
        user={user}
        band={band}
        project={project}
        onSelectProject={() => {}}
        onOpenSongs={() => {}}
        onBack={() => {}}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /create new project/i }));
    expect(screen.getByRole("dialog")).toBeTruthy();
    expect(screen.getByLabelText("Project Name")).toBeTruthy();
  });

  it("modal closes on Cancel button click", () => {
    render(
      <ProjectHomePage
        user={user}
        band={band}
        project={project}
        onSelectProject={() => {}}
        onOpenSongs={() => {}}
        onBack={() => {}}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /create new project/i }));
    fireEvent.click(screen.getByRole("button", { name: /cancel/i }));
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("modal closes on Escape key", () => {
    render(
      <ProjectHomePage
        user={user}
        band={band}
        project={project}
        onSelectProject={() => {}}
        onOpenSongs={() => {}}
        onBack={() => {}}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /create new project/i }));
    fireEvent.keyDown(document, { key: "Escape" });
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("modal closes on backdrop click", () => {
    render(
      <ProjectHomePage
        user={user}
        band={band}
        project={project}
        onSelectProject={() => {}}
        onOpenSongs={() => {}}
        onBack={() => {}}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /create new project/i }));
    fireEvent.click(screen.getByRole("dialog"));
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("submitting calls onCreateProject with name and description", async () => {
    const onCreateProject = vi.fn().mockResolvedValue(undefined);
    render(
      <ProjectHomePage
        user={user}
        band={band}
        project={project}
        onSelectProject={() => {}}
        onCreateProject={onCreateProject}
        onOpenSongs={() => {}}
        onBack={() => {}}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /create new project/i }));
    fireEvent.change(screen.getByLabelText("Project Name"), { target: { value: "Live Set" } });
    fireEvent.change(screen.getByLabelText("Project Description"), { target: { value: "Summer tour" } });
    fireEvent.click(screen.getByRole("button", { name: /save project/i }));
    await waitFor(() =>
      expect(onCreateProject).toHaveBeenCalledWith({ name: "Live Set", description: "Summer tour" }),
    );
  });

  it("Save Project button is disabled when name is empty", () => {
    render(
      <ProjectHomePage
        user={user}
        band={band}
        project={project}
        onSelectProject={() => {}}
        onOpenSongs={() => {}}
        onBack={() => {}}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /create new project/i }));
    const saveButton = screen.getByRole("button", { name: /save project/i }) as HTMLButtonElement;
    expect(saveButton.disabled).toBe(true);
  });

  it("Save Project button is disabled while a save is in flight", () => {
    let resolveCreate!: () => void;
    const onCreateProject = vi.fn().mockReturnValue(
      new Promise<void>((r) => { resolveCreate = r; }),
    );
    render(
      <ProjectHomePage
        user={user}
        band={band}
        project={project}
        onSelectProject={() => {}}
        onCreateProject={onCreateProject}
        onOpenSongs={() => {}}
        onBack={() => {}}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /create new project/i }));
    fireEvent.change(screen.getByLabelText("Project Name"), { target: { value: "Live Set" } });
    fireEvent.click(screen.getByRole("button", { name: /save project/i }));
    const saveButton = screen.getByRole("button", { name: /save project/i }) as HTMLButtonElement;
    expect(saveButton.disabled).toBe(true);
    resolveCreate();
  });

  it("modal stays open when onCreateProject rejects (error silently swallowed)", async () => {
    const onCreateProject = vi.fn().mockRejectedValue(new Error("Network error"));
    render(
      <ProjectHomePage
        user={user}
        band={band}
        project={project}
        onSelectProject={() => {}}
        onCreateProject={onCreateProject}
        onOpenSongs={() => {}}
        onBack={() => {}}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /create new project/i }));
    fireEvent.change(screen.getByLabelText("Project Name"), { target: { value: "Live Set" } });
    fireEvent.click(screen.getByRole("button", { name: /save project/i }));
    await waitFor(() => expect(onCreateProject).toHaveBeenCalled());
    expect(screen.getByRole("dialog")).toBeTruthy();
  });
});