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
  ready: { bg: "rgba(0, 255, 65, 0.1)", text: "#00ff41" },
  processing: { bg: "rgba(0, 229, 255, 0.1)", text: "#00e5ff" },
  uploaded: { bg: "rgba(58, 58, 58, 0.3)", text: "#d0d0d0" },
  failed: { bg: "rgba(255, 0, 0, 0.15)", text: "#ff4444" },
  needs_review: { bg: "rgba(255, 0, 255, 0.1)", text: "#ff00ff" },
};

export function SongDetailPage({ user, band, project, song, onOpenPlayer, onBack }: SongDetailPageProps) {
  const [showResolved, setShowResolved] = useState(false);
  const activeStems = song.stems.filter((s) => !s.isArchived);
  const archivedStems = song.stems.filter((s) => s.isArchived);
  const openComments = song.notes.filter((n) => !n.resolved);
  const resolvedComments = song.notes.filter((n) => n.resolved);
  const ss = STATUS_STYLES[song.status] ?? STATUS_STYLES.uploaded;

  return (
    <div className="scanlines min-h-screen" style={{ background: "#0a0a0a" }}>
      {/* Header */}
      <nav className="relative z-10 flex items-center justify-between border-b px-8 py-4" style={{ borderColor: "rgba(0, 255, 65, 0.1)" }}>
        <div className="flex items-center gap-4">
          <button onClick={onBack} className="font-mono text-sm transition-colors hover:text-green-300" style={{ color: "#00ff41" }}>&lt;-- song-library</button>
          <div className="h-4 w-px" style={{ background: "rgba(0, 255, 65, 0.2)" }} />
          <span className="font-mono text-xs" style={{ color: "#3a3a3a" }}>{band.name} / {project.name}</span>
        </div>
        <div className="flex h-7 w-7 items-center justify-center border text-[10px] font-bold" style={{ borderColor: "#00ff41", color: "#00ff41" }}>{user.avatar}</div>
      </nav>

      <main className="relative z-10 mx-auto max-w-5xl px-8 pt-8">
        {/* Song header */}
        <div className="mb-8 flex items-start justify-between">
          <div>
            <div className="mb-2 flex items-center gap-3">
              <span className="border px-3 py-1 font-mono text-xs font-medium" style={{ background: ss.bg, color: ss.text, borderColor: ss.text + "33" }}>{song.status}</span>
            </div>
            <h1 className="text-4xl" style={{ fontFamily: "Outfit, sans-serif", color: "#e8e8e8" }}>{song.title}</h1>
            <p className="mt-1 text-lg" style={{ color: "#00e5ff" }}>{song.artist}</p>
            <div className="mt-3 flex items-center gap-5 font-mono text-sm" style={{ color: "#3a3a3a" }}>
              <span>key: <strong style={{ color: "#00ff41" }}>{song.key}</strong></span>
              <span>tempo: <strong style={{ color: "#00ff41" }}>{song.tempo} BPM</strong></span>
              <span>dur: <strong style={{ color: "#00ff41" }}>{Math.floor(song.duration / 60)}:{String(Math.floor(song.duration % 60)).padStart(2, "0")}</strong></span>
              <span>chords: <strong style={{ color: "#00ff41" }}>{song.chords.length}</strong></span>
            </div>
          </div>
          {song.status === "ready" && (
            <button onClick={onOpenPlayer} className="border-2 px-8 py-3.5 font-mono text-base font-semibold transition-all hover:bg-green-900/20" style={{ borderColor: "#00ff41", color: "#00ff41", background: "rgba(0, 255, 65, 0.05)", boxShadow: "0 0 20px rgba(0, 255, 65, 0.15)" }}>
              &gt; open-player
            </button>
          )}
        </div>

        <div className="grid grid-cols-3 gap-8">
          {/* Stems column */}
          <div className="col-span-2">
            <h2 className="mb-4 text-lg" style={{ fontFamily: "Outfit, sans-serif", color: "#e8e8e8" }}>Stems</h2>
            {activeStems.length === 0 ? (
              <p className="font-mono text-sm" style={{ color: "#3a3a3a" }}>// no stems available yet</p>
            ) : (
              <div className="space-y-2">
                {activeStems.map((stem) => (
                  <div key={stem.id} className="flex items-center gap-4 border p-4" style={{ borderColor: "rgba(0, 255, 65, 0.06)", background: "rgba(0, 255, 65, 0.02)" }}>
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center border font-mono text-sm font-bold" style={{ borderColor: stem.sourceType === "System" ? "#00ff41" : "#00e5ff", color: stem.sourceType === "System" ? "#00ff41" : "#00e5ff" }}>
                      {stem.label.charAt(0)}
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-semibold" style={{ color: "#e8e8e8" }}>{stem.label}</span>
                        <span className="border px-1.5 py-0.5 font-mono text-[10px]" style={{ borderColor: "rgba(0, 255, 65, 0.1)", color: "#3a3a3a" }}>v{stem.version}</span>
                        <span className="border px-1.5 py-0.5 font-mono text-[10px]" style={{ borderColor: stem.sourceType === "System" ? "rgba(0, 255, 65, 0.2)" : "rgba(0, 229, 255, 0.2)", color: stem.sourceType === "System" ? "#00ff41" : "#00e5ff" }}>
                          {stem.sourceType}
                        </span>
                      </div>
                      <div className="mt-0.5 font-mono text-xs" style={{ color: "#3a3a3a" }}>{stem.description} -- by {stem.uploaderName}</div>
                    </div>
                    <button className="border px-3 py-1.5 font-mono text-xs transition-colors hover:bg-green-900/20" style={{ borderColor: "rgba(0, 255, 65, 0.2)", color: "#00ff41" }}>
                      download
                    </button>
                  </div>
                ))}
              </div>
            )}

            {archivedStems.length > 0 && (
              <div className="mt-4">
                <h3 className="mb-2 font-mono text-xs font-medium uppercase tracking-widest" style={{ color: "#3a3a3a" }}>// archived ({archivedStems.length})</h3>
                {archivedStems.map((stem) => (
                  <div key={stem.id} className="flex items-center gap-4 p-3 opacity-50" style={{ background: "rgba(17, 17, 17, 0.5)" }}>
                    <span className="font-mono text-sm" style={{ color: "#3a3a3a" }}>{stem.label} v{stem.version} -- {stem.description}</span>
                  </div>
                ))}
              </div>
            )}

            {/* Upload actions */}
            <div className="mt-6 flex gap-3">
              <button className="border px-5 py-2.5 font-mono text-sm font-medium transition-colors hover:bg-green-900/15" style={{ borderColor: "rgba(0, 255, 65, 0.2)", color: "#00ff41" }}>
                upload-stem
              </button>
              <button className="border px-5 py-2.5 font-mono text-sm font-medium transition-colors hover:bg-cyan-900/15" style={{ borderColor: "rgba(0, 229, 255, 0.2)", color: "#00e5ff" }}>
                generate-stems
              </button>
              <button className="border px-5 py-2.5 font-mono text-sm font-medium transition-colors hover:bg-fuchsia-900/15" style={{ borderColor: "rgba(255, 0, 255, 0.2)", color: "#ff00ff" }}>
                generate-tab
              </button>
            </div>
          </div>

          {/* Comments column */}
          <div>
            <h2 className="mb-4 text-lg" style={{ fontFamily: "Outfit, sans-serif", color: "#e8e8e8" }}>Comments</h2>
            {openComments.length === 0 && <p className="font-mono text-sm" style={{ color: "#3a3a3a" }}>// no open comments</p>}
            <div className="space-y-3">
              {openComments.map((note) => (
                <div key={note.id} className="border p-4" style={{ borderColor: "rgba(0, 229, 255, 0.15)", background: "rgba(0, 229, 255, 0.03)" }}>
                  <div className="mb-2 flex items-center gap-2">
                    <div className="flex h-6 w-6 items-center justify-center border text-[9px] font-bold" style={{ borderColor: "#00e5ff", color: "#00e5ff" }}>{note.authorAvatar}</div>
                    <span className="text-xs font-semibold" style={{ color: "#e8e8e8" }}>{note.authorName}</span>
                    <span className="font-mono text-[10px]" style={{ color: "#3a3a3a" }}>{note.type === "time" ? `@${note.timestampSec?.toFixed(1)}s` : `chord[${(note.chordIndex ?? 0) + 1}]`}</span>
                  </div>
                  <p className="text-sm leading-relaxed" style={{ color: "#d0d0d0" }}>{note.text}</p>
                </div>
              ))}
            </div>

            {resolvedComments.length > 0 && (
              <div className="mt-4">
                <button onClick={() => setShowResolved(!showResolved)} className="font-mono text-xs font-medium transition-colors hover:text-green-300" style={{ color: "#3a3a3a" }}>
                  {showResolved ? "hide" : "show"} resolved ({resolvedComments.length})
                </button>
                {showResolved && (
                  <div className="mt-2 space-y-2">
                    {resolvedComments.map((note) => (
                      <div key={note.id} className="border p-3 opacity-60" style={{ borderColor: "rgba(0, 255, 65, 0.05)", background: "rgba(17, 17, 17, 0.3)" }}>
                        <div className="mb-1 flex items-center gap-2">
                          <span className="font-mono text-xs" style={{ color: "#3a3a3a" }}>{note.authorName}</span>
                          <span className="font-mono text-[10px]" style={{ color: "#00ff41" }}>[resolved]</span>
                        </div>
                        <p className="font-mono text-xs" style={{ color: "#3a3a3a" }}>{note.text}</p>
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
