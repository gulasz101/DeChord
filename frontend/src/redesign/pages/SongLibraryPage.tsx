import { useRef, useState, type DragEvent } from "react";
import type { JobStatus, ProcessMode, TabGenerationQuality } from "../../lib/types";
import type { Band, Project, Song, User } from "../lib/types";

interface SongLibraryPageProps {
  user: User;
  band: Band;
  project: Project;
  onSelectSong: (s: Song) => void;
  onUploadSong?: (file: File, processMode: ProcessMode, tabGenerationQuality: TabGenerationQuality) => Promise<void> | void;
  onBack: () => void;
  uploadLoading?: boolean;
  uploadStatus?: Pick<JobStatus, "message" | "progress_pct" | "stage_progress_pct"> | null;
  uploadWarning?: string | null;
  uploadError?: string | null;
}

const STATUS_COLORS: Record<string, { bg: string; text: string; dot: string }> = {
  ready: { bg: "rgba(20, 184, 166, 0.12)", text: "#14b8a6", dot: "#0d9488" },
  processing: { bg: "rgba(124, 58, 237, 0.12)", text: "#a78bfa", dot: "#7c3aed" },
  uploaded: { bg: "rgba(192, 192, 192, 0.08)", text: "#c0c0c0", dot: "#8a8a9a" },
  failed: { bg: "rgba(239, 68, 68, 0.12)", text: "#ef4444", dot: "#dc2626" },
  needs_review: { bg: "rgba(124, 58, 237, 0.15)", text: "#a78bfa", dot: "#8b5cf6" },
};

export function SongLibraryPage({
  user,
  band,
  project,
  onSelectSong,
  onBack,
  onUploadSong,
  uploadLoading = false,
  uploadStatus = null,
  uploadWarning = null,
  uploadError = null,
}: SongLibraryPageProps) {
  const [showUpload, setShowUpload] = useState(false);
  const [processMode, setProcessMode] = useState<ProcessMode>("analysis_and_stems");
  const [tabQuality, setTabQuality] = useState<TabGenerationQuality>("standard");
  const [dragActive, setDragActive] = useState(false);
  const [stagedFile, setStagedFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const handleSelectedFile = (file: File | null | undefined) => {
    if (!file || uploadLoading) return;
    setStagedFile(file);
  };

  const handleStartUpload = () => {
    if (!stagedFile || !onUploadSong || uploadLoading) return;
    onUploadSong(stagedFile, processMode, tabQuality);
    setStagedFile(null);
  };

  const handleDrop = (event: DragEvent<HTMLButtonElement>) => {
    event.preventDefault();
    setDragActive(false);
    handleSelectedFile(event.dataTransfer.files?.[0]);
  };

  return (
    <div className="me-mesh min-h-screen" style={{ background: "linear-gradient(160deg, #0a0e27 0%, #111638 40%, #0a0e27 100%)" }}>
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

        {showUpload && (
          <div className="mb-6 border p-6" style={{ borderRadius: "4px", borderColor: "rgba(124, 58, 237, 0.2)", background: "rgba(124, 58, 237, 0.05)", backdropFilter: "blur(12px)" }}>
            <div className="flex items-start justify-between gap-4">
              <div>
                <h3 className="mb-1 text-sm font-semibold" style={{ fontFamily: "Playfair Display, serif", color: "#a78bfa", fontSize: "0.7rem" }}>Upload a Song</h3>
                <p className="text-xs" style={{ color: "#7a7a90" }}>Keep the 5-3 workflow, use the original analysis pipeline.</p>
              </div>
              {uploadLoading ? (
                <span className="rounded-full border px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.2em]" style={{ borderColor: "rgba(20, 184, 166, 0.25)", color: "#14b8a6", background: "rgba(20, 184, 166, 0.08)" }}>
                  Processing
                </span>
              ) : null}
            </div>

            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              onDragOver={(event) => { event.preventDefault(); setDragActive(true); }}
              onDragLeave={() => setDragActive(false)}
              onDrop={handleDrop}
              className="mt-4 flex w-full flex-col items-center rounded-xl border-2 border-dashed p-8 text-center transition-colors"
              style={{
                borderColor: dragActive ? "rgba(124, 58, 237, 0.55)" : "rgba(192, 192, 192, 0.15)",
                background: dragActive ? "rgba(124, 58, 237, 0.1)" : "rgba(255, 255, 255, 0.015)",
                color: "#c0c0c0",
              }}
            >
              <span className="text-sm">Drop an audio file here or click to browse</span>
              <span className="mt-1 text-xs" style={{ color: "#5a5a6e" }}>MP3, WAV, FLAC, M4A, AAC, MP4</span>
            </button>
            <input
              ref={fileInputRef}
              aria-label="Upload Song File"
              type="file"
              accept=".mp3,.wav,.flac,.m4a,.aac,.mp4"
              className="hidden"
              onChange={(event) => handleSelectedFile(event.target.files?.[0])}
            />

            <div className="mt-4 grid gap-4 md:grid-cols-[1fr_1fr]">
              <label className="block text-xs font-medium" style={{ color: "#c0c0c0" }}>
                <span className="mb-1 block">Process Mode</span>
                <select
                  aria-label="Process Mode"
                  value={processMode}
                  onChange={(event) => setProcessMode(event.target.value as ProcessMode)}
                  className="w-full rounded-lg border px-3 py-2 text-xs"
                  style={{ background: "rgba(10, 14, 39, 0.6)", borderColor: "rgba(192, 192, 192, 0.12)", color: "#e2e2f0" }}
                >
                  <option value="analysis_and_stems">Analyze + Split Stems</option>
                  <option value="analysis_only">Analyze Only</option>
                </select>
              </label>
              <label className="block text-xs font-medium" style={{ color: "#c0c0c0" }}>
                <span className="mb-1 block">Tab Quality</span>
                <select
                  aria-label="Tab Quality"
                  value={tabQuality}
                  onChange={(event) => setTabQuality(event.target.value as TabGenerationQuality)}
                  className="w-full rounded-lg border px-3 py-2 text-xs"
                  style={{ background: "rgba(10, 14, 39, 0.6)", borderColor: "rgba(192, 192, 192, 0.12)", color: "#e2e2f0" }}
                >
                  <option value="standard">Standard</option>
                  <option value="high_accuracy">High Accuracy</option>
                  <option value="high_accuracy_aggressive">High Accuracy Aggressive</option>
                </select>
              </label>
            </div>

            {stagedFile && (
              <div className="mt-4 flex items-center justify-between gap-4">
                <span className="text-xs truncate" style={{ color: "#c0c0c0" }}>{stagedFile.name}</span>
                <button
                  type="button"
                  onClick={handleStartUpload}
                  disabled={uploadLoading}
                  className="shrink-0 px-5 py-2 text-sm font-semibold text-white transition-all hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-50"
                  style={{ borderRadius: "3px", background: "linear-gradient(135deg, #14b8a6, #0f766e)" }}
                >
                  Start Upload
                </button>
              </div>
            )}

            {uploadStatus ? (
              <div className="mt-4 rounded border px-4 py-3 text-sm" style={{ borderColor: "rgba(20, 184, 166, 0.18)", background: "rgba(20, 184, 166, 0.06)", color: "#d7fff9" }}>
                <div className="font-semibold">{uploadStatus.message ?? "Processing..."}</div>
                <div className="mt-1 text-xs" style={{ color: "#8fe6d8" }}>
                  {Math.round(uploadStatus.progress_pct ?? 0)}% complete · Stage {Math.round(uploadStatus.stage_progress_pct ?? 0)}%
                </div>
              </div>
            ) : null}

            {uploadWarning ? (
              <div className="mt-3 rounded border px-4 py-3 text-sm" style={{ borderColor: "rgba(245, 158, 11, 0.22)", background: "rgba(245, 158, 11, 0.08)", color: "#f5d38a" }}>
                {uploadWarning}
              </div>
            ) : null}

            {uploadError ? (
              <div className="mt-3 rounded border px-4 py-3 text-sm" style={{ borderColor: "rgba(239, 68, 68, 0.22)", background: "rgba(239, 68, 68, 0.08)", color: "#ffb3b3" }}>
                {uploadError}
              </div>
            ) : null}
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
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg" style={{ background: sc.bg }}>
                  <div className="h-2.5 w-2.5 rounded-full" style={{ background: sc.dot }} />
                </div>

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
