import { useEffect, useState } from "react";
import type { Band, Project, Song, User } from "../lib/types";

interface SongDetailPageProps {
  user: User;
  band: Band;
  project: Project;
  song: Song;
  onOpenPlayer: () => void;
  onBack: () => void;
  onDownloadStem?: (stemId: string) => void;
  onDownloadAllStems?: () => void;
  onUploadStem?: (payload: { stemKey: string; file: File }) => Promise<void> | void;
  onGenerateStems?: () => Promise<void> | void;
  onGenerateBassTab?: (sourceStemKey: string) => Promise<void> | void;
}

const STATUS_STYLES: Record<string, { bg: string; text: string }> = {
  ready: { bg: "rgba(20, 184, 166, 0.15)", text: "#14b8a6" },
  processing: { bg: "rgba(124, 58, 237, 0.15)", text: "#a78bfa" },
  uploaded: { bg: "rgba(192, 192, 192, 0.1)", text: "#c0c0c0" },
  failed: { bg: "rgba(239, 68, 68, 0.15)", text: "#ef4444" },
  needs_review: { bg: "rgba(124, 58, 237, 0.2)", text: "#a78bfa" },
};

export function SongDetailPage({
  user,
  band,
  project,
  song,
  onOpenPlayer,
  onBack,
  onDownloadStem,
  onDownloadAllStems,
  onUploadStem,
  onGenerateStems,
  onGenerateBassTab,
}: SongDetailPageProps) {
  const [showResolved, setShowResolved] = useState(false);
  const [openPanel, setOpenPanel] = useState<"upload" | "stems" | "tabs" | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);
  const activeStems = song.stems.filter((s) => !s.isArchived);
  const archivedStems = song.stems.filter((s) => s.isArchived);
  const openComments = song.notes.filter((n) => !n.resolved);
  const resolvedComments = song.notes.filter((n) => n.resolved);
  const ss = STATUS_STYLES[song.status] ?? STATUS_STYLES.uploaded;
  const tabEligibleStems = activeStems.filter((stem) => stem.stemKey !== "drums");
  const defaultTabStemKey = tabEligibleStems.find((stem) => stem.stemKey === "bass")?.stemKey ?? tabEligibleStems[0]?.stemKey ?? "";
  const [selectedTabStemKey, setSelectedTabStemKey] = useState(defaultTabStemKey);
  const [uploadStemKey, setUploadStemKey] = useState(defaultTabStemKey || "bass");
  const [uploadFile, setUploadFile] = useState<File | null>(null);

  useEffect(() => {
    setSelectedTabStemKey(defaultTabStemKey);
    setUploadStemKey(defaultTabStemKey || "bass");
  }, [defaultTabStemKey]);

  function resetUploadState() {
    setUploadFile(null);
    setUploadStemKey(defaultTabStemKey || "bass");
  }

  function togglePanel(panel: "upload" | "stems" | "tabs") {
    const nextPanel = openPanel === panel ? null : panel;
    if (openPanel === "upload" || nextPanel === "upload") {
      resetUploadState();
    }
    setOpenPanel(nextPanel);
    setActionError(null);
    setActionSuccess(null);
  }

  const currentTabSourceLabel = song.tab?.sourceDisplayName?.trim() || song.tab?.sourceStemKey || null;

  async function runAction(action: () => Promise<void>, successMessage: string) {
    setActionError(null);
    setActionSuccess(null);
    setIsSubmitting(true);
    try {
      await action();
      setActionSuccess(successMessage);
    } catch (error) {
      setActionError(error instanceof Error ? error.message : "Action failed");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="me-mesh min-h-screen" style={{ background: "linear-gradient(160deg, #0a0e27 0%, #111638 40%, #0a0e27 100%)" }}>
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
              <span className="px-3 py-1 text-xs font-medium" style={{ borderRadius: "2px", background: ss.bg, color: ss.text }}>{song.status}</span>
            </div>
            <h1 className="text-4xl" style={{ fontFamily: "Playfair Display, serif", color: "#e2e2f0" }}>{song.title}</h1>
            <p className="mt-1 text-lg" style={{ color: "#c0c0c0" }}>{song.artist}</p>
            <div className="mt-3 flex items-center gap-5 text-sm" style={{ color: "#7a7a90" }}>
              <span>Key: <strong style={{ color: "#e2e2f0" }}>{song.key}</strong></span>
              <span>Tempo: <strong style={{ color: "#e2e2f0" }}>{song.tempo} BPM</strong></span>
              <span>Duration: <strong style={{ color: "#e2e2f0" }}>{Math.floor(song.duration / 60)}:{String(Math.floor(song.duration % 60)).padStart(2, "0")}</strong></span>
              <span>Chords: <strong style={{ color: "#e2e2f0" }}>{song.chords.length}</strong></span>
            </div>
          </div>
          {song.status === "ready" && (
            <button onClick={onOpenPlayer} className="px-8 py-3.5 text-base font-semibold text-white shadow-lg transition-all hover:brightness-110 hover:shadow-xl hover:shadow-purple-500/20" style={{ borderRadius: "3px", background: "linear-gradient(135deg, #7c3aed, #5b21b6)" }}>
              ▶ Open Player
            </button>
          )}
        </div>

        <div className="grid grid-cols-3 gap-8">
          {/* Stems column */}
          <div className="col-span-2">
            <h2 className="mb-4 text-lg" style={{ fontFamily: "Playfair Display, serif", color: "#e2e2f0" }}>Stems</h2>
            {activeStems.length === 0 ? (
              <p className="text-sm" style={{ color: "#7a7a90" }}>No stems available yet.</p>
            ) : (
              <div className="space-y-2">
                {activeStems.map((stem) => (
                  <div key={stem.id} className="flex items-center gap-4 border p-4" style={{ borderRadius: "3px", borderColor: "rgba(192, 192, 192, 0.05)", background: "rgba(255, 255, 255, 0.02)", backdropFilter: "blur(8px)" }}>
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
                      <div className="mt-0.5 text-xs" style={{ color: "#7a7a90" }}>
                        {stem.description}
                        {stem.uploaderName ? ` - by ${stem.uploaderName}` : ""}
                      </div>
                    </div>
                    <button
                      onClick={() => onDownloadStem?.(stem.stemKey)}
                      className="rounded-lg border px-3 py-1.5 text-xs transition-all hover:bg-white/5 hover:border-purple-500/30"
                      style={{ borderColor: "rgba(192, 192, 192, 0.12)", color: "#c0c0c0" }}
                    >
                      Download
                    </button>
                  </div>
                ))}
              </div>
            )}

            {archivedStems.length > 0 && (
              <div className="mt-4">
                <h3 className="mb-2 text-xs font-medium" style={{ fontFamily: "Playfair Display, serif", color: "#5a5a6e" }}>Archived ({archivedStems.length})</h3>
                {archivedStems.map((stem) => (
                  <div key={stem.id} className="flex items-center gap-4 rounded-lg p-3 opacity-50" style={{ background: "rgba(255, 255, 255, 0.01)" }}>
                    <span className="text-sm" style={{ color: "#7a7a90" }}>{stem.label} v{stem.version} — {stem.description}</span>
                  </div>
                ))}
              </div>
            )}

            {/* Upload actions */}
            <div className="mt-6 flex gap-3">
              <button
                onClick={onDownloadAllStems}
                className="border px-5 py-2.5 text-sm font-medium transition-all hover:bg-white/5 hover:border-purple-500/30"
                style={{ borderRadius: "3px", borderColor: "rgba(20, 184, 166, 0.35)", color: "#14b8a6" }}
              >
                Download All Stems
              </button>
              <button
                onClick={() => togglePanel("upload")}
                className="border px-5 py-2.5 text-sm font-medium transition-all hover:bg-white/5 hover:border-purple-500/30"
                style={{ borderRadius: "3px", borderColor: openPanel === "upload" ? "rgba(20, 184, 166, 0.35)" : "rgba(192, 192, 192, 0.1)", color: openPanel === "upload" ? "#14b8a6" : "#c0c0c0" }}
              >
                Upload Stem
              </button>
              <button
                onClick={() => togglePanel("stems")}
                className="border px-5 py-2.5 text-sm font-medium transition-all hover:bg-white/5 hover:border-purple-500/30"
                style={{ borderRadius: "3px", borderColor: openPanel === "stems" ? "rgba(20, 184, 166, 0.35)" : "rgba(192, 192, 192, 0.1)", color: openPanel === "stems" ? "#14b8a6" : "#c0c0c0" }}
              >
                Generate Stems
              </button>
              <button
                onClick={() => togglePanel("tabs")}
                className="border px-5 py-2.5 text-sm font-medium transition-all hover:bg-white/5 hover:border-purple-500/30"
                style={{ borderRadius: "3px", borderColor: openPanel === "tabs" ? "rgba(20, 184, 166, 0.35)" : "rgba(192, 192, 192, 0.1)", color: openPanel === "tabs" ? "#14b8a6" : "#c0c0c0" }}
              >
                Generate Bass Tab
              </button>
            </div>

            <div className="mt-6 border p-4" style={{ borderRadius: "3px", borderColor: "rgba(192, 192, 192, 0.05)", background: "rgba(255, 255, 255, 0.02)", backdropFilter: "blur(8px)" }}>
              {song.tab ? (
                <>
                  <h3 className="text-sm font-semibold" style={{ color: "#e2e2f0" }}>Current bass tab</h3>
                  <p className="mt-2 text-sm" style={{ color: "#c0c0c0" }}>
                    {currentTabSourceLabel ? `Generated from ${currentTabSourceLabel}.` : "Generated from the current active source stem."}
                  </p>
                  <div className="mt-2 flex flex-wrap gap-2 text-xs" style={{ color: "#7a7a90" }}>
                    <span>Status: {song.tab.status}</span>
                    <span>Provenance: {song.tab.sourceType}</span>
                    <span>Generator: {song.tab.generatorVersion}</span>
                    <span>Updated: {song.tab.updatedAt}</span>
                  </div>
                  {song.tab.errorMessage ? <p className="mt-2 text-sm" style={{ color: "#ef4444" }}>{song.tab.errorMessage}</p> : null}
                </>
              ) : (
                <>
                  <h3 className="text-sm font-semibold" style={{ color: "#e2e2f0" }}>No generated bass tab yet</h3>
                  <p className="mt-2 text-sm" style={{ color: "#7a7a90" }}>
                    Tab provenance will appear after a successful tab generation run.
                  </p>
                </>
              )}
            </div>

            {openPanel === "upload" && (
              <div className="mt-4 border p-4" style={{ borderRadius: "3px", borderColor: "rgba(20, 184, 166, 0.2)", background: "rgba(20, 184, 166, 0.06)" }}>
                <h3 className="text-sm font-semibold" style={{ color: "#e2e2f0" }}>Upload Replacement Stem</h3>
                <p className="mt-2 text-sm" style={{ color: "#c0c0c0" }}>
                  Upload a file for the active stem role. The newest active asset replaces the current role on this page.
                </p>
                <div className="mt-4 grid gap-4">
                  <label className="grid gap-1 text-sm" style={{ color: "#e2e2f0" }}>
                    <span>Stem Role</span>
                    <select
                      aria-label="Stem Role"
                      value={uploadStemKey}
                      onChange={(event) => setUploadStemKey(event.target.value)}
                      className="border px-3 py-2"
                      style={{ borderRadius: "3px", borderColor: "rgba(192, 192, 192, 0.12)", background: "rgba(10, 14, 39, 0.7)", color: "#e2e2f0" }}
                    >
                      {Array.from(new Set(["bass", ...activeStems.map((stem) => stem.stemKey)])).map((stemKey) => (
                        <option key={stemKey} value={stemKey}>{stemKey}</option>
                      ))}
                    </select>
                  </label>
                  <label className="grid gap-1 text-sm" style={{ color: "#e2e2f0" }}>
                    <span>Stem File</span>
                    <input
                      aria-label="Stem File"
                      type="file"
                      accept="audio/*"
                      onChange={(event) => setUploadFile(event.target.files?.[0] ?? null)}
                      className="border px-3 py-2"
                      style={{ borderRadius: "3px", borderColor: "rgba(192, 192, 192, 0.12)", background: "rgba(10, 14, 39, 0.7)", color: "#e2e2f0" }}
                    />
                  </label>
                </div>
                {actionError && <p className="mt-3 text-sm" style={{ color: "#ef4444" }}>{actionError}</p>}
                {actionSuccess && <p className="mt-3 text-sm" style={{ color: "#14b8a6" }}>{actionSuccess}</p>}
                <div className="mt-4 flex gap-3">
                  <button
                    onClick={() => {
                      void runAction(async () => {
                        if (!uploadFile) throw new Error("Select a stem file");
                        await onUploadStem?.({ stemKey: uploadStemKey, file: uploadFile });
                        resetUploadState();
                      }, "Stem uploaded.");
                    }}
                    disabled={isSubmitting}
                    className="border px-4 py-2 text-sm font-medium transition-all disabled:opacity-60"
                    style={{ borderRadius: "3px", borderColor: "rgba(20, 184, 166, 0.35)", color: "#14b8a6" }}
                  >
                    {isSubmitting ? "Uploading..." : "Confirm Stem Upload"}
                  </button>
                  <button
                    onClick={() => togglePanel("upload")}
                    disabled={isSubmitting}
                    className="border px-4 py-2 text-sm font-medium transition-all disabled:opacity-60"
                    style={{ borderRadius: "3px", borderColor: "rgba(192, 192, 192, 0.1)", color: "#c0c0c0" }}
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}

            {openPanel === "stems" && (
              <div className="mt-4 border p-4" style={{ borderRadius: "3px", borderColor: "rgba(20, 184, 166, 0.2)", background: "rgba(20, 184, 166, 0.06)" }}>
                <h3 className="text-sm font-semibold" style={{ color: "#e2e2f0" }}>Regenerate System Stems</h3>
                <p className="mt-2 text-sm" style={{ color: "#c0c0c0" }}>
                  This regenerates system stems from the original uploaded mix. Existing stem records are refreshed in place.
                </p>
                {actionError && <p className="mt-3 text-sm" style={{ color: "#ef4444" }}>{actionError}</p>}
                {actionSuccess && <p className="mt-3 text-sm" style={{ color: "#14b8a6" }}>{actionSuccess}</p>}
                <div className="mt-4 flex gap-3">
                  <button
                    onClick={() => void runAction(async () => { await onGenerateStems?.(); }, "Stems regenerated.")}
                    disabled={isSubmitting}
                    className="border px-4 py-2 text-sm font-medium transition-all disabled:opacity-60"
                    style={{ borderRadius: "3px", borderColor: "rgba(20, 184, 166, 0.35)", color: "#14b8a6" }}
                  >
                    {isSubmitting ? "Generating..." : "Confirm Stem Generation"}
                  </button>
                  <button
                    onClick={() => setOpenPanel(null)}
                    disabled={isSubmitting}
                    className="border px-4 py-2 text-sm font-medium transition-all disabled:opacity-60"
                    style={{ borderRadius: "3px", borderColor: "rgba(192, 192, 192, 0.1)", color: "#c0c0c0" }}
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}

            {openPanel === "tabs" && (
              <div className="mt-4 border p-4" style={{ borderRadius: "3px", borderColor: "rgba(20, 184, 166, 0.2)", background: "rgba(20, 184, 166, 0.06)" }}>
                <h3 className="text-sm font-semibold" style={{ color: "#e2e2f0" }}>Generate Bass Tab</h3>
                <p className="mt-2 text-sm" style={{ color: "#c0c0c0" }}>
                  Choose the stem to use as the bass-tab source. Bass is selected by default when available.
                </p>
                <div className="mt-4 space-y-2">
                  {tabEligibleStems.length === 0 ? (
                    <p className="text-sm" style={{ color: "#ef4444" }}>No eligible stems available for tab generation.</p>
                  ) : (
                    tabEligibleStems.map((stem) => (
                      <label key={stem.id} className="flex items-center gap-3 border px-3 py-2 text-sm" style={{ borderRadius: "3px", borderColor: "rgba(192, 192, 192, 0.08)", color: "#e2e2f0" }}>
                        <input
                          type="radio"
                          name="tab-source-stem"
                          aria-label={stem.label}
                          value={stem.stemKey}
                          checked={selectedTabStemKey === stem.stemKey}
                          onChange={() => setSelectedTabStemKey(stem.stemKey)}
                        />
                        <span>{stem.label}</span>
                        <span style={{ color: "#7a7a90" }}>{stem.description}</span>
                      </label>
                    ))
                  )}
                </div>
                {actionError && <p className="mt-3 text-sm" style={{ color: "#ef4444" }}>{actionError}</p>}
                {actionSuccess && <p className="mt-3 text-sm" style={{ color: "#14b8a6" }}>{actionSuccess}</p>}
                <div className="mt-4 flex gap-3">
                  <button
                    onClick={() => {
                      const selectedStem = tabEligibleStems.find((stem) => stem.stemKey === selectedTabStemKey);
                      void runAction(
                        async () => {
                          if (!selectedStem) throw new Error("Select a source stem");
                          await onGenerateBassTab?.(selectedStem.stemKey);
                        },
                        `Bass tab regenerated from ${tabEligibleStems.find((stem) => stem.stemKey === selectedTabStemKey)?.label ?? selectedTabStemKey}.`,
                      );
                    }}
                    disabled={isSubmitting || !selectedTabStemKey}
                    className="border px-4 py-2 text-sm font-medium transition-all disabled:opacity-60"
                    style={{ borderRadius: "3px", borderColor: "rgba(20, 184, 166, 0.35)", color: "#14b8a6" }}
                  >
                    {isSubmitting ? "Generating..." : "Confirm Tab Generation"}
                  </button>
                  <button
                    onClick={() => setOpenPanel(null)}
                    disabled={isSubmitting}
                    className="border px-4 py-2 text-sm font-medium transition-all disabled:opacity-60"
                    style={{ borderRadius: "3px", borderColor: "rgba(192, 192, 192, 0.1)", color: "#c0c0c0" }}
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Comments column */}
          <div>
            <h2 className="mb-4 text-lg" style={{ fontFamily: "Playfair Display, serif", color: "#e2e2f0" }}>Comments</h2>
            {openComments.length === 0 && <p className="text-sm" style={{ color: "#7a7a90" }}>No open comments.</p>}
            <div className="space-y-3">
              {openComments.map((note) => (
                <div key={note.id} className="border-l-2 border p-4" style={{ borderRadius: "3px", borderColor: "rgba(192, 192, 192, 0.05)", borderLeftColor: "rgba(124, 58, 237, 0.5)", background: "rgba(255, 255, 255, 0.02)" }}>
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
                      <div key={note.id} className="border p-3 opacity-60" style={{ borderRadius: "3px", borderColor: "rgba(192, 192, 192, 0.03)", background: "rgba(255, 255, 255, 0.01)" }}>
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
