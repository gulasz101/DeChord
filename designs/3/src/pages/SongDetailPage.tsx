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

const STATUS_STYLES: Record<string, { text: string }> = {
  ready: { text: "#2d6a30" },
  processing: { text: "#b45309" },
  uploaded: { text: "#6b6b6b" },
  failed: { text: "#e63946" },
  needs_review: { text: "#7c3aed" },
};

export function SongDetailPage({ user, band, project, song, onOpenPlayer, onBack }: SongDetailPageProps) {
  const [showResolved, setShowResolved] = useState(false);
  const activeStems = song.stems.filter((s) => !s.isArchived);
  const archivedStems = song.stems.filter((s) => s.isArchived);
  const openComments = song.notes.filter((n) => !n.resolved);
  const resolvedComments = song.notes.filter((n) => n.resolved);
  const ss = STATUS_STYLES[song.status] ?? STATUS_STYLES.uploaded;

  return (
    <div className="min-h-screen" style={{ background: "#f8f6f1" }}>
      {/* Header */}
      <nav className="flex items-center justify-between border-b px-8 py-4" style={{ borderColor: "#e0ddd6" }}>
        <div className="flex items-center gap-4">
          <button onClick={onBack} className="text-sm transition-colors hover:text-[#e63946]" style={{ color: "#6b6b6b" }}>&larr; Song Library</button>
          <div className="h-4 w-px" style={{ background: "#e0ddd6" }} />
          <span className="text-xs" style={{ color: "#6b6b6b" }}>{band.name} / {project.name}</span>
        </div>
        <div className="flex h-7 w-7 items-center justify-center rounded-full text-[10px] font-bold text-white" style={{ background: "#1a1a1a" }}>{user.avatar}</div>
      </nav>

      <main className="mx-auto max-w-5xl px-8 pt-8">
        {/* Song header */}
        <div className="mb-8 flex items-start justify-between">
          <div>
            <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: ss.text }}>{song.status}</span>
            <h1 className="mt-1 text-4xl" style={{ fontFamily: "Playfair Display, serif", color: "#1a1a1a" }}>{song.title}</h1>
            <p className="mt-1 text-lg" style={{ color: "#6b6b6b" }}>{song.artist}</p>
            <div className="mt-3 flex items-center gap-6 text-sm" style={{ color: "#6b6b6b" }}>
              <span>Key: <strong style={{ color: "#1a1a1a" }}>{song.key}</strong></span>
              <span>Tempo: <strong style={{ color: "#1a1a1a" }}>{song.tempo} BPM</strong></span>
              <span>Duration: <strong style={{ color: "#1a1a1a" }}>{Math.floor(song.duration / 60)}:{String(Math.floor(song.duration % 60)).padStart(2, "0")}</strong></span>
              <span>Chords: <strong style={{ color: "#1a1a1a" }}>{song.chords.length}</strong></span>
            </div>
          </div>
          {song.status === "ready" && (
            <button onClick={onOpenPlayer} className="px-8 py-3.5 text-sm font-semibold text-white tracking-wide transition-all hover:brightness-110" style={{ background: "#1a1a1a", borderRadius: "2px" }}>
              &#9654; Open Player
            </button>
          )}
        </div>

        <div className="grid grid-cols-3 gap-12">
          {/* Stems column */}
          <div className="col-span-2">
            <h2 className="mb-4 text-lg" style={{ fontFamily: "Playfair Display, serif", color: "#1a1a1a" }}>Stems</h2>
            {activeStems.length === 0 ? (
              <p className="text-sm" style={{ color: "#6b6b6b" }}>No stems available yet.</p>
            ) : (
              <div className="border-t" style={{ borderColor: "#e0ddd6" }}>
                {activeStems.map((stem) => (
                  <div key={stem.id} className="flex items-center gap-4 border-b py-3" style={{ borderColor: "#e0ddd6" }}>
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center text-xs font-bold" style={{ background: "#f0ede6", color: "#1a1a1a", borderRadius: "2px" }}>
                      {stem.label.charAt(0)}
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-semibold" style={{ color: "#1a1a1a" }}>{stem.label}</span>
                        <span className="text-[10px] font-medium" style={{ color: "#6b6b6b" }}>v{stem.version}</span>
                        <span className="text-[10px]" style={{ color: stem.sourceType === "System" ? "#2d6a30" : "#b45309" }}>
                          {stem.sourceType}
                        </span>
                      </div>
                      <div className="mt-0.5 text-xs" style={{ color: "#6b6b6b" }}>{stem.description} — by {stem.uploaderName}</div>
                    </div>
                    <button className="border px-3 py-1.5 text-xs transition-colors hover:bg-black/[0.03]" style={{ borderColor: "#e0ddd6", color: "#1a1a1a", borderRadius: "2px" }}>
                      Download
                    </button>
                  </div>
                ))}
              </div>
            )}

            {archivedStems.length > 0 && (
              <div className="mt-4">
                <h3 className="mb-2 text-xs font-semibold uppercase tracking-[0.15em]" style={{ color: "#6b6b6b" }}>Archived ({archivedStems.length})</h3>
                {archivedStems.map((stem) => (
                  <div key={stem.id} className="py-2 opacity-50">
                    <span className="text-sm" style={{ color: "#6b6b6b" }}>{stem.label} v{stem.version} — {stem.description}</span>
                  </div>
                ))}
              </div>
            )}

            {/* Upload actions */}
            <div className="mt-6 flex gap-3">
              {["Upload Stem", "Generate Stems", "Generate Bass Tab"].map((label) => (
                <button key={label} className="border px-5 py-2.5 text-sm font-medium transition-colors hover:bg-black/[0.03]" style={{ borderColor: "#e0ddd6", color: "#1a1a1a", borderRadius: "2px" }}>
                  {label}
                </button>
              ))}
            </div>
          </div>

          {/* Comments column — editorial margin notes */}
          <div className="border-l pl-8" style={{ borderColor: "#e0ddd6" }}>
            <h2 className="mb-4 text-lg" style={{ fontFamily: "Playfair Display, serif", color: "#1a1a1a" }}>Comments</h2>
            {openComments.length === 0 && <p className="text-sm" style={{ color: "#6b6b6b" }}>No open comments.</p>}
            <div className="space-y-4">
              {openComments.map((note) => (
                <div key={note.id} className="border-l-2 pl-3" style={{ borderColor: "#e63946" }}>
                  <div className="mb-1 flex items-center gap-2">
                    <span className="text-xs font-semibold" style={{ color: "#1a1a1a" }}>{note.authorName}</span>
                    <span className="text-[10px]" style={{ color: "#6b6b6b" }}>{note.type === "time" ? `at ${note.timestampSec?.toFixed(1)}s` : `chord #${(note.chordIndex ?? 0) + 1}`}</span>
                  </div>
                  <p className="text-sm leading-relaxed" style={{ color: "#6b6b6b" }}>{note.text}</p>
                </div>
              ))}
            </div>

            {resolvedComments.length > 0 && (
              <div className="mt-4">
                <button onClick={() => setShowResolved(!showResolved)} className="text-xs font-medium transition-colors hover:text-[#e63946]" style={{ color: "#6b6b6b" }}>
                  {showResolved ? "Hide" : "Show"} resolved ({resolvedComments.length})
                </button>
                {showResolved && (
                  <div className="mt-2 space-y-3">
                    {resolvedComments.map((note) => (
                      <div key={note.id} className="border-l-2 pl-3 opacity-50" style={{ borderColor: "#d4d0c8" }}>
                        <div className="mb-1 flex items-center gap-2">
                          <span className="text-xs" style={{ color: "#6b6b6b" }}>{note.authorName}</span>
                          <span className="text-[10px]" style={{ color: "#2d6a30" }}>&#10003; resolved</span>
                        </div>
                        <p className="text-xs" style={{ color: "#6b6b6b" }}>{note.text}</p>
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
