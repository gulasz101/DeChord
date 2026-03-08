import type { Band, Project, User } from "../lib/types";

interface ProjectHomePageProps {
  user: User;
  band: Band;
  project: Project;
  onSelectProject: (p: Project) => void;
  onOpenSongs: () => void;
  onBack: () => void;
}

const STATUS_COLORS: Record<string, { bg: string; text: string }> = {
  ready: { bg: "rgba(0, 255, 65, 0.1)", text: "#00ff41" },
  processing: { bg: "rgba(0, 229, 255, 0.1)", text: "#00e5ff" },
  uploaded: { bg: "rgba(58, 58, 58, 0.3)", text: "#d0d0d0" },
  failed: { bg: "rgba(255, 0, 0, 0.15)", text: "#ff4444" },
  needs_review: { bg: "rgba(255, 0, 255, 0.1)", text: "#ff00ff" },
};

const ACTIVITY_ICONS: Record<string, string> = {
  stem_upload: "[STEM]", comment: "[MSG]", status_change: "[OK]", song_added: "[ADD]", comment_resolved: "[RES]",
};

export function ProjectHomePage({ user, band, project, onSelectProject, onOpenSongs, onBack }: ProjectHomePageProps) {
  return (
    <div className="scanlines min-h-screen" style={{ background: "#0a0a0a" }}>
      {/* Header */}
      <nav className="relative z-10 flex items-center justify-between border-b px-8 py-4" style={{ borderColor: "rgba(0, 255, 65, 0.1)" }}>
        <div className="flex items-center gap-4">
          <button onClick={onBack} className="font-mono text-sm transition-colors hover:text-green-300" style={{ color: "#00ff41" }}>&lt;-- bands</button>
          <div className="h-4 w-px" style={{ background: "rgba(0, 255, 65, 0.2)" }} />
          <span className="text-sm font-semibold" style={{ color: "#e8e8e8" }}>{band.name}</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center border text-[10px] font-bold" style={{ borderColor: "#00ff41", color: "#00ff41" }}>{user.avatar}</div>
          <span className="font-mono text-xs" style={{ color: "#00e5ff" }}>{user.name}</span>
        </div>
      </nav>

      <div className="relative z-10 mx-auto flex max-w-6xl gap-8 px-8 pt-8">
        {/* Sidebar — project list */}
        <aside className="w-56 shrink-0">
          <h3 className="mb-3 font-mono text-xs font-medium uppercase tracking-widest" style={{ color: "#3a3a3a" }}>// projects</h3>
          <div className="space-y-1">
            {band.projects.map((p) => (
              <button key={p.id} onClick={() => onSelectProject(p)}
                className="flex w-full items-center justify-between px-3 py-2.5 text-left font-mono text-sm transition-colors"
                style={{ background: p.id === project.id ? "rgba(0, 255, 65, 0.08)" : "transparent", color: p.id === project.id ? "#00ff41" : "#3a3a3a" }}>
                <span>{p.id === project.id ? "> " : "  "}{p.name}</span>
                {p.unreadCount > 0 && (
                  <span className="flex h-5 min-w-5 items-center justify-center px-1.5 font-mono text-[10px] font-bold" style={{ background: "rgba(0, 255, 65, 0.15)", color: "#00ff41" }}>
                    {p.unreadCount}
                  </span>
                )}
              </button>
            ))}
          </div>

          {/* Band members */}
          <h3 className="mb-3 mt-8 font-mono text-xs font-medium uppercase tracking-widest" style={{ color: "#3a3a3a" }}>// members</h3>
          <div className="space-y-2">
            {band.members.map((m) => (
              <div key={m.id} className="flex items-center gap-2">
                <div className="relative">
                  <div className="flex h-7 w-7 items-center justify-center border text-[10px] font-bold" style={{ borderColor: m.isOnline ? "#00ff41" : "#3a3a3a", color: m.isOnline ? "#00ff41" : "#3a3a3a" }}>{m.avatar}</div>
                  {m.isOnline && <div className="absolute -bottom-0.5 -right-0.5 h-2.5 w-2.5 border-2" style={{ background: "#00ff41", borderColor: "#0a0a0a" }} />}
                </div>
                <div>
                  <div className="text-xs font-medium" style={{ color: "#e8e8e8" }}>{m.name}</div>
                  <div className="font-mono text-[10px]" style={{ color: "#3a3a3a" }}>{m.instrument}</div>
                </div>
              </div>
            ))}
          </div>
        </aside>

        {/* Main content */}
        <main className="flex-1">
          <div className="mb-6 flex items-end justify-between">
            <div>
              <h1 className="text-3xl" style={{ fontFamily: "Outfit, sans-serif", color: "#e8e8e8" }}>{project.name}</h1>
              <p className="mt-1 font-mono text-sm" style={{ color: "#3a3a3a" }}>{project.description}</p>
            </div>
            <button onClick={onOpenSongs} className="border-2 px-6 py-2.5 font-mono text-sm font-semibold transition-all hover:bg-green-900/20" style={{ borderColor: "#00ff41", color: "#00ff41", background: "rgba(0, 255, 65, 0.05)" }}>
              song-library &gt;
            </button>
          </div>

          {/* Stats row */}
          <div className="mb-8 grid grid-cols-4 gap-3">
            {[
              { label: "songs", value: project.songs.length },
              { label: "ready", value: project.songs.filter((s) => s.status === "ready").length },
              { label: "processing", value: project.songs.filter((s) => s.status === "processing").length },
              { label: "unread", value: project.unreadCount },
            ].map((s) => (
              <div key={s.label} className="border p-4" style={{ borderColor: "rgba(0, 255, 65, 0.1)", background: "rgba(0, 255, 65, 0.02)" }}>
                <div className="font-mono text-2xl font-bold glow-green" style={{ color: "#00ff41" }}>{s.value}</div>
                <div className="font-mono text-xs" style={{ color: "#3a3a3a" }}>{s.label}</div>
              </div>
            ))}
          </div>

          {/* Recent activity */}
          <h2 className="mb-4 text-lg" style={{ fontFamily: "Outfit, sans-serif", color: "#e8e8e8" }}>Recent Activity</h2>
          <div className="space-y-2">
            {project.recentActivity.map((a) => (
              <div key={a.id} className="flex items-start gap-3 border p-4" style={{ borderColor: "rgba(0, 255, 65, 0.06)", background: "rgba(0, 255, 65, 0.02)" }}>
                <span className="mt-0.5 font-mono text-xs font-bold" style={{ color: "#00e5ff" }}>{ACTIVITY_ICONS[a.type] ?? "[---]"}</span>
                <div className="flex-1">
                  <div className="font-mono text-sm" style={{ color: "#e8e8e8" }}>
                    <span className="font-semibold" style={{ color: "#00ff41" }}>{a.authorName}</span>{" "}
                    <span style={{ color: "#d0d0d0" }}>{a.message}</span>
                  </div>
                  {a.songTitle && <div className="mt-0.5 font-mono text-xs" style={{ color: "#3a3a3a" }}>in {a.songTitle}</div>}
                </div>
              </div>
            ))}
          </div>

          {/* Song status overview */}
          <h2 className="mb-4 mt-8 text-lg" style={{ fontFamily: "Outfit, sans-serif", color: "#e8e8e8" }}>Songs Overview</h2>
          <div className="space-y-2">
            {project.songs.map((s) => {
              const sc = STATUS_COLORS[s.status] ?? STATUS_COLORS.uploaded;
              return (
                <div key={s.id} className="flex items-center gap-4 border p-4" style={{ borderColor: "rgba(0, 255, 65, 0.06)", background: "rgba(0, 255, 65, 0.02)" }}>
                  <div className="flex-1">
                    <div className="text-sm font-semibold" style={{ color: "#e8e8e8" }}>{s.title}</div>
                    <div className="font-mono text-xs" style={{ color: "#3a3a3a" }}>{s.artist} | {s.key} | {s.tempo} BPM</div>
                  </div>
                  <span className="border px-3 py-1 font-mono text-xs font-medium" style={{ background: sc.bg, color: sc.text, borderColor: sc.text + "33" }}>{s.status}</span>
                  {s.stems.filter((st) => !st.isArchived).length > 0 && <span className="font-mono text-xs" style={{ color: "#3a3a3a" }}>{s.stems.filter((st) => !st.isArchived).length} stems</span>}
                  {s.notes.length > 0 && <span className="font-mono text-xs" style={{ color: "#3a3a3a" }}>{s.notes.filter((n) => !n.resolved).length} open</span>}
                </div>
              );
            })}
          </div>
        </main>
      </div>
    </div>
  );
}
