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
  ready: { bg: "rgba(107, 114, 52, 0.2)", text: "#a3b236" },
  processing: { bg: "rgba(180, 83, 9, 0.2)", text: "#d97706" },
  uploaded: { bg: "rgba(196, 168, 130, 0.15)", text: "#c4a882" },
  failed: { bg: "rgba(180, 40, 40, 0.2)", text: "#ef4444" },
  needs_review: { bg: "rgba(139, 92, 246, 0.2)", text: "#a78bfa" },
};

const ACTIVITY_ICONS: Record<string, string> = {
  stem_upload: "🎵", comment: "💬", status_change: "✅", song_added: "➕", comment_resolved: "☑️",
};

export function ProjectHomePage({ user, band, project, onSelectProject, onOpenSongs, onBack }: ProjectHomePageProps) {
  return (
    <div className="vinyl-noise min-h-screen" style={{ background: "linear-gradient(160deg, #1a1209 0%, #2d1f0e 40%, #1a1209 100%)" }}>
      {/* Header */}
      <nav className="relative z-10 flex items-center justify-between border-b px-8 py-4" style={{ borderColor: "rgba(196, 168, 130, 0.1)" }}>
        <div className="flex items-center gap-4">
          <button onClick={onBack} className="text-sm transition-colors hover:text-amber-300" style={{ color: "#c4a882" }}>← Bands</button>
          <div className="h-4 w-px" style={{ background: "rgba(196, 168, 130, 0.2)" }} />
          <span className="text-sm font-semibold" style={{ color: "#faf5eb" }}>{band.name}</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-full text-[10px] font-bold text-white" style={{ background: "#b45309" }}>{user.avatar}</div>
          <span className="text-xs" style={{ color: "#c4a882" }}>{user.name}</span>
        </div>
      </nav>

      <div className="relative z-10 mx-auto flex max-w-6xl gap-8 px-8 pt-8">
        {/* Sidebar — project list */}
        <aside className="w-56 shrink-0">
          <h3 className="mb-3 text-xs font-medium uppercase tracking-widest" style={{ color: "#8b7d6b" }}>Projects</h3>
          <div className="space-y-1">
            {band.projects.map((p) => (
              <button key={p.id} onClick={() => onSelectProject(p)}
                className="flex w-full items-center justify-between rounded-lg px-3 py-2.5 text-left text-sm transition-colors"
                style={{ background: p.id === project.id ? "rgba(180, 83, 9, 0.15)" : "transparent", color: p.id === project.id ? "#d97706" : "#c4a882" }}>
                <span>{p.name}</span>
                {p.unreadCount > 0 && (
                  <span className="flex h-5 min-w-5 items-center justify-center rounded-full px-1.5 text-[10px] font-bold text-white" style={{ background: "#b45309" }}>
                    {p.unreadCount}
                  </span>
                )}
              </button>
            ))}
          </div>

          {/* Band members */}
          <h3 className="mb-3 mt-8 text-xs font-medium uppercase tracking-widest" style={{ color: "#8b7d6b" }}>Members</h3>
          <div className="space-y-2">
            {band.members.map((m) => (
              <div key={m.id} className="flex items-center gap-2">
                <div className="relative">
                  <div className="flex h-7 w-7 items-center justify-center rounded-full text-[10px] font-bold text-white" style={{ background: "#3d2b1f" }}>{m.avatar}</div>
                  {m.isOnline && <div className="absolute -bottom-0.5 -right-0.5 h-2.5 w-2.5 rounded-full border-2" style={{ background: "#6b7234", borderColor: "#1a1209" }} />}
                </div>
                <div>
                  <div className="text-xs font-medium" style={{ color: "#faf5eb" }}>{m.name}</div>
                  <div className="text-[10px]" style={{ color: "#6b5d4e" }}>{m.instrument}</div>
                </div>
              </div>
            ))}
          </div>
        </aside>

        {/* Main content */}
        <main className="flex-1">
          <div className="mb-6 flex items-end justify-between">
            <div>
              <h1 className="text-3xl" style={{ fontFamily: "DM Serif Display, serif", color: "#faf5eb" }}>{project.name}</h1>
              <p className="mt-1 text-sm" style={{ color: "#8b7d6b" }}>{project.description}</p>
            </div>
            <button onClick={onOpenSongs} className="rounded-xl px-6 py-2.5 text-sm font-semibold text-white transition-all hover:brightness-110" style={{ background: "linear-gradient(135deg, #b45309, #92400e)" }}>
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
              <div key={s.label} className="rounded-xl border p-4" style={{ borderColor: "rgba(196, 168, 130, 0.1)", background: "rgba(26, 18, 9, 0.5)" }}>
                <div className="text-2xl font-bold" style={{ fontFamily: "DM Serif Display, serif", color: "#faf5eb" }}>{s.value}</div>
                <div className="text-xs" style={{ color: "#8b7d6b" }}>{s.label}</div>
              </div>
            ))}
          </div>

          {/* Recent activity */}
          <h2 className="mb-4 text-lg" style={{ fontFamily: "DM Serif Display, serif", color: "#faf5eb" }}>Recent Activity</h2>
          <div className="space-y-2">
            {project.recentActivity.map((a) => (
              <div key={a.id} className="flex items-start gap-3 rounded-xl border p-4" style={{ borderColor: "rgba(196, 168, 130, 0.08)", background: "rgba(26, 18, 9, 0.4)" }}>
                <span className="mt-0.5 text-lg">{ACTIVITY_ICONS[a.type] ?? "📌"}</span>
                <div className="flex-1">
                  <div className="text-sm" style={{ color: "#faf5eb" }}>
                    <span className="font-semibold">{a.authorName}</span>{" "}
                    <span style={{ color: "#c4a882" }}>{a.message}</span>
                  </div>
                  {a.songTitle && <div className="mt-0.5 text-xs" style={{ color: "#8b7d6b" }}>in {a.songTitle}</div>}
                </div>
              </div>
            ))}
          </div>

          {/* Song status overview */}
          <h2 className="mb-4 mt-8 text-lg" style={{ fontFamily: "DM Serif Display, serif", color: "#faf5eb" }}>Songs Overview</h2>
          <div className="space-y-2">
            {project.songs.map((s) => {
              const sc = STATUS_COLORS[s.status] ?? STATUS_COLORS.uploaded;
              return (
                <div key={s.id} className="flex items-center gap-4 rounded-xl border p-4" style={{ borderColor: "rgba(196, 168, 130, 0.08)", background: "rgba(26, 18, 9, 0.4)" }}>
                  <div className="flex-1">
                    <div className="text-sm font-semibold" style={{ color: "#faf5eb" }}>{s.title}</div>
                    <div className="text-xs" style={{ color: "#8b7d6b" }}>{s.artist} · {s.key} · {s.tempo} BPM</div>
                  </div>
                  <span className="rounded-full px-3 py-1 text-xs font-medium" style={{ background: sc.bg, color: sc.text }}>{s.status}</span>
                  {s.stems.filter((st) => !st.isArchived).length > 0 && <span className="text-xs" style={{ color: "#8b7d6b" }}>{s.stems.filter((st) => !st.isArchived).length} stems</span>}
                  {s.notes.length > 0 && <span className="text-xs" style={{ color: "#8b7d6b" }}>{s.notes.filter((n) => !n.resolved).length} open comments</span>}
                </div>
              );
            })}
          </div>
        </main>
      </div>
    </div>
  );
}
