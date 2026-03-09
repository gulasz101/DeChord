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
  ready: { bg: "rgba(20, 184, 166, 0.12)", text: "#14b8a6", dot: "#0d9488" },
  processing: { bg: "rgba(124, 58, 237, 0.12)", text: "#a78bfa", dot: "#7c3aed" },
  uploaded: { bg: "rgba(192, 192, 192, 0.08)", text: "#c0c0c0", dot: "#8a8a9a" },
  failed: { bg: "rgba(239, 68, 68, 0.12)", text: "#ef4444", dot: "#dc2626" },
  needs_review: { bg: "rgba(124, 58, 237, 0.15)", text: "#a78bfa", dot: "#8b5cf6" },
};

export function SongLibraryPage({ user, band, project, onSelectSong, onBack }: SongLibraryPageProps) {
  const [showUpload, setShowUpload] = useState(false);

  return (
    <div className="midnight-mesh min-h-screen" style={{ background: "linear-gradient(160deg, #0a0e27 0%, #111638 40%, #0a0e27 100%)" }}>
      {/* Header */}
      <nav className="relative z-10 flex items-center justify-between border-b px-8 py-4" style={{ borderColor: "rgba(192, 192, 192, 0.06)" }}>
        <div className="flex items-center gap-4">
          <button onClick={onBack} className="text-sm transition-colors hover:text-purple-300" style={{ color: "#c0c0c0" }}>← {project.name}</button>
          <div className="h-4 w-px" style={{ background: "rgba(192, 192, 192, 0.12)" }} />
          <span className="text-sm" style={{ color: "#7a7a90" }}>{band.name}</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-full text-[10px] font-bold text-white" style={{ background: "#7c3aed" }}>{user.avatar}</div>
        </div>
      </nav>

      <main className="relative z-10 mx-auto max-w-4xl px-8 pt-8">
        <div className="mb-8 flex items-end justify-between">
          <div>
            <h1 className="text-3xl" style={{ fontFamily: "Orbitron, sans-serif", color: "#e2e2f0" }}>Song Library</h1>
            <p className="mt-1 text-sm" style={{ color: "#7a7a90" }}>{project.songs.length} songs in {project.name}</p>
          </div>
          <div className="flex gap-2">
            <button onClick={() => setShowUpload(!showUpload)} className="rounded-2xl px-5 py-2.5 text-sm font-semibold text-white transition-all hover:brightness-110 hover:shadow-purple-500/20" style={{ background: "linear-gradient(135deg, #7c3aed, #5b21b6)" }}>
              + Upload Song
            </button>
          </div>
        </div>

        {/* Upload panel */}
        {showUpload && (
          <div className="mb-6 rounded-2xl border p-6" style={{ borderColor: "rgba(124, 58, 237, 0.2)", background: "rgba(124, 58, 237, 0.05)", backdropFilter: "blur(12px)" }}>
            <h3 className="mb-3 text-sm font-semibold" style={{ fontFamily: "Orbitron, sans-serif", color: "#a78bfa", fontSize: "0.7rem" }}>Upload a Song</h3>
            <div className="flex items-center gap-4">
              <div className="flex-1 rounded-xl border-2 border-dashed p-8 text-center" style={{ borderColor: "rgba(192, 192, 192, 0.15)" }}>
                <p className="text-sm" style={{ color: "#c0c0c0" }}>Drop an audio file here or click to browse</p>
                <p className="mt-1 text-xs" style={{ color: "#5a5a6e" }}>MP3, WAV, FLAC — up to 50MB</p>
              </div>
            </div>
            <div className="mt-4 flex items-center gap-4">
              <label className="text-xs font-medium" style={{ color: "#c0c0c0" }}>Process Mode:</label>
              <select className="rounded-lg border px-3 py-2 text-xs" style={{ background: "rgba(10, 14, 39, 0.6)", borderColor: "rgba(192, 192, 192, 0.12)", color: "#e2e2f0" }}>
                <option>Analyze + Split Stems</option>
                <option>Analyze Only</option>
              </select>
              <label className="text-xs font-medium" style={{ color: "#c0c0c0" }}>Tab Quality:</label>
              <select className="rounded-lg border px-3 py-2 text-xs" style={{ background: "rgba(10, 14, 39, 0.6)", borderColor: "rgba(192, 192, 192, 0.12)", color: "#e2e2f0" }}>
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
                className="group flex w-full items-center gap-5 rounded-2xl border p-5 text-left transition-all hover:border-purple-500/30 hover:shadow-lg hover:shadow-purple-500/5"
                style={{ background: "rgba(255, 255, 255, 0.02)", borderColor: "rgba(192, 192, 192, 0.05)", backdropFilter: "blur(8px)" }}>
                {/* Status indicator */}
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg" style={{ background: sc.bg }}>
                  <div className="h-2.5 w-2.5 rounded-full" style={{ background: sc.dot }} />
                </div>

                {/* Song info */}
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-base font-semibold group-hover:text-purple-300" style={{ color: "#e2e2f0" }}>{song.title}</span>
                    <span className="text-xs" style={{ color: "#5a5a6e" }}>—</span>
                    <span className="text-sm" style={{ color: "#c0c0c0" }}>{song.artist}</span>
                  </div>
                  <div className="mt-1 flex items-center gap-4 text-xs" style={{ color: "#7a7a90" }}>
                    <span>{song.key}</span>
                    <span>{song.tempo} BPM</span>
                    <span>{Math.floor(song.duration / 60)}:{String(Math.floor(song.duration % 60)).padStart(2, "0")}</span>
                  </div>
                </div>

                {/* Metadata badges */}
                <div className="flex items-center gap-3">
                  {activeStems.length > 0 && (
                    <span className="rounded-full px-2.5 py-1 text-[10px] font-medium" style={{ background: "rgba(20, 184, 166, 0.12)", color: "#14b8a6" }}>
                      {activeStems.length} stems
                    </span>
                  )}
                  {openComments.length > 0 && (
                    <span className="rounded-full px-2.5 py-1 text-[10px] font-medium" style={{ background: "rgba(124, 58, 237, 0.12)", color: "#a78bfa" }}>
                      {openComments.length} comments
                    </span>
                  )}
                  <span className="rounded-full px-2.5 py-1 text-[10px] font-medium" style={{ background: sc.bg, color: sc.text }}>
                    {song.status}
                  </span>
                </div>

                <span className="text-sm transition-transform group-hover:translate-x-1" style={{ color: "#c0c0c0" }}>→</span>
              </button>
            );
          })}
        </div>
      </main>
    </div>
  );
}
