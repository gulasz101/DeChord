import { useState } from "react";
import type { Band, Project, Song, User } from "../lib/types";

interface SongDetailPageProps {
  user: User;
  band: Band;
  project: Project;
  song: Song;
  onOpenPlayer: () => void;
  onBack: () => void;
}

const STATUS_STYLES: Record<string, { bg: string; text: string }> = {
  ready: { bg: "#FFE500", text: "#000" },
  processing: { bg: "#000", text: "#FFE500" },
  uploaded: { bg: "#f5f5f5", text: "#000" },
  failed: { bg: "#FF0000", text: "#fff" },
  needs_review: { bg: "#333", text: "#fff" },
};

export function SongDetailPage({ user, band, project, song, onOpenPlayer, onBack }: SongDetailPageProps) {
  const [showResolved, setShowResolved] = useState(false);
  const activeStems = song.stems.filter((s) => !s.isArchived);
  const archivedStems = song.stems.filter((s) => s.isArchived);
  const openComments = song.notes.filter((n) => !n.resolved);
  const resolvedComments = song.notes.filter((n) => n.resolved);
  const ss = STATUS_STYLES[song.status] ?? STATUS_STYLES.uploaded;

  return (
    <div className="min-h-screen" style={{ background: "#fff" }}>
      {/* Header */}
      <nav className="flex items-center justify-between px-8 py-4" style={{ borderBottom: "3px solid #000" }}>
        <div className="flex items-center gap-4">
          <button onClick={onBack} className="text-sm font-bold uppercase tracking-wider transition-colors hover:text-yellow-500" style={{ color: "#000" }}>← Song Library</button>
          <div style={{ width: "3px", height: "16px", background: "#000" }} />
          <span className="text-xs font-bold uppercase" style={{ color: "#888" }}>{band.name} / {project.name}</span>
        </div>
        <div className="flex h-7 w-7 items-center justify-center text-[10px] font-bold" style={{ background: "#FFE500", border: "2px solid #000", color: "#000" }}>{user.avatar}</div>
      </nav>

      <main className="mx-auto max-w-5xl px-8 pt-8">
        {/* Song header */}
        <div className="mb-8 flex items-start justify-between">
          <div>
            <div className="mb-2 flex items-center gap-3">
              <span className="px-3 py-1 text-xs font-bold uppercase" style={{ background: ss.bg, color: ss.text, border: "2px solid #000" }}>{song.status}</span>
            </div>
            <h1 className="text-5xl uppercase" style={{ fontFamily: "Archivo Black, sans-serif", color: "#000" }}>{song.title}</h1>
            <p className="mt-1 text-lg font-bold uppercase" style={{ color: "#555" }}>{song.artist}</p>
            <div className="mt-3 flex items-center gap-5 text-sm" style={{ color: "#888" }}>
              <span>Key: <strong style={{ color: "#000" }}>{song.key}</strong></span>
              <span>|</span>
              <span>Tempo: <strong style={{ color: "#000" }}>{song.tempo} BPM</strong></span>
              <span>|</span>
              <span>Duration: <strong style={{ color: "#000" }}>{Math.floor(song.duration / 60)}:{String(Math.floor(song.duration % 60)).padStart(2, "0")}</strong></span>
              <span>|</span>
              <span>Chords: <strong style={{ color: "#000" }}>{song.chords.length}</strong></span>
            </div>
          </div>
          {song.status === "ready" && (
            <button onClick={onOpenPlayer} className="px-8 py-4 text-base font-bold uppercase tracking-wider transition-all hover:bg-yellow-300" style={{ background: "#FFE500", color: "#000", border: "3px solid #000" }}>
              ▶ Open Player
            </button>
          )}
        </div>

        <div className="grid grid-cols-3 gap-8">
          {/* Stems column */}
          <div className="col-span-2">
            <h2 className="mb-4 text-lg uppercase" style={{ fontFamily: "Archivo Black, sans-serif", color: "#000" }}>Stems</h2>
            {activeStems.length === 0 ? (
              <p className="text-sm font-bold uppercase" style={{ color: "#888" }}>No stems available yet.</p>
            ) : (
              <div style={{ border: "3px solid #000" }}>
                {activeStems.map((stem) => (
                  <div key={stem.id} className="flex items-center gap-4 p-4" style={{ borderBottom: "2px solid #000" }}>
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center text-sm font-bold" style={{ background: stem.sourceType === "System" ? "#FFE500" : "#000", color: stem.sourceType === "System" ? "#000" : "#FFE500", border: "2px solid #000" }}>
                      {stem.label.charAt(0)}
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-bold uppercase" style={{ color: "#000" }}>{stem.label}</span>
                        <span className="px-1.5 py-0.5 text-[10px] font-bold uppercase" style={{ background: "#f5f5f5", color: "#000", border: "1px solid #000" }}>v{stem.version}</span>
                        <span className="px-1.5 py-0.5 text-[10px] font-bold uppercase" style={{ background: stem.sourceType === "System" ? "#FFE500" : "#000", color: stem.sourceType === "System" ? "#000" : "#FFE500" }}>
                          {stem.sourceType}
                        </span>
                      </div>
                      <div className="mt-0.5 text-xs" style={{ color: "#555" }}>{stem.description} — by {stem.uploaderName}</div>
                    </div>
                    <button className="px-3 py-1.5 text-xs font-bold uppercase tracking-wider transition-colors hover:bg-yellow-300" style={{ border: "2px solid #000", color: "#000" }}>
                      Download
                    </button>
                  </div>
                ))}
              </div>
            )}

            {archivedStems.length > 0 && (
              <div className="mt-4">
                <h3 className="mb-2 text-xs font-bold uppercase tracking-widest" style={{ color: "#888" }}>Archived ({archivedStems.length})</h3>
                {archivedStems.map((stem) => (
                  <div key={stem.id} className="flex items-center gap-4 p-3 opacity-50" style={{ background: "#f5f5f5", border: "1px solid #000" }}>
                    <span className="text-sm" style={{ color: "#555" }}>{stem.label} v{stem.version} — {stem.description}</span>
                  </div>
                ))}
              </div>
            )}

            {/* Upload actions */}
            <div className="mt-6 flex gap-3">
              <button className="px-5 py-2.5 text-sm font-bold uppercase tracking-wider transition-colors hover:bg-yellow-300" style={{ border: "3px solid #000", color: "#000" }}>
                Upload Stem
              </button>
              <button className="px-5 py-2.5 text-sm font-bold uppercase tracking-wider transition-colors hover:bg-yellow-300" style={{ border: "3px solid #000", color: "#000" }}>
                Generate Stems
              </button>
              <button className="px-5 py-2.5 text-sm font-bold uppercase tracking-wider transition-colors hover:bg-yellow-300" style={{ border: "3px solid #000", color: "#000" }}>
                Generate Bass Tab
              </button>
            </div>
          </div>

          {/* Comments column */}
          <div>
            <h2 className="mb-4 text-lg uppercase" style={{ fontFamily: "Archivo Black, sans-serif", color: "#000" }}>Comments</h2>
            {openComments.length === 0 && <p className="text-sm font-bold uppercase" style={{ color: "#888" }}>No open comments.</p>}
            <div className="space-y-0" style={{ border: openComments.length > 0 ? "3px solid #000" : "none" }}>
              {openComments.map((note) => (
                <div key={note.id} className="p-4" style={{ borderBottom: "2px solid #000", borderLeft: "6px solid #FFE500" }}>
                  <div className="mb-2 flex items-center gap-2">
                    <div className="flex h-6 w-6 items-center justify-center text-[9px] font-bold" style={{ background: "#000", color: "#FFE500" }}>{note.authorAvatar}</div>
                    <span className="text-xs font-bold uppercase" style={{ color: "#000" }}>{note.authorName}</span>
                    <span className="text-[10px] font-bold uppercase" style={{ color: "#888" }}>{note.type === "time" ? `at ${note.timestampSec?.toFixed(1)}s` : `chord #${(note.chordIndex ?? 0) + 1}`}</span>
                  </div>
                  <p className="text-sm leading-relaxed" style={{ color: "#333" }}>{note.text}</p>
                </div>
              ))}
            </div>

            {resolvedComments.length > 0 && (
              <div className="mt-4">
                <button onClick={() => setShowResolved(!showResolved)} className="text-xs font-bold uppercase tracking-wider transition-colors hover:text-yellow-500" style={{ color: "#888" }}>
                  {showResolved ? "Hide" : "Show"} resolved ({resolvedComments.length})
                </button>
                {showResolved && (
                  <div className="mt-2 space-y-0" style={{ border: "2px solid #000" }}>
                    {resolvedComments.map((note) => (
                      <div key={note.id} className="p-3 opacity-60" style={{ borderBottom: "1px solid #000" }}>
                        <div className="mb-1 flex items-center gap-2">
                          <span className="text-xs font-bold uppercase" style={{ color: "#555" }}>{note.authorName}</span>
                          <span className="text-[10px] font-bold" style={{ color: "#000" }}>✓ RESOLVED</span>
                        </div>
                        <p className="text-xs" style={{ color: "#555" }}>{note.text}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
