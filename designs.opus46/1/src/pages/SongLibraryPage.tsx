import { useState } from "react";
import type { Band, Project, Song, User } from "../lib/types";

interface SongLibraryPageProps {
  user: User;
  band: Band;
  project: Project;
  onSelectSong: (s: Song) => void;
  onBack: () => void;
}

const STATUS_COLORS: Record<string, { bg: string; text: string; dot: string }> = {
  ready: { bg: "rgba(107, 114, 52, 0.15)", text: "#a3b236", dot: "#6b7234" },
  processing: { bg: "rgba(180, 83, 9, 0.15)", text: "#d97706", dot: "#b45309" },
  uploaded: { bg: "rgba(196, 168, 130, 0.1)", text: "#c4a882", dot: "#8b7d6b" },
  failed: { bg: "rgba(180, 40, 40, 0.15)", text: "#ef4444", dot: "#dc2626" },
  needs_review: { bg: "rgba(139, 92, 246, 0.15)", text: "#a78bfa", dot: "#8b5cf6" },
};

export function SongLibraryPage({ user, band, project, onSelectSong, onBack }: SongLibraryPageProps) {
  const [showUpload, setShowUpload] = useState(false);

  return (
    <div className="vinyl-noise min-h-screen" style={{ background: "linear-gradient(160deg, #1a1209 0%, #2d1f0e 40%, #1a1209 100%)" }}>
      {/* Header */}
      <nav className="relative z-10 flex items-center justify-between border-b px-8 py-4" style={{ borderColor: "rgba(196, 168, 130, 0.1)" }}>
        <div className="flex items-center gap-4">
          <button onClick={onBack} className="text-sm transition-colors hover:text-amber-300" style={{ color: "#c4a882" }}>← {project.name}</button>
          <div className="h-4 w-px" style={{ background: "rgba(196, 168, 130, 0.2)" }} />
          <span className="text-sm" style={{ color: "#8b7d6b" }}>{band.name}</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-full text-[10px] font-bold text-white" style={{ background: "#b45309" }}>{user.avatar}</div>
        </div>
      </nav>

      <main className="relative z-10 mx-auto max-w-4xl px-8 pt-8">
        <div className="mb-8 flex items-end justify-between">
          <div>
            <h1 className="text-3xl" style={{ fontFamily: "DM Serif Display, serif", color: "#faf5eb" }}>Song Library</h1>
            <p className="mt-1 text-sm" style={{ color: "#8b7d6b" }}>{project.songs.length} songs in {project.name}</p>
          </div>
          <div className="flex gap-2">
            <button onClick={() => setShowUpload(!showUpload)} className="rounded-xl px-5 py-2.5 text-sm font-semibold text-white transition-all hover:brightness-110" style={{ background: "linear-gradient(135deg, #b45309, #92400e)" }}>
              + Upload Song
            </button>
          </div>
        </div>

        {/* Upload panel */}
        {showUpload && (
          <div className="mb-6 rounded-2xl border p-6" style={{ borderColor: "rgba(180, 83, 9, 0.3)", background: "rgba(180, 83, 9, 0.08)" }}>
            <h3 className="mb-3 text-sm font-semibold" style={{ color: "#d97706" }}>Upload a Song</h3>
            <div className="flex items-center gap-4">
              <div className="flex-1 rounded-xl border-2 border-dashed p-8 text-center" style={{ borderColor: "rgba(180, 83, 9, 0.3)" }}>
                <p className="text-sm" style={{ color: "#c4a882" }}>Drop an audio file here or click to browse</p>
                <p className="mt-1 text-xs" style={{ color: "#6b5d4e" }}>MP3, WAV, FLAC — up to 50MB</p>
              </div>
            </div>
            <div className="mt-4 flex items-center gap-4">
              <label className="text-xs font-medium" style={{ color: "#c4a882" }}>Process Mode:</label>
              <select className="rounded-lg border px-3 py-2 text-xs" style={{ background: "rgba(26, 18, 9, 0.6)", borderColor: "rgba(196, 168, 130, 0.2)", color: "#faf5eb" }}>
                <option>Analyze + Split Stems</option>
                <option>Analyze Only</option>
              </select>
              <label className="text-xs font-medium" style={{ color: "#c4a882" }}>Tab Quality:</label>
              <select className="rounded-lg border px-3 py-2 text-xs" style={{ background: "rgba(26, 18, 9, 0.6)", borderColor: "rgba(196, 168, 130, 0.2)", color: "#faf5eb" }}>
                <option>Standard</option>
                <option>High Accuracy</option>
                <option>High Accuracy Aggressive</option>
              </select>
            </div>
          </div>
        )}

        {/* Song list */}
        <div className="space-y-3">
          {project.songs.map((song) => {
            const sc = STATUS_COLORS[song.status] ?? STATUS_COLORS.uploaded;
            const activeStems = song.stems.filter((s) => !s.isArchived);
            const openComments = song.notes.filter((n) => !n.resolved);
            return (
              <button key={song.id} onClick={() => onSelectSong(song)}
                className="group flex w-full items-center gap-5 rounded-2xl border p-5 text-left transition-all hover:border-amber-800/40 hover:shadow-md"
                style={{ background: "rgba(26, 18, 9, 0.5)", borderColor: "rgba(196, 168, 130, 0.08)" }}>
                {/* Status indicator */}
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg" style={{ background: sc.bg }}>
                  <div className="h-2.5 w-2.5 rounded-full" style={{ background: sc.dot }} />
                </div>

                {/* Song info */}
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-base font-semibold group-hover:text-amber-300" style={{ color: "#faf5eb" }}>{song.title}</span>
                    <span className="text-xs" style={{ color: "#6b5d4e" }}>—</span>
                    <span className="text-sm" style={{ color: "#c4a882" }}>{song.artist}</span>
                  </div>
                  <div className="mt-1 flex items-center gap-4 text-xs" style={{ color: "#8b7d6b" }}>
                    <span>{song.key}</span>
                    <span>{song.tempo} BPM</span>
                    <span>{Math.floor(song.duration / 60)}:{String(Math.floor(song.duration % 60)).padStart(2, "0")}</span>
                  </div>
                </div>

                {/* Metadata badges */}
                <div className="flex items-center gap-3">
                  {activeStems.length > 0 && (
                    <span className="rounded-full px-2.5 py-1 text-[10px] font-medium" style={{ background: "rgba(107, 114, 52, 0.15)", color: "#a3b236" }}>
                      {activeStems.length} stems
                    </span>
                  )}
                  {openComments.length > 0 && (
                    <span className="rounded-full px-2.5 py-1 text-[10px] font-medium" style={{ background: "rgba(180, 83, 9, 0.15)", color: "#d97706" }}>
                      {openComments.length} comments
                    </span>
                  )}
                  <span className="rounded-full px-2.5 py-1 text-[10px] font-medium" style={{ background: sc.bg, color: sc.text }}>
                    {song.status}
                  </span>
                </div>

                <span className="text-sm transition-transform group-hover:translate-x-1" style={{ color: "#c4a882" }}>→</span>
              </button>
            );
          })}
        </div>
      </main>
    </div>
  );
}
