import { useState } from "react";
import type { Band, Project, Song, User } from "../lib/types";
import type { ProcessMode, TabGenerationQuality } from "../../lib/types";

interface SongLibraryPageProps {
  user: User;
  band: Band;
  project: Project;
  onSelectSong: (s: Song) => void;
  onUploadSong?: (file: File, processMode: ProcessMode, tabGenerationQuality: TabGenerationQuality) => Promise<void> | void;
  onBack: () => void;
}

const STATUS_COLORS: Record<string, { bg: string; text: string; dot: string }> = {
  ready: { bg: "rgba(20, 184, 166, 0.12)", text: "#14b8a6", dot: "#0d9488" },
  processing: { bg: "rgba(124, 58, 237, 0.12)", text: "#a78bfa", dot: "#7c3aed" },
  uploaded: { bg: "rgba(192, 192, 192, 0.08)", text: "#c0c0c0", dot: "#8a8a9a" },
  failed: { bg: "rgba(239, 68, 68, 0.12)", text: "#ef4444", dot: "#dc2626" },
  needs_review: { bg: "rgba(124, 58, 237, 0.15)", text: "#a78bfa", dot: "#8b5cf6" },
};

export function SongLibraryPage({ user, band, project, onSelectSong, onUploadSong, onBack }: SongLibraryPageProps) {
  const [showUpload, setShowUpload] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [processMode, setProcessMode] = useState<ProcessMode>("analysis_and_stems");
  const [tabGenerationQuality, setTabGenerationQuality] = useState<TabGenerationQuality>("standard");
  const [isUploading, setIsUploading] = useState(false);

  const startUpload = async () => {
    if (!selectedFile || !onUploadSong || isUploading) return;
    setIsUploading(true);
    try {
      await onUploadSong(selectedFile, processMode, tabGenerationQuality);
      setSelectedFile(null);
      setProcessMode("analysis_and_stems");
      setTabGenerationQuality("standard");
      setShowUpload(false);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="me-mesh min-h-screen" style={{ background: "linear-gradient(160deg, #0a0e27 0%, #111638 40%, #0a0e27 100%)" }}>
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
            <h1 className="text-3xl" style={{ fontFamily: "Playfair Display, serif", color: "#e2e2f0" }}>Song Library</h1>
            <p className="mt-1 text-sm" style={{ color: "#7a7a90" }}>{project.songs.length} songs in {project.name}</p>
          </div>
          <div className="flex gap-2">
            <button onClick={() => setShowUpload(!showUpload)} className="px-5 py-2.5 text-sm font-semibold text-white transition-all hover:brightness-110 hover:shadow-purple-500/20" style={{ borderRadius: "3px", background: "linear-gradient(135deg, #7c3aed, #5b21b6)" }}>
              + Upload Song
            </button>
          </div>
        </div>

        {/* Upload panel */}
        {showUpload && (
          <div className="mb-6 border p-6" style={{ borderRadius: "4px", borderColor: "rgba(124, 58, 237, 0.2)", background: "rgba(124, 58, 237, 0.05)", backdropFilter: "blur(12px)" }}>
            <h3 className="mb-3 text-sm font-semibold" style={{ fontFamily: "Playfair Display, serif", color: "#a78bfa", fontSize: "0.7rem" }}>Upload a Song</h3>
            <div className="flex items-center gap-4">
              <label className="flex-1 rounded-xl border-2 border-dashed p-8 text-center" style={{ borderColor: "rgba(192, 192, 192, 0.15)" }}>
                <span className="text-sm" style={{ color: "#c0c0c0" }}>Drop an audio file here or click to browse</span>
                <span className="mt-1 block text-xs" style={{ color: "#5a5a6e" }}>MP3, WAV, FLAC — up to 50MB</span>
                <span className="mt-3 block text-xs font-semibold uppercase tracking-[0.18em]" style={{ color: "#a78bfa" }}>
                  {selectedFile ? selectedFile.name : "Choose File"}
                </span>
                <input
                  aria-label="Song File"
                  type="file"
                  accept="audio/*"
                  className="sr-only"
                  onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
                />
              </label>
            </div>
            <div className="mt-4 flex items-center gap-4">
              <label className="text-xs font-medium" style={{ color: "#c0c0c0" }}>Process Mode:</label>
              <select
                aria-label="Process Mode"
                value={processMode}
                onChange={(event) => setProcessMode(event.target.value as ProcessMode)}
                className="rounded-lg border px-3 py-2 text-xs"
                style={{ background: "rgba(10, 14, 39, 0.6)", borderColor: "rgba(192, 192, 192, 0.12)", color: "#e2e2f0" }}
              >
                <option value="analysis_and_stems">Analyze + Split Stems</option>
                <option value="analysis_only">Analyze Only</option>
              </select>
              <label className="text-xs font-medium" style={{ color: "#c0c0c0" }}>Tab Quality:</label>
              <select
                aria-label="Tab Quality"
                value={tabGenerationQuality}
                onChange={(event) => setTabGenerationQuality(event.target.value as TabGenerationQuality)}
                className="rounded-lg border px-3 py-2 text-xs"
                style={{ background: "rgba(10, 14, 39, 0.6)", borderColor: "rgba(192, 192, 192, 0.12)", color: "#e2e2f0" }}
              >
                <option value="standard">Standard</option>
                <option value="high_accuracy">High Accuracy</option>
                <option value="high_accuracy_aggressive">High Accuracy Aggressive</option>
              </select>
            </div>
            <div className="mt-4 flex gap-3">
              <button
                onClick={() => {
                  setSelectedFile(null);
                  setShowUpload(false);
                }}
                className="px-4 py-2 text-sm transition-colors hover:text-white"
                style={{ color: "#7a7a90" }}
              >
                Cancel
              </button>
              <button
                onClick={() => void startUpload()}
                disabled={!selectedFile || isUploading}
                className="px-5 py-2.5 text-sm font-semibold text-white transition-all hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-50"
                style={{ borderRadius: "3px", background: "linear-gradient(135deg, #14b8a6, #0f766e)" }}
              >
                Start Upload
              </button>
            </div>
          </div>
        )}

        {/* Song list */}
        {project.songs.length === 0 && !showUpload && (
          <div className="mb-6 border border-dashed p-8 text-center" style={{ borderRadius: "4px", borderColor: "rgba(192, 192, 192, 0.12)", background: "rgba(255, 255, 255, 0.02)" }}>
            <h2 className="text-xl" style={{ fontFamily: "Playfair Display, serif", color: "#e2e2f0" }}>No Songs Yet</h2>
            <p className="mt-2 text-sm" style={{ color: "#7a7a90" }}>
              Upload the first track for this project to start analysis, stem generation, and bass tab work.
            </p>
          </div>
        )}

        <div className="space-y-3">
          {project.songs.map((song) => {
            const sc = STATUS_COLORS[song.status] ?? STATUS_COLORS.uploaded;
            const activeStems = song.stems.filter((s) => !s.isArchived);
            const openComments = song.notes.filter((n) => !n.resolved);
            return (
              <button key={song.id} onClick={() => onSelectSong(song)}
                className="group flex w-full items-center gap-5 border p-5 text-left transition-all hover:border-purple-500/30 hover:shadow-lg hover:shadow-purple-500/5"
                style={{ borderRadius: "4px", background: "rgba(255, 255, 255, 0.02)", borderColor: "rgba(192, 192, 192, 0.05)", backdropFilter: "blur(8px)" }}>
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
                    <span className="px-2.5 py-1 text-[10px] font-medium" style={{ borderRadius: "2px", background: "rgba(20, 184, 166, 0.12)", color: "#14b8a6" }}>
                      {activeStems.length} stems
                    </span>
                  )}
                  {openComments.length > 0 && (
                    <span className="px-2.5 py-1 text-[10px] font-medium" style={{ borderRadius: "2px", background: "rgba(124, 58, 237, 0.12)", color: "#a78bfa" }}>
                      {openComments.length} comments
                    </span>
                  )}
                  <span className="px-2.5 py-1 text-[10px] font-medium" style={{ borderRadius: "2px", background: sc.bg, color: sc.text }}>
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
