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
  ready: { bg: "#FFE500", text: "#000" },
  processing: { bg: "#000", text: "#FFE500" },
  uploaded: { bg: "#f5f5f5", text: "#000" },
  failed: { bg: "#FF0000", text: "#fff" },
  needs_review: { bg: "#333", text: "#fff" },
};

const ACTIVITY_ICONS: Record<string, string> = {
  stem_upload: "🎵", comment: "💬", status_change: "✅", song_added: "➕", comment_resolved: "☑️",
};

export function ProjectHomePage({ user, band, project, onSelectProject, onOpenSongs, onBack }: ProjectHomePageProps) {
  return (
    <div className="min-h-screen" style={{ background: "#fff" }}>
      {/* Header */}
      <nav className="flex items-center justify-between px-8 py-4" style={{ borderBottom: "3px solid #000" }}>
        <div className="flex items-center gap-4">
          <button onClick={onBack} className="text-sm font-bold uppercase tracking-wider transition-colors hover:text-yellow-500" style={{ color: "#000" }}>← Bands</button>
          <div style={{ width: "3px", height: "16px", background: "#000" }} />
          <span className="text-sm font-bold uppercase" style={{ color: "#000" }}>{band.name}</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center text-[10px] font-bold" style={{ background: "#FFE500", border: "2px solid #000", color: "#000" }}>{user.avatar}</div>
          <span className="text-xs font-bold uppercase" style={{ color: "#000" }}>{user.name}</span>
        </div>
      </nav>

      <div className="mx-auto flex max-w-6xl gap-0 px-8 pt-8">
        {/* Sidebar — project list */}
        <aside className="w-56 shrink-0 pr-6" style={{ borderRight: "3px solid #000" }}>
          <h3 className="mb-3 text-xs font-bold uppercase tracking-widest" style={{ color: "#888" }}>Projects</h3>
          <div className="space-y-0">
            {band.projects.map((p) => (
              <button key={p.id} onClick={() => onSelectProject(p)}
                className="flex w-full items-center justify-between px-3 py-2.5 text-left text-sm font-bold uppercase transition-colors hover:bg-yellow-300"
                style={{ background: p.id === project.id ? "#FFE500" : "transparent", color: "#000", borderBottom: "2px solid #000" }}>
                <span>{p.name}</span>
                {p.unreadCount > 0 && (
                  <span className="flex h-5 min-w-5 items-center justify-center px-1.5 text-[10px] font-bold" style={{ background: "#FF0000", color: "#fff" }}>
                    {p.unreadCount}
                  </span>
                )}
              </button>
            ))}
          </div>

          {/* Band members */}
          <h3 className="mb-3 mt-8 text-xs font-bold uppercase tracking-widest" style={{ color: "#888" }}>Members</h3>
          <div className="space-y-2">
            {band.members.map((m) => (
              <div key={m.id} className="flex items-center gap-2">
                <div className="relative">
                  <div className="flex h-7 w-7 items-center justify-center text-[10px] font-bold" style={{ background: "#000", color: "#FFE500" }}>{m.avatar}</div>
                  {m.isOnline && <div className="absolute -bottom-0.5 -right-0.5 h-2.5 w-2.5" style={{ background: "#FFE500", border: "2px solid #fff" }} />}
                </div>
                <div>
                  <div className="text-xs font-bold uppercase" style={{ color: "#000" }}>{m.name}</div>
                  <div className="text-[10px] uppercase" style={{ color: "#888" }}>{m.instrument}</div>
                </div>
              </div>
            ))}
          </div>
        </aside>

        {/* Main content */}
        <main className="flex-1 pl-6">
          <div className="mb-6 flex items-end justify-between">
            <div>
              <h1 className="text-3xl uppercase" style={{ fontFamily: "Archivo Black, sans-serif", color: "#000" }}>{project.name}</h1>
              <p className="mt-1 text-sm" style={{ color: "#555" }}>{project.description}</p>
            </div>
            <button onClick={onOpenSongs} className="px-6 py-2.5 text-sm font-bold uppercase tracking-wider transition-all hover:bg-white hover:text-black" style={{ background: "#000", color: "#fff", border: "3px solid #000" }}>
              Song Library →
            </button>
          </div>

          {/* Stats row */}
          <div className="mb-8 grid grid-cols-4 gap-0" style={{ border: "3px solid #000" }}>
            {[
              { label: "Songs", value: project.songs.length },
              { label: "Ready", value: project.songs.filter((s) => s.status === "ready").length },
              { label: "Processing", value: project.songs.filter((s) => s.status === "processing").length },
              { label: "Unread", value: project.unreadCount },
            ].map((s, i) => (
              <div key={s.label} className="p-4" style={{ borderRight: i < 3 ? "3px solid #000" : "none" }}>
                <div className="text-5xl font-bold" style={{ fontFamily: "Archivo Black, sans-serif", color: "#000" }}>{s.value}</div>
                <div className="text-xs font-bold uppercase tracking-wider" style={{ color: "#888" }}>{s.label}</div>
              </div>
            ))}
          </div>

          {/* Recent activity */}
          <h2 className="mb-4 text-lg uppercase" style={{ fontFamily: "Archivo Black, sans-serif", color: "#000" }}>Recent Activity</h2>
          <div className="space-y-0" style={{ border: "3px solid #000" }}>
            {project.recentActivity.map((a) => (
              <div key={a.id} className="flex items-start gap-3 p-4" style={{ borderBottom: "2px solid #000", borderLeft: "6px solid #FFE500" }}>
                <span className="mt-0.5 text-lg">{ACTIVITY_ICONS[a.type] ?? "📌"}</span>
                <div className="flex-1">
                  <div className="text-sm" style={{ color: "#000" }}>
                    <span className="font-bold uppercase">{a.authorName}</span>{" "}
                    <span>{a.message}</span>
                  </div>
                  {a.songTitle && <div className="mt-0.5 text-xs font-bold uppercase" style={{ color: "#888" }}>in {a.songTitle}</div>}
                </div>
              </div>
            ))}
          </div>

          {/* Song status overview */}
          <h2 className="mb-4 mt-8 text-lg uppercase" style={{ fontFamily: "Archivo Black, sans-serif", color: "#000" }}>Songs Overview</h2>
          <div style={{ border: "3px solid #000" }}>
            {project.songs.map((s) => {
              const sc = STATUS_COLORS[s.status] ?? STATUS_COLORS.uploaded;
              return (
                <div key={s.id} className="flex items-center gap-4 p-4" style={{ borderBottom: "2px solid #000" }}>
                  <div className="flex-1">
                    <div className="text-sm font-bold uppercase" style={{ color: "#000" }}>{s.title}</div>
                    <div className="text-xs" style={{ color: "#555" }}>{s.artist} · {s.key} · {s.tempo} BPM</div>
                  </div>
                  <span className="px-3 py-1 text-xs font-bold uppercase" style={{ background: sc.bg, color: sc.text, border: "2px solid #000" }}>{s.status}</span>
                  {s.stems.filter((st) => !st.isArchived).length > 0 && <span className="text-xs font-bold uppercase" style={{ color: "#555" }}>{s.stems.filter((st) => !st.isArchived).length} stems</span>}
                  {s.notes.length > 0 && <span className="text-xs font-bold uppercase" style={{ color: "#555" }}>{s.notes.filter((n) => !n.resolved).length} open</span>}
                </div>
              );
            })}
          </div>
        </main>
      </div>
    </div>
  );
}
