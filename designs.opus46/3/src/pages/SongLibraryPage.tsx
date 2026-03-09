import { useState } from "react";
import type { Band, Project, Song, User } from "../lib/types";

interface SongLibraryPageProps {
  user: User;
  band: Band;
  project: Project;
  onSelectSong: (s: Song) => void;
  onBack: () => void;
}

const STATUS_COLORS: Record<string, { text: string }> = {
  ready: { text: "#2d6a30" },
  processing: { text: "#b45309" },
  uploaded: { text: "#6b6b6b" },
  failed: { text: "#e63946" },
  needs_review: { text: "#7c3aed" },
};

export function SongLibraryPage({ user, band, project, onSelectSong, onBack }: SongLibraryPageProps) {
  const [showUpload, setShowUpload] = useState(false);

  return (
    <div className="min-h-screen" style={{ background: "#f8f6f1" }}>
      {/* Header */}
      <nav className="flex items-center justify-between border-b px-8 py-4" style={{ borderColor: "#e0ddd6" }}>
        <div className="flex items-center gap-4">
          <button onClick={onBack} className="text-sm transition-colors hover:text-[#e63946]" style={{ color: "#6b6b6b" }}>&larr; {project.name}</button>
          <div className="h-4 w-px" style={{ background: "#e0ddd6" }} />
          <span className="text-sm" style={{ color: "#6b6b6b" }}>{band.name}</span>
        </div>
        <div className="flex h-7 w-7 items-center justify-center rounded-full text-[10px] font-bold text-white" style={{ background: "#1a1a1a" }}>{user.avatar}</div>
      </nav>

      <main className="mx-auto max-w-4xl px-8 pt-8">
        <div className="mb-8 flex items-end justify-between">
          <div>
            <h1 className="text-3xl" style={{ fontFamily: "Playfair Display, serif", color: "#1a1a1a" }}>Song Library</h1>
            <p className="mt-1 text-sm" style={{ color: "#6b6b6b" }}>{project.songs.length} songs in {project.name}</p>
          </div>
          <button onClick={() => setShowUpload(!showUpload)} className="px-5 py-2.5 text-sm font-semibold text-white tracking-wide transition-all hover:brightness-110" style={{ background: "#e63946", borderRadius: "2px" }}>
            + Upload Song
          </button>
        </div>

        {/* Upload panel */}
        {showUpload && (
          <div className="mb-6 border p-6" style={{ borderColor: "#e0ddd6", borderRadius: "2px" }}>
            <h3 className="mb-3 text-sm font-semibold" style={{ color: "#1a1a1a" }}>Upload a Song</h3>
            <div className="flex items-center gap-4">
              <div className="flex-1 border border-dashed p-8 text-center" style={{ borderColor: "#d4d0c8", borderRadius: "2px" }}>
                <p className="text-sm" style={{ color: "#6b6b6b" }}>Drop an audio file here or click to browse</p>
                <p className="mt-1 text-xs" style={{ color: "#a0a0a0" }}>MP3, WAV, FLAC — up to 50MB</p>
              </div>
            </div>
            <div className="mt-4 flex items-center gap-4">
              <label className="text-xs font-semibold" style={{ color: "#1a1a1a" }}>Process Mode:</label>
              <select className="border-b bg-transparent px-1 py-1 text-xs" style={{ borderColor: "#d4d0c8", color: "#1a1a1a" }}>
                <option>Analyze + Split Stems</option>
                <option>Analyze Only</option>
              </select>
              <label className="text-xs font-semibold" style={{ color: "#1a1a1a" }}>Tab Quality:</label>
              <select className="border-b bg-transparent px-1 py-1 text-xs" style={{ borderColor: "#d4d0c8", color: "#1a1a1a" }}>
                <option>Standard</option>
                <option>High Accuracy</option>
                <option>High Accuracy Aggressive</option>
              </select>
            </div>
          </div>
        )}

        {/* Song list — table-like rows */}
        <div className="border-t" style={{ borderColor: "#e0ddd6" }}>
          {/* Table header */}
          <div className="flex items-center gap-4 border-b py-2 text-xs font-semibold uppercase tracking-wider" style={{ borderColor: "#e0ddd6", color: "#6b6b6b" }}>
            <div className="flex-1">Title / Artist</div>
            <div className="w-16 text-center">Key</div>
            <div className="w-20 text-center">Tempo</div>
            <div className="w-16 text-center">Time</div>
            <div className="w-20 text-center">Status</div>
            <div className="w-16 text-right">Info</div>
          </div>

          {project.songs.map((song) => {
            const sc = STATUS_COLORS[song.status] ?? STATUS_COLORS.uploaded;
            const activeStems = song.stems.filter((s) => !s.isArchived);
            const openComments = song.notes.filter((n) => !n.resolved);
            return (
              <button key={song.id} onClick={() => onSelectSong(song)}
                className="group flex w-full items-center gap-4 border-b py-4 text-left transition-colors hover:bg-black/[0.02]"
                style={{ borderColor: "#e0ddd6" }}>
                <div className="flex-1">
                  <span className="text-sm font-semibold group-hover:text-[#e63946]" style={{ color: "#1a1a1a" }}>{song.title}</span>
                  <span className="ml-2 text-sm" style={{ color: "#6b6b6b" }}>{song.artist}</span>
                </div>
                <div className="w-16 text-center text-xs" style={{ color: "#1a1a1a" }}>{song.key}</div>
                <div className="w-20 text-center text-xs" style={{ color: "#1a1a1a" }}>{song.tempo}</div>
                <div className="w-16 text-center text-xs" style={{ color: "#6b6b6b" }}>{Math.floor(song.duration / 60)}:{String(Math.floor(song.duration % 60)).padStart(2, "0")}</div>
                <div className="w-20 text-center text-xs font-medium" style={{ color: sc.text }}>{song.status}</div>
                <div className="w-16 text-right text-[10px]" style={{ color: "#6b6b6b" }}>
                  {activeStems.length > 0 && <span>{activeStems.length}s </span>}
                  {openComments.length > 0 && <span>{openComments.length}c</span>}
                </div>
              </button>
            );
          })}
        </div>
      </main>
    </div>
  );
}
