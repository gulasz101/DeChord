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
  ready: { bg: "rgba(0, 255, 65, 0.08)", text: "#00ff41", dot: "#00ff41" },
  processing: { bg: "rgba(0, 229, 255, 0.08)", text: "#00e5ff", dot: "#00e5ff" },
  uploaded: { bg: "rgba(58, 58, 58, 0.2)", text: "#d0d0d0", dot: "#3a3a3a" },
  failed: { bg: "rgba(255, 0, 0, 0.1)", text: "#ff4444", dot: "#ff4444" },
  needs_review: { bg: "rgba(255, 0, 255, 0.08)", text: "#ff00ff", dot: "#ff00ff" },
};

export function SongLibraryPage({ user, band, project, onSelectSong, onBack }: SongLibraryPageProps) {
  const [showUpload, setShowUpload] = useState(false);

  return (
    <div className="scanlines min-h-screen" style={{ background: "#0a0a0a" }}>
      {/* Header */}
      <nav className="relative z-10 flex items-center justify-between border-b px-8 py-4" style={{ borderColor: "rgba(0, 255, 65, 0.1)" }}>
        <div className="flex items-center gap-4">
          <button onClick={onBack} className="font-mono text-sm transition-colors hover:text-green-300" style={{ color: "#00ff41" }}>&lt;-- {project.name}</button>
          <div className="h-4 w-px" style={{ background: "rgba(0, 255, 65, 0.2)" }} />
          <span className="font-mono text-sm" style={{ color: "#3a3a3a" }}>{band.name}</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center border text-[10px] font-bold" style={{ borderColor: "#00ff41", color: "#00ff41" }}>{user.avatar}</div>
        </div>
      </nav>

      <main className="relative z-10 mx-auto max-w-4xl px-8 pt-8">
        <div className="mb-8 flex items-end justify-between">
          <div>
            <h1 className="text-3xl" style={{ fontFamily: "Outfit, sans-serif", color: "#e8e8e8" }}>Song Library</h1>
            <p className="mt-1 font-mono text-sm" style={{ color: "#3a3a3a" }}>{project.songs.length} songs in {project.name}</p>
          </div>
          <div className="flex gap-2">
            <button onClick={() => setShowUpload(!showUpload)} className="border-2 px-5 py-2.5 font-mono text-sm font-semibold transition-all hover:bg-green-900/20" style={{ borderColor: "#00ff41", color: "#00ff41", background: "rgba(0, 255, 65, 0.05)" }}>
              + upload
            </button>
          </div>
        </div>

        {/* Upload panel */}
        {showUpload && (
          <div className="mb-6 border p-6" style={{ borderColor: "rgba(0, 255, 65, 0.3)", background: "rgba(0, 255, 65, 0.03)" }}>
            <h3 className="mb-3 font-mono text-sm font-semibold" style={{ color: "#00ff41" }}>$ upload-song</h3>
            <div className="flex items-center gap-4">
              <div className="flex-1 border-2 border-dashed p-8 text-center" style={{ borderColor: "rgba(0, 255, 65, 0.3)" }}>
                <p className="font-mono text-sm" style={{ color: "#00e5ff" }}>Drop an audio file here or click to browse</p>
                <p className="mt-1 font-mono text-xs" style={{ color: "#3a3a3a" }}>MP3, WAV, FLAC -- up to 50MB</p>
              </div>
            </div>
            <div className="mt-4 flex items-center gap-4">
              <label className="font-mono text-xs font-medium" style={{ color: "#00e5ff" }}>mode:</label>
              <select className="border px-3 py-2 font-mono text-xs" style={{ background: "#111111", borderColor: "rgba(0, 255, 65, 0.2)", color: "#00ff41" }}>
                <option>Analyze + Split Stems</option>
                <option>Analyze Only</option>
              </select>
              <label className="font-mono text-xs font-medium" style={{ color: "#00e5ff" }}>quality:</label>
              <select className="border px-3 py-2 font-mono text-xs" style={{ background: "#111111", borderColor: "rgba(0, 255, 65, 0.2)", color: "#00ff41" }}>
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
                className="group flex w-full items-center gap-5 border p-5 text-left transition-all hover:border-green-500/30 hover:shadow-[0_0_10px_rgba(0,255,65,0.08)]"
                style={{ background: "rgba(0, 255, 65, 0.02)", borderColor: "rgba(0, 255, 65, 0.06)" }}>
                {/* Status indicator */}
                <div className="flex h-10 w-10 shrink-0 items-center justify-center border" style={{ background: sc.bg, borderColor: sc.dot + "33" }}>
                  <div className="h-2.5 w-2.5" style={{ background: sc.dot }} />
                </div>

                {/* Song info */}
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-base font-semibold group-hover:text-green-300" style={{ color: "#e8e8e8" }}>{song.title}</span>
                    <span className="font-mono text-xs" style={{ color: "#3a3a3a" }}>--</span>
                    <span className="text-sm" style={{ color: "#00e5ff" }}>{song.artist}</span>
                  </div>
                  <div className="mt-1 flex items-center gap-4 font-mono text-xs" style={{ color: "#3a3a3a" }}>
                    <span>{song.key}</span>
                    <span>{song.tempo} BPM</span>
                    <span>{Math.floor(song.duration / 60)}:{String(Math.floor(song.duration % 60)).padStart(2, "0")}</span>
                  </div>
                </div>

                {/* Metadata badges */}
                <div className="flex items-center gap-3">
                  {activeStems.length > 0 && (
                    <span className="border px-2.5 py-1 font-mono text-[10px] font-medium" style={{ borderColor: "rgba(0, 255, 65, 0.2)", color: "#00ff41" }}>
                      {activeStems.length} stems
                    </span>
                  )}
                  {openComments.length > 0 && (
                    <span className="border px-2.5 py-1 font-mono text-[10px] font-medium" style={{ borderColor: "rgba(0, 229, 255, 0.2)", color: "#00e5ff" }}>
                      {openComments.length} comments
                    </span>
                  )}
                  <span className="border px-2.5 py-1 font-mono text-[10px] font-medium" style={{ background: sc.bg, color: sc.text, borderColor: sc.text + "33" }}>
                    {song.status}
                  </span>
                </div>

                <span className="font-mono text-sm transition-transform group-hover:translate-x-1" style={{ color: "#00ff41" }}>&gt;</span>
              </button>
            );
          })}
        </div>
      </main>
    </div>
  );
}
