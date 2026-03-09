import { useState } from "react";
import type { Band, Project, Song, User } from "../lib/types";

interface SongLibraryPageProps {
  user: User;
  band: Band;
  project: Project;
  onSelectSong: (s: Song) => void;
  onBack: () => void;
}

const STATUS_COLORS: Record<string, { bg: string; text: string }> = {
  ready: { bg: "#FFE500", text: "#000" },
  processing: { bg: "#000", text: "#FFE500" },
  uploaded: { bg: "#f5f5f5", text: "#000" },
  failed: { bg: "#FF0000", text: "#fff" },
  needs_review: { bg: "#333", text: "#fff" },
};

export function SongLibraryPage({ user, band, project, onSelectSong, onBack }: SongLibraryPageProps) {
  const [showUpload, setShowUpload] = useState(false);

  return (
    <div className="min-h-screen" style={{ background: "#fff" }}>
      {/* Header */}
      <nav className="flex items-center justify-between px-8 py-4" style={{ borderBottom: "3px solid #000" }}>
        <div className="flex items-center gap-4">
          <button onClick={onBack} className="text-sm font-bold uppercase tracking-wider transition-colors hover:text-yellow-500" style={{ color: "#000" }}>← {project.name}</button>
          <div style={{ width: "3px", height: "16px", background: "#000" }} />
          <span className="text-sm font-bold uppercase" style={{ color: "#888" }}>{band.name}</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center text-[10px] font-bold" style={{ background: "#FFE500", border: "2px solid #000", color: "#000" }}>{user.avatar}</div>
        </div>
      </nav>

      <main className="mx-auto max-w-4xl px-8 pt-8">
        <div className="mb-8 flex items-end justify-between">
          <div>
            <h1 className="text-3xl uppercase" style={{ fontFamily: "Archivo Black, sans-serif", color: "#000" }}>Song Library</h1>
            <p className="mt-1 text-sm font-bold uppercase" style={{ color: "#888" }}>{project.songs.length} songs in {project.name}</p>
          </div>
          <div className="flex gap-2">
            <button onClick={() => setShowUpload(!showUpload)} className="px-5 py-2.5 text-sm font-bold uppercase tracking-wider transition-all hover:bg-yellow-300" style={{ background: "#FFE500", color: "#000", border: "3px solid #000" }}>
              + Upload Song
            </button>
          </div>
        </div>

        {/* Upload panel */}
        {showUpload && (
          <div className="mb-6 p-6" style={{ border: "3px solid #000", background: "#f5f5f5" }}>
            <h3 className="mb-3 text-sm font-bold uppercase" style={{ color: "#000" }}>Upload a Song</h3>
            <div className="flex items-center gap-4">
              <div className="flex-1 p-8 text-center" style={{ border: "3px dashed #000" }}>
                <p className="text-sm font-bold uppercase" style={{ color: "#000" }}>Drop an audio file here or click to browse</p>
                <p className="mt-1 text-xs" style={{ color: "#555" }}>MP3, WAV, FLAC — up to 50MB</p>
              </div>
            </div>
            <div className="mt-4 flex items-center gap-4">
              <label className="text-xs font-bold uppercase" style={{ color: "#000" }}>Process Mode:</label>
              <select className="px-3 py-2 text-xs font-bold" style={{ background: "#fff", border: "2px solid #000", color: "#000" }}>
                <option>Analyze + Split Stems</option>
                <option>Analyze Only</option>
              </select>
              <label className="text-xs font-bold uppercase" style={{ color: "#000" }}>Tab Quality:</label>
              <select className="px-3 py-2 text-xs font-bold" style={{ background: "#fff", border: "2px solid #000", color: "#000" }}>
                <option>Standard</option>
                <option>High Accuracy</option>
                <option>High Accuracy Aggressive</option>
              </select>
            </div>
          </div>
        )}

        {/* Song list — table style */}
        <div style={{ border: "3px solid #000" }}>
          {/* Table header */}
          <div className="flex items-center gap-5 p-4" style={{ background: "#000", color: "#fff" }}>
            <div className="w-10 shrink-0 text-xs font-bold uppercase">#</div>
            <div className="flex-1 text-xs font-bold uppercase">Song</div>
            <div className="w-24 text-xs font-bold uppercase text-center">Status</div>
            <div className="w-20 text-xs font-bold uppercase text-center">Stems</div>
            <div className="w-20 text-xs font-bold uppercase text-center">Notes</div>
            <div className="w-8"></div>
          </div>
          {project.songs.map((song, idx) => {
            const sc = STATUS_COLORS[song.status] ?? STATUS_COLORS.uploaded;
            const activeStems = song.stems.filter((s) => !s.isArchived);
            const openComments = song.notes.filter((n) => !n.resolved);
            return (
              <button key={song.id} onClick={() => onSelectSong(song)}
                className="group flex w-full items-center gap-5 p-4 text-left transition-colors hover:bg-yellow-300"
                style={{ borderBottom: "2px solid #000" }}>
                <div className="w-10 shrink-0 text-lg font-bold" style={{ fontFamily: "Archivo Black, sans-serif", color: "#000" }}>{idx + 1}</div>
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-base font-bold uppercase" style={{ color: "#000" }}>{song.title}</span>
                    <span style={{ color: "#000" }}>—</span>
                    <span className="text-sm" style={{ color: "#555" }}>{song.artist}</span>
                  </div>
                  <div className="mt-0.5 flex items-center gap-4 text-xs font-bold uppercase" style={{ color: "#888" }}>
                    <span>{song.key}</span>
                    <span>{song.tempo} BPM</span>
                    <span>{Math.floor(song.duration / 60)}:{String(Math.floor(song.duration % 60)).padStart(2, "0")}</span>
                  </div>
                </div>
                <div className="w-24 text-center">
                  <span className="px-2.5 py-1 text-[10px] font-bold uppercase" style={{ background: sc.bg, color: sc.text, border: "2px solid #000" }}>
                    {song.status}
                  </span>
                </div>
                <div className="w-20 text-center">
                  {activeStems.length > 0 && (
                    <span className="text-xs font-bold" style={{ color: "#000" }}>{activeStems.length}</span>
                  )}
                </div>
                <div className="w-20 text-center">
                  {openComments.length > 0 && (
                    <span className="text-xs font-bold" style={{ color: "#FF0000" }}>{openComments.length}</span>
                  )}
                </div>
                <span className="w-8 text-xl font-bold transition-transform group-hover:translate-x-1" style={{ color: "#000" }}>→</span>
              </button>
            );
          })}
        </div>
      </main>
    </div>
  );
}
