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
  ready: { bg: "rgba(20, 184, 166, 0.15)", text: "#14b8a6" },
  processing: { bg: "rgba(124, 58, 237, 0.15)", text: "#a78bfa" },
  uploaded: { bg: "rgba(192, 192, 192, 0.1)", text: "#c0c0c0" },
  failed: { bg: "rgba(239, 68, 68, 0.15)", text: "#ef4444" },
  needs_review: { bg: "rgba(124, 58, 237, 0.2)", text: "#a78bfa" },
};

export function SongDetailPage({ user, band, project, song, onOpenPlayer, onBack }: SongDetailPageProps) {
  const [showResolved, setShowResolved] = useState(false);
  const activeStems = song.stems.filter((s) => !s.isArchived);
  const archivedStems = song.stems.filter((s) => s.isArchived);
  const openComments = song.notes.filter((n) => !n.resolved);
  const resolvedComments = song.notes.filter((n) => n.resolved);
  const ss = STATUS_STYLES[song.status] ?? STATUS_STYLES.uploaded;

  return (
    <div className="midnight-mesh min-h-screen" style={{ background: "linear-gradient(160deg, #0a0e27 0%, #111638 40%, #0a0e27 100%)" }}>
      {/* Header */}
      <nav className="relative z-10 flex items-center justify-between border-b px-8 py-4" style={{ borderColor: "rgba(192, 192, 192, 0.06)" }}>
        <div className="flex items-center gap-4">
          <button onClick={onBack} className="text-sm transition-colors hover:text-purple-300" style={{ color: "#c0c0c0" }}>← Song Library</button>
          <div className="h-4 w-px" style={{ background: "rgba(192, 192, 192, 0.12)" }} />
          <span className="text-xs" style={{ color: "#7a7a90" }}>{band.name} / {project.name}</span>
        </div>
        <div className="flex h-7 w-7 items-center justify-center rounded-full text-[10px] font-bold text-white" style={{ background: "#7c3aed" }}>{user.avatar}</div>
      </nav>

      <main className="relative z-10 mx-auto max-w-5xl px-8 pt-8">
        {/* Song header */}
        <div className="mb-8 flex items-start justify-between">
          <div>
            <div className="mb-2 flex items-center gap-3">
              <span className="rounded-full px-3 py-1 text-xs font-medium" style={{ background: ss.bg, color: ss.text }}>{song.status}</span>
            </div>
            <h1 className="text-4xl" style={{ fontFamily: "Orbitron, sans-serif", color: "#e2e2f0" }}>{song.title}</h1>
            <p className="mt-1 text-lg" style={{ color: "#c0c0c0" }}>{song.artist}</p>
            <div className="mt-3 flex items-center gap-5 text-sm" style={{ color: "#7a7a90" }}>
              <span>Key: <strong style={{ color: "#e2e2f0" }}>{song.key}</strong></span>
              <span>Tempo: <strong style={{ color: "#e2e2f0" }}>{song.tempo} BPM</strong></span>
              <span>Duration: <strong style={{ color: "#e2e2f0" }}>{Math.floor(song.duration / 60)}:{String(Math.floor(song.duration % 60)).padStart(2, "0")}</strong></span>
              <span>Chords: <strong style={{ color: "#e2e2f0" }}>{song.chords.length}</strong></span>
            </div>
          </div>
          {song.status === "ready" && (
            <button onClick={onOpenPlayer} className="rounded-2xl px-8 py-3.5 text-base font-semibold text-white shadow-lg transition-all hover:brightness-110 hover:shadow-xl hover:shadow-purple-500/20" style={{ background: "linear-gradient(135deg, #7c3aed, #5b21b6)" }}>
              ▶ Open Player
            </button>
          )}
        </div>

        <div className="grid grid-cols-3 gap-8">
          {/* Stems column */}
          <div className="col-span-2">
            <h2 className="mb-4 text-lg" style={{ fontFamily: "Orbitron, sans-serif", color: "#e2e2f0", fontSize: "0.9rem" }}>Stems</h2>
            {activeStems.length === 0 ? (
              <p className="text-sm" style={{ color: "#7a7a90" }}>No stems available yet.</p>
            ) : (
              <div className="space-y-2">
                {activeStems.map((stem) => (
                  <div key={stem.id} className="flex items-center gap-4 rounded-xl border p-4" style={{ borderColor: "rgba(192, 192, 192, 0.05)", background: "rgba(255, 255, 255, 0.02)", backdropFilter: "blur(8px)" }}>
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-sm font-bold" style={{ background: stem.sourceType === "System" ? "rgba(20, 184, 166, 0.15)" : "rgba(124, 58, 237, 0.15)", color: stem.sourceType === "System" ? "#14b8a6" : "#a78bfa" }}>
                      {stem.label.charAt(0)}
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-semibold" style={{ color: "#e2e2f0" }}>{stem.label}</span>
                        <span className="rounded px-1.5 py-0.5 text-[10px]" style={{ background: "rgba(192, 192, 192, 0.06)", color: "#7a7a90" }}>v{stem.version}</span>
                        <span className="rounded px-1.5 py-0.5 text-[10px]" style={{ background: stem.sourceType === "System" ? "rgba(20, 184, 166, 0.1)" : "rgba(124, 58, 237, 0.1)", color: stem.sourceType === "System" ? "#14b8a6" : "#a78bfa" }}>
                          {stem.sourceType}
                        </span>
                      </div>
                      <div className="mt-0.5 text-xs" style={{ color: "#7a7a90" }}>{stem.description} — by {stem.uploaderName}</div>
                    </div>
                    <button className="rounded-lg border px-3 py-1.5 text-xs transition-all hover:bg-white/5 hover:border-purple-500/30" style={{ borderColor: "rgba(192, 192, 192, 0.12)", color: "#c0c0c0" }}>
                      Download
                    </button>
                  </div>
                ))}
              </div>
            )}

            {archivedStems.length > 0 && (
              <div className="mt-4">
                <h3 className="mb-2 text-xs font-medium uppercase tracking-widest" style={{ fontFamily: "Orbitron, sans-serif", color: "#5a5a6e", fontSize: "0.55rem" }}>Archived ({archivedStems.length})</h3>
                {archivedStems.map((stem) => (
                  <div key={stem.id} className="flex items-center gap-4 rounded-lg p-3 opacity-50" style={{ background: "rgba(255, 255, 255, 0.01)" }}>
                    <span className="text-sm" style={{ color: "#7a7a90" }}>{stem.label} v{stem.version} — {stem.description}</span>
                  </div>
                ))}
              </div>
            )}

            {/* Upload actions */}
            <div className="mt-6 flex gap-3">
              <button className="rounded-2xl border px-5 py-2.5 text-sm font-medium transition-all hover:bg-white/5 hover:border-purple-500/30" style={{ borderColor: "rgba(192, 192, 192, 0.1)", color: "#c0c0c0" }}>
                Upload Stem
              </button>
              <button className="rounded-2xl border px-5 py-2.5 text-sm font-medium transition-all hover:bg-white/5 hover:border-purple-500/30" style={{ borderColor: "rgba(192, 192, 192, 0.1)", color: "#c0c0c0" }}>
                Generate Stems
              </button>
              <button className="rounded-2xl border px-5 py-2.5 text-sm font-medium transition-all hover:bg-white/5 hover:border-purple-500/30" style={{ borderColor: "rgba(192, 192, 192, 0.1)", color: "#c0c0c0" }}>
                Generate Bass Tab
              </button>
            </div>
          </div>

          {/* Comments column */}
          <div>
            <h2 className="mb-4 text-lg" style={{ fontFamily: "Orbitron, sans-serif", color: "#e2e2f0", fontSize: "0.9rem" }}>Comments</h2>
            {openComments.length === 0 && <p className="text-sm" style={{ color: "#7a7a90" }}>No open comments.</p>}
            <div className="space-y-3">
              {openComments.map((note) => (
                <div key={note.id} className="rounded-xl border-l-2 border p-4" style={{ borderColor: "rgba(192, 192, 192, 0.05)", borderLeftColor: "rgba(124, 58, 237, 0.5)", background: "rgba(255, 255, 255, 0.02)" }}>
                  <div className="mb-2 flex items-center gap-2">
                    <div className="flex h-6 w-6 items-center justify-center rounded-full text-[9px] font-bold text-white" style={{ background: "#1e1e3a" }}>{note.authorAvatar}</div>
                    <span className="text-xs font-semibold" style={{ color: "#e2e2f0" }}>{note.authorName}</span>
                    <span className="text-[10px]" style={{ color: "#5a5a6e" }}>{note.type === "time" ? `at ${note.timestampSec?.toFixed(1)}s` : `chord #${(note.chordIndex ?? 0) + 1}`}</span>
                  </div>
                  <p className="text-sm leading-relaxed" style={{ color: "#c0c0c0" }}>{note.text}</p>
                </div>
              ))}
            </div>

            {resolvedComments.length > 0 && (
              <div className="mt-4">
                <button onClick={() => setShowResolved(!showResolved)} className="text-xs font-medium transition-colors hover:text-purple-300" style={{ color: "#7a7a90" }}>
                  {showResolved ? "Hide" : "Show"} resolved ({resolvedComments.length})
                </button>
                {showResolved && (
                  <div className="mt-2 space-y-2">
                    {resolvedComments.map((note) => (
                      <div key={note.id} className="rounded-xl border p-3 opacity-60" style={{ borderColor: "rgba(192, 192, 192, 0.03)", background: "rgba(255, 255, 255, 0.01)" }}>
                        <div className="mb-1 flex items-center gap-2">
                          <span className="text-xs" style={{ color: "#7a7a90" }}>{note.authorName}</span>
                          <span className="text-[10px]" style={{ color: "#14b8a6" }}>✓ resolved</span>
                        </div>
                        <p className="text-xs" style={{ color: "#5a5a6e" }}>{note.text}</p>
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
