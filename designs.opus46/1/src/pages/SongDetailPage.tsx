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
  ready: { bg: "rgba(107, 114, 52, 0.2)", text: "#a3b236" },
  processing: { bg: "rgba(180, 83, 9, 0.2)", text: "#d97706" },
  uploaded: { bg: "rgba(196, 168, 130, 0.15)", text: "#c4a882" },
  failed: { bg: "rgba(180, 40, 40, 0.2)", text: "#ef4444" },
  needs_review: { bg: "rgba(139, 92, 246, 0.2)", text: "#a78bfa" },
};

export function SongDetailPage({ user, band, project, song, onOpenPlayer, onBack }: SongDetailPageProps) {
  const [showResolved, setShowResolved] = useState(false);
  const activeStems = song.stems.filter((s) => !s.isArchived);
  const archivedStems = song.stems.filter((s) => s.isArchived);
  const openComments = song.notes.filter((n) => !n.resolved);
  const resolvedComments = song.notes.filter((n) => n.resolved);
  const ss = STATUS_STYLES[song.status] ?? STATUS_STYLES.uploaded;

  return (
    <div className="vinyl-noise min-h-screen" style={{ background: "linear-gradient(160deg, #1a1209 0%, #2d1f0e 40%, #1a1209 100%)" }}>
      {/* Header */}
      <nav className="relative z-10 flex items-center justify-between border-b px-8 py-4" style={{ borderColor: "rgba(196, 168, 130, 0.1)" }}>
        <div className="flex items-center gap-4">
          <button onClick={onBack} className="text-sm transition-colors hover:text-amber-300" style={{ color: "#c4a882" }}>← Song Library</button>
          <div className="h-4 w-px" style={{ background: "rgba(196, 168, 130, 0.2)" }} />
          <span className="text-xs" style={{ color: "#8b7d6b" }}>{band.name} / {project.name}</span>
        </div>
        <div className="flex h-7 w-7 items-center justify-center rounded-full text-[10px] font-bold text-white" style={{ background: "#b45309" }}>{user.avatar}</div>
      </nav>

      <main className="relative z-10 mx-auto max-w-5xl px-8 pt-8">
        {/* Song header */}
        <div className="mb-8 flex items-start justify-between">
          <div>
            <div className="mb-2 flex items-center gap-3">
              <span className="rounded-full px-3 py-1 text-xs font-medium" style={{ background: ss.bg, color: ss.text }}>{song.status}</span>
            </div>
            <h1 className="text-4xl" style={{ fontFamily: "DM Serif Display, serif", color: "#faf5eb" }}>{song.title}</h1>
            <p className="mt-1 text-lg" style={{ color: "#c4a882" }}>{song.artist}</p>
            <div className="mt-3 flex items-center gap-5 text-sm" style={{ color: "#8b7d6b" }}>
              <span>Key: <strong style={{ color: "#faf5eb" }}>{song.key}</strong></span>
              <span>Tempo: <strong style={{ color: "#faf5eb" }}>{song.tempo} BPM</strong></span>
              <span>Duration: <strong style={{ color: "#faf5eb" }}>{Math.floor(song.duration / 60)}:{String(Math.floor(song.duration % 60)).padStart(2, "0")}</strong></span>
              <span>Chords: <strong style={{ color: "#faf5eb" }}>{song.chords.length}</strong></span>
            </div>
          </div>
          {song.status === "ready" && (
            <button onClick={onOpenPlayer} className="rounded-xl px-8 py-3.5 text-base font-semibold text-white shadow-lg transition-all hover:brightness-110 hover:shadow-xl" style={{ background: "linear-gradient(135deg, #b45309, #92400e)" }}>
              ▶ Open Player
            </button>
          )}
        </div>

        <div className="grid grid-cols-3 gap-8">
          {/* Stems column */}
          <div className="col-span-2">
            <h2 className="mb-4 text-lg" style={{ fontFamily: "DM Serif Display, serif", color: "#faf5eb" }}>Stems</h2>
            {activeStems.length === 0 ? (
              <p className="text-sm" style={{ color: "#8b7d6b" }}>No stems available yet.</p>
            ) : (
              <div className="space-y-2">
                {activeStems.map((stem) => (
                  <div key={stem.id} className="flex items-center gap-4 rounded-xl border p-4" style={{ borderColor: "rgba(196, 168, 130, 0.08)", background: "rgba(26, 18, 9, 0.5)" }}>
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-sm font-bold" style={{ background: stem.sourceType === "System" ? "rgba(107, 114, 52, 0.2)" : "rgba(180, 83, 9, 0.2)", color: stem.sourceType === "System" ? "#a3b236" : "#d97706" }}>
                      {stem.label.charAt(0)}
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-semibold" style={{ color: "#faf5eb" }}>{stem.label}</span>
                        <span className="rounded px-1.5 py-0.5 text-[10px]" style={{ background: "rgba(196, 168, 130, 0.1)", color: "#8b7d6b" }}>v{stem.version}</span>
                        <span className="rounded px-1.5 py-0.5 text-[10px]" style={{ background: stem.sourceType === "System" ? "rgba(107, 114, 52, 0.15)" : "rgba(180, 83, 9, 0.15)", color: stem.sourceType === "System" ? "#a3b236" : "#d97706" }}>
                          {stem.sourceType}
                        </span>
                      </div>
                      <div className="mt-0.5 text-xs" style={{ color: "#8b7d6b" }}>{stem.description} — by {stem.uploaderName}</div>
                    </div>
                    <button className="rounded-lg border px-3 py-1.5 text-xs transition-colors hover:bg-white/5" style={{ borderColor: "rgba(196, 168, 130, 0.2)", color: "#c4a882" }}>
                      Download
                    </button>
                  </div>
                ))}
              </div>
            )}

            {archivedStems.length > 0 && (
              <div className="mt-4">
                <h3 className="mb-2 text-xs font-medium uppercase tracking-widest" style={{ color: "#6b5d4e" }}>Archived ({archivedStems.length})</h3>
                {archivedStems.map((stem) => (
                  <div key={stem.id} className="flex items-center gap-4 rounded-lg p-3 opacity-50" style={{ background: "rgba(26, 18, 9, 0.3)" }}>
                    <span className="text-sm" style={{ color: "#8b7d6b" }}>{stem.label} v{stem.version} — {stem.description}</span>
                  </div>
                ))}
              </div>
            )}

            {/* Upload actions */}
            <div className="mt-6 flex gap-3">
              <button className="rounded-xl border px-5 py-2.5 text-sm font-medium transition-colors hover:bg-white/5" style={{ borderColor: "rgba(196, 168, 130, 0.2)", color: "#c4a882" }}>
                Upload Stem
              </button>
              <button className="rounded-xl border px-5 py-2.5 text-sm font-medium transition-colors hover:bg-white/5" style={{ borderColor: "rgba(196, 168, 130, 0.2)", color: "#c4a882" }}>
                Generate Stems
              </button>
              <button className="rounded-xl border px-5 py-2.5 text-sm font-medium transition-colors hover:bg-white/5" style={{ borderColor: "rgba(196, 168, 130, 0.2)", color: "#c4a882" }}>
                Generate Bass Tab
              </button>
            </div>
          </div>

          {/* Comments column */}
          <div>
            <h2 className="mb-4 text-lg" style={{ fontFamily: "DM Serif Display, serif", color: "#faf5eb" }}>Comments</h2>
            {openComments.length === 0 && <p className="text-sm" style={{ color: "#8b7d6b" }}>No open comments.</p>}
            <div className="space-y-3">
              {openComments.map((note) => (
                <div key={note.id} className="rounded-xl border p-4" style={{ borderColor: "rgba(196, 168, 130, 0.08)", background: "rgba(26, 18, 9, 0.5)" }}>
                  <div className="mb-2 flex items-center gap-2">
                    <div className="flex h-6 w-6 items-center justify-center rounded-full text-[9px] font-bold text-white" style={{ background: "#3d2b1f" }}>{note.authorAvatar}</div>
                    <span className="text-xs font-semibold" style={{ color: "#faf5eb" }}>{note.authorName}</span>
                    <span className="text-[10px]" style={{ color: "#6b5d4e" }}>{note.type === "time" ? `at ${note.timestampSec?.toFixed(1)}s` : `chord #${(note.chordIndex ?? 0) + 1}`}</span>
                  </div>
                  <p className="text-sm leading-relaxed" style={{ color: "#c4a882" }}>{note.text}</p>
                </div>
              ))}
            </div>

            {resolvedComments.length > 0 && (
              <div className="mt-4">
                <button onClick={() => setShowResolved(!showResolved)} className="text-xs font-medium transition-colors hover:text-amber-300" style={{ color: "#8b7d6b" }}>
                  {showResolved ? "Hide" : "Show"} resolved ({resolvedComments.length})
                </button>
                {showResolved && (
                  <div className="mt-2 space-y-2">
                    {resolvedComments.map((note) => (
                      <div key={note.id} className="rounded-xl border p-3 opacity-60" style={{ borderColor: "rgba(196, 168, 130, 0.05)", background: "rgba(26, 18, 9, 0.3)" }}>
                        <div className="mb-1 flex items-center gap-2">
                          <span className="text-xs" style={{ color: "#8b7d6b" }}>{note.authorName}</span>
                          <span className="text-[10px]" style={{ color: "#6b7234" }}>✓ resolved</span>
                        </div>
                        <p className="text-xs" style={{ color: "#6b5d4e" }}>{note.text}</p>
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
