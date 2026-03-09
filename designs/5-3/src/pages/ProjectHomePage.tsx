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
  ready: { bg: "rgba(20, 184, 166, 0.15)", text: "#14b8a6" },
  processing: { bg: "rgba(124, 58, 237, 0.15)", text: "#a78bfa" },
  uploaded: { bg: "rgba(192, 192, 192, 0.1)", text: "#c0c0c0" },
  failed: { bg: "rgba(239, 68, 68, 0.15)", text: "#ef4444" },
  needs_review: { bg: "rgba(124, 58, 237, 0.2)", text: "#a78bfa" },
};

const ACTIVITY_ICONS: Record<string, string> = {
  stem_upload: "🎵", comment: "💬", status_change: "✅", song_added: "➕", comment_resolved: "☑️",
};

export function ProjectHomePage({ user, band, project, onSelectProject, onOpenSongs, onBack }: ProjectHomePageProps) {
  return (
    <div className="me-mesh min-h-screen" style={{ background: "linear-gradient(160deg, #0a0e27 0%, #111638 40%, #0a0e27 100%)" }}>
      {/* Header */}
      <nav className="relative z-10 flex items-center justify-between border-b px-8 py-4" style={{ borderColor: "rgba(192, 192, 192, 0.06)" }}>
        <div className="flex items-center gap-4">
          <button onClick={onBack} className="text-sm transition-colors hover:text-purple-300" style={{ color: "#c0c0c0" }}>← Bands</button>
          <div className="h-4 w-px" style={{ background: "rgba(192, 192, 192, 0.12)" }} />
          <span className="text-sm font-semibold" style={{ color: "#e2e2f0" }}>{band.name}</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-full text-[10px] font-bold text-white" style={{ background: "#7c3aed" }}>{user.avatar}</div>
          <span className="text-xs" style={{ color: "#c0c0c0" }}>{user.name}</span>
        </div>
      </nav>

      <div className="relative z-10 mx-auto flex max-w-6xl gap-8 px-8 pt-8">
        {/* Sidebar — project list */}
        <aside className="w-56 shrink-0 border p-4" style={{ borderRadius: "4px", background: "rgba(255, 255, 255, 0.02)", borderColor: "rgba(192, 192, 192, 0.06)", backdropFilter: "blur(12px)" }}>
          <h3 className="mb-3 text-xs font-medium" style={{ fontFamily: "Playfair Display, serif", color: "#7a7a90" }}>Projects</h3>
          <div className="space-y-1">
            {band.projects.map((p) => (
              <button key={p.id} onClick={() => onSelectProject(p)}
                className="flex w-full items-center justify-between rounded-lg px-3 py-2.5 text-left text-sm transition-colors"
                style={{ background: p.id === project.id ? "rgba(124, 58, 237, 0.15)" : "transparent", color: p.id === project.id ? "#a78bfa" : "#c0c0c0" }}>
                <span>{p.name}</span>
                {p.unreadCount > 0 && (
                  <span className="flex h-5 min-w-5 items-center justify-center rounded-full px-1.5 text-[10px] font-bold text-white" style={{ background: "#7c3aed" }}>
                    {p.unreadCount}
                  </span>
                )}
              </button>
            ))}
          </div>

          {/* Band members */}
          <h3 className="mb-3 mt-8 text-xs font-medium" style={{ fontFamily: "Playfair Display, serif", color: "#7a7a90" }}>Members</h3>
          <div className="space-y-2">
            {band.members.map((m) => (
              <div key={m.id} className="flex items-center gap-2">
                <div className="relative">
                  <div className="flex h-7 w-7 items-center justify-center rounded-full text-[10px] font-bold text-white" style={{ background: "#1e1e3a" }}>{m.avatar}</div>
                  {m.isOnline && <div className="absolute -bottom-0.5 -right-0.5 h-2.5 w-2.5 rounded-full border-2" style={{ background: "#14b8a6", borderColor: "#0a0e27" }} />}
                </div>
                <div>
                  <div className="text-xs font-medium" style={{ color: "#e2e2f0" }}>{m.name}</div>
                  <div className="text-[10px]" style={{ color: "#5a5a6e" }}>{m.instrument}</div>
                </div>
              </div>
            ))}
          </div>
        </aside>

        {/* Main content */}
        <main className="flex-1">
          <div className="mb-6 flex items-end justify-between">
            <div>
              <h1 className="text-3xl" style={{ fontFamily: "Playfair Display, serif", color: "#e2e2f0" }}>{project.name}</h1>
              <p className="mt-1 text-sm" style={{ color: "#7a7a90" }}>{project.description}</p>
            </div>
            <button onClick={onOpenSongs} className="px-6 py-2.5 text-sm font-semibold text-white transition-all hover:brightness-110 hover:shadow-purple-500/20" style={{ borderRadius: "3px", background: "linear-gradient(135deg, #7c3aed, #5b21b6)" }}>
              Song Library →
            </button>
          </div>

          {/* Stats row */}
          <div className="mb-8 grid grid-cols-4 gap-3">
            {[
              { label: "Songs", value: project.songs.length },
              { label: "Ready", value: project.songs.filter((s) => s.status === "ready").length },
              { label: "Processing", value: project.songs.filter((s) => s.status === "processing").length },
              { label: "Unread", value: project.unreadCount },
            ].map((s) => (
              <div key={s.label} className="border p-4" style={{ borderRadius: "3px", borderColor: "rgba(192, 192, 192, 0.06)", background: "rgba(255, 255, 255, 0.02)" }}>
                <div className="text-2xl font-bold" style={{ fontFamily: "Playfair Display, serif", color: "transparent", backgroundImage: "linear-gradient(135deg, #7c3aed, #14b8a6)", backgroundClip: "text", WebkitBackgroundClip: "text" }}>{s.value}</div>
                <div className="text-xs" style={{ color: "#7a7a90" }}>{s.label}</div>
              </div>
            ))}
          </div>

          {/* Recent activity */}
          <h2 className="mb-4 text-lg" style={{ fontFamily: "Playfair Display, serif", color: "#e2e2f0" }}>Recent Activity</h2>
          <div className="space-y-2">
            {project.recentActivity.map((a) => (
              <div key={a.id} className="flex items-start gap-3 border-l-2 border p-4" style={{ borderRadius: "3px", borderColor: "rgba(192, 192, 192, 0.05)", borderLeftColor: "rgba(124, 58, 237, 0.4)", background: "rgba(255, 255, 255, 0.02)" }}>
                <span className="mt-0.5 text-lg">{ACTIVITY_ICONS[a.type] ?? "📌"}</span>
                <div className="flex-1">
                  <div className="text-sm" style={{ color: "#e2e2f0" }}>
                    <span className="font-semibold">{a.authorName}</span>{" "}
                    <span style={{ color: "#c0c0c0" }}>{a.message}</span>
                  </div>
                  {a.songTitle && <div className="mt-0.5 text-xs" style={{ color: "#7a7a90" }}>in {a.songTitle}</div>}
                </div>
              </div>
            ))}
          </div>

          {/* Song status overview */}
          <h2 className="mb-4 mt-8 text-lg" style={{ fontFamily: "Playfair Display, serif", color: "#e2e2f0" }}>Songs Overview</h2>
          <div className="space-y-2">
            {project.songs.map((s) => {
              const sc = STATUS_COLORS[s.status] ?? STATUS_COLORS.uploaded;
              return (
                <div key={s.id} className="flex items-center gap-4 border p-4" style={{ borderRadius: "3px", borderColor: "rgba(192, 192, 192, 0.05)", background: "rgba(255, 255, 255, 0.02)" }}>
                  <div className="flex-1">
                    <div className="text-sm font-semibold" style={{ color: "#e2e2f0" }}>{s.title}</div>
                    <div className="text-xs" style={{ color: "#7a7a90" }}>{s.artist} · {s.key} · {s.tempo} BPM</div>
                  </div>
                  <span className="px-3 py-1 text-xs font-medium" style={{ borderRadius: "2px", background: sc.bg, color: sc.text }}>{s.status}</span>
                  {s.stems.filter((st) => !st.isArchived).length > 0 && <span className="text-xs" style={{ color: "#7a7a90" }}>{s.stems.filter((st) => !st.isArchived).length} stems</span>}
                  {s.notes.length > 0 && <span className="text-xs" style={{ color: "#7a7a90" }}>{s.notes.filter((n) => !n.resolved).length} open comments</span>}
                </div>
              );
            })}
          </div>
        </main>
      </div>
    </div>
  );
}
