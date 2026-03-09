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
  ready: { bg: "#f0ede6", text: "#2d6a30" },
  processing: { bg: "#f0ede6", text: "#b45309" },
  uploaded: { bg: "#f0ede6", text: "#6b6b6b" },
  failed: { bg: "#f0ede6", text: "#e63946" },
  needs_review: { bg: "#f0ede6", text: "#7c3aed" },
};

const ACTIVITY_ICONS: Record<string, string> = {
  stem_upload: "//", comment: ">>", status_change: "++", song_added: "++", comment_resolved: "ok",
};

export function ProjectHomePage({ user, band, project, onSelectProject, onOpenSongs, onBack }: ProjectHomePageProps) {
  return (
    <div className="min-h-screen" style={{ background: "#f8f6f1" }}>
      {/* Header */}
      <nav className="flex items-center justify-between border-b px-8 py-4" style={{ borderColor: "#e0ddd6" }}>
        <div className="flex items-center gap-4">
          <button onClick={onBack} className="text-sm transition-colors hover:text-[#e63946]" style={{ color: "#6b6b6b" }}>&larr; Bands</button>
          <div className="h-4 w-px" style={{ background: "#e0ddd6" }} />
          <span className="text-sm font-semibold" style={{ color: "#1a1a1a" }}>{band.name}</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-full text-[10px] font-bold text-white" style={{ background: "#1a1a1a" }}>{user.avatar}</div>
          <span className="text-xs" style={{ color: "#6b6b6b" }}>{user.name}</span>
        </div>
      </nav>

      <div className="mx-auto flex max-w-6xl gap-8 px-8 pt-8">
        {/* Sidebar — project list */}
        <aside className="w-56 shrink-0">
          <h3 className="mb-3 text-xs font-semibold uppercase tracking-[0.15em]" style={{ color: "#6b6b6b" }}>Projects</h3>
          <div className="space-y-0 border-t" style={{ borderColor: "#e0ddd6" }}>
            {band.projects.map((p) => (
              <button key={p.id} onClick={() => onSelectProject(p)}
                className="flex w-full items-center justify-between border-b px-0 py-3 text-left text-sm transition-colors hover:text-[#e63946]"
                style={{ borderColor: "#e0ddd6", color: p.id === project.id ? "#e63946" : "#1a1a1a", fontWeight: p.id === project.id ? 600 : 400 }}>
                <span>{p.name}</span>
                {p.unreadCount > 0 && (
                  <span className="flex h-5 min-w-5 items-center justify-center px-1.5 text-[10px] font-bold text-white" style={{ background: "#e63946", borderRadius: "2px" }}>
                    {p.unreadCount}
                  </span>
                )}
              </button>
            ))}
          </div>

          {/* Band members */}
          <h3 className="mb-3 mt-8 text-xs font-semibold uppercase tracking-[0.15em]" style={{ color: "#6b6b6b" }}>Members</h3>
          <div className="space-y-2">
            {band.members.map((m) => (
              <div key={m.id} className="flex items-center gap-2">
                <div className="relative">
                  <div className="flex h-7 w-7 items-center justify-center rounded-full text-[10px] font-bold text-white" style={{ background: "#1a1a1a" }}>{m.avatar}</div>
                  {m.isOnline && <div className="absolute -bottom-0.5 -right-0.5 h-2.5 w-2.5 rounded-full border-2" style={{ background: "#2d6a30", borderColor: "#f8f6f1" }} />}
                </div>
                <div>
                  <div className="text-xs font-medium" style={{ color: "#1a1a1a" }}>{m.name}</div>
                  <div className="text-[10px]" style={{ color: "#6b6b6b" }}>{m.instrument}</div>
                </div>
              </div>
            ))}
          </div>
        </aside>

        {/* Main content */}
        <main className="flex-1">
          <div className="mb-6 flex items-end justify-between">
            <div>
              <h1 className="text-3xl" style={{ fontFamily: "Playfair Display, serif", color: "#1a1a1a" }}>{project.name}</h1>
              <p className="mt-1 text-sm" style={{ color: "#6b6b6b" }}>{project.description}</p>
            </div>
            <button onClick={onOpenSongs} className="px-6 py-2.5 text-sm font-semibold text-white tracking-wide transition-all hover:brightness-110" style={{ background: "#e63946", borderRadius: "2px" }}>
              Song Library &rarr;
            </button>
          </div>

          {/* Stats row */}
          <div className="mb-8 grid grid-cols-4 gap-0 border" style={{ borderColor: "#e0ddd6" }}>
            {[
              { label: "Songs", value: project.songs.length },
              { label: "Ready", value: project.songs.filter((s) => s.status === "ready").length },
              { label: "Processing", value: project.songs.filter((s) => s.status === "processing").length },
              { label: "Unread", value: project.unreadCount },
            ].map((s, i) => (
              <div key={s.label} className="p-4" style={{ borderRight: i < 3 ? "1px solid #e0ddd6" : "none" }}>
                <div className="text-2xl font-bold" style={{ fontFamily: "Playfair Display, serif", color: "#1a1a1a" }}>{s.value}</div>
                <div className="text-xs uppercase tracking-wider" style={{ color: "#6b6b6b" }}>{s.label}</div>
              </div>
            ))}
          </div>

          {/* Recent activity */}
          <h2 className="mb-4 text-lg" style={{ fontFamily: "Playfair Display, serif", color: "#1a1a1a" }}>Recent Activity</h2>
          <div className="space-y-0">
            {project.recentActivity.map((a) => (
              <div key={a.id} className="flex items-start gap-3 border-l-2 py-3 pl-4" style={{ borderColor: "#e0ddd6" }}>
                <span className="mt-0.5 font-mono text-xs font-bold" style={{ color: "#6b6b6b" }}>{ACTIVITY_ICONS[a.type] ?? ">>"}</span>
                <div className="flex-1">
                  <div className="text-sm" style={{ color: "#1a1a1a" }}>
                    <span className="font-semibold">{a.authorName}</span>{" "}
                    <span style={{ color: "#6b6b6b" }}>{a.message}</span>
                  </div>
                  {a.songTitle && <div className="mt-0.5 text-xs" style={{ color: "#6b6b6b" }}>in {a.songTitle}</div>}
                </div>
              </div>
            ))}
          </div>

          {/* Song status overview */}
          <h2 className="mb-4 mt-8 text-lg" style={{ fontFamily: "Playfair Display, serif", color: "#1a1a1a" }}>Songs Overview</h2>
          <div className="border-t" style={{ borderColor: "#e0ddd6" }}>
            {project.songs.map((s) => {
              const sc = STATUS_COLORS[s.status] ?? STATUS_COLORS.uploaded;
              return (
                <div key={s.id} className="flex items-center gap-4 border-b py-3" style={{ borderColor: "#e0ddd6" }}>
                  <div className="flex-1">
                    <div className="text-sm font-semibold" style={{ color: "#1a1a1a" }}>{s.title}</div>
                    <div className="text-xs" style={{ color: "#6b6b6b" }}>{s.artist} &middot; {s.key} &middot; {s.tempo} BPM</div>
                  </div>
                  <span className="px-2 py-0.5 text-xs font-medium" style={{ background: sc.bg, color: sc.text, borderRadius: "2px" }}>{s.status}</span>
                  {s.stems.filter((st) => !st.isArchived).length > 0 && <span className="text-xs" style={{ color: "#6b6b6b" }}>{s.stems.filter((st) => !st.isArchived).length} stems</span>}
                  {s.notes.length > 0 && <span className="text-xs" style={{ color: "#6b6b6b" }}>{s.notes.filter((n) => !n.resolved).length} open comments</span>}
                </div>
              );
            })}
          </div>
        </main>
      </div>
    </div>
  );
}
