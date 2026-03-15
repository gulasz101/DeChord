import { useState, useRef } from "react";
import type { SongSummary } from "../lib/types";
import type { ProcessMode, TabGenerationQuality } from "../lib/types";
import { ENABLE_TABS_UI } from "../lib/featureFlags";
import { ThreeDotMenu } from "./ThreeDotMenu";
import { RenameModal } from "./RenameModal";
import { updateSong, listProjectSongs } from "../lib/api";

interface SongLibraryPanelProps {
  songs: SongSummary[];
  selectedSongId: number | null;
  loading?: boolean;
  projectId: number;
  onSelect: (songId: number) => void;
  onUpload: (file: File, mode: ProcessMode, quality: TabGenerationQuality) => void;
  onSongsChange?: (songs: SongSummary[]) => void;
}

export function SongLibraryPanel({
  songs,
  selectedSongId,
  loading,
  projectId,
  onSelect,
  onUpload,
  onSongsChange,
}: SongLibraryPanelProps) {
  const [mode, setMode] = useState<ProcessMode>("analysis_only");
  const [tabQuality, setTabQuality] = useState<TabGenerationQuality>("standard");
  const [showArchived, setShowArchived] = useState(false);
  const [renamingSong, setRenamingSong] = useState<SongSummary | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  return (
    <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-3">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-slate-100">Song Library</h2>
        <div className="flex items-center gap-2">
          <label className="flex items-center gap-1.5 text-xs text-slate-400">
            <input
              type="checkbox"
              checked={showArchived}
              onChange={(e) => setShowArchived(e.target.checked)}
              className="rounded border-slate-600"
            />
            Show archived
          </label>
          <select
            name="library-process-mode"
            value={mode}
            onChange={(e) => setMode(e.target.value as ProcessMode)}
            className="rounded border border-slate-700 bg-slate-900 px-2 py-1 text-xs text-slate-200"
          >
            <option value="analysis_only">Analyze chords only</option>
            <option value="analysis_and_stems">Analyze + split stems</option>
          </select>
          <button
            type="button"
            className="cursor-pointer rounded-md bg-blue-600 px-2.5 py-1 text-xs font-semibold text-white hover:bg-blue-500"
            disabled={loading}
            onClick={() => fileInputRef.current?.click()}
          >
            {loading ? "Processing..." : "Upload"}
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".mp3,.wav,.m4a,.aac,.mp4"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) onUpload(file, mode, ENABLE_TABS_UI ? tabQuality : "standard");
            }}
            disabled={loading}
          />
        </div>
      </div>
      {ENABLE_TABS_UI ? (
        <div className="mb-3 rounded-lg border border-slate-700 bg-slate-900/70 p-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Advanced</p>
          <p className="mt-2 text-sm font-medium text-slate-100">Tab accuracy</p>
          <p className="mt-1 whitespace-pre-line text-xs text-slate-400">
            Runs an extra analysis pass in sections where bass is likely present but no notes were detected.
            Improves tabs for quiet or ghost-note passages, but increases processing time.
          </p>
          <label className="mt-3 flex items-center gap-2 text-sm text-slate-200">
            <input
              type="radio"
              name="library-tab-quality"
              value="standard"
              checked={tabQuality === "standard"}
              onChange={() => setTabQuality("standard")}
            />
            <span>Standard (faster)</span>
          </label>
          <label className="mt-2 flex items-center gap-2 text-sm text-slate-200">
            <input
              type="radio"
              name="library-tab-quality"
              value="high_accuracy"
              checked={tabQuality === "high_accuracy"}
              onChange={() => setTabQuality("high_accuracy")}
            />
            <span>High accuracy (slower)</span>
          </label>
          <label className="mt-2 flex items-center gap-2 text-sm text-slate-200">
            <input
              type="radio"
              name="library-tab-quality"
              value="high_accuracy_aggressive"
              checked={tabQuality === "high_accuracy_aggressive"}
              onChange={() => setTabQuality("high_accuracy_aggressive")}
            />
            <span>High accuracy aggressive (slowest)</span>
          </label>
        </div>
      ) : null}

      <div className="max-h-48 space-y-1 overflow-y-auto pr-1">
        {songs.length === 0 ? (
          <p className="text-xs text-slate-400">No songs yet. Upload one to get started.</p>
        ) : (
          songs.map((song) => {
            const active = song.id === selectedSongId;
            const isArchived = !!song.archived_at;
            if (isArchived && !showArchived) return null;
            return (
              <div
                key={song.id}
                className={`group flex w-full items-center gap-2 rounded-md border px-3 py-2 text-left transition-colors ${
                  active
                    ? "border-blue-500 bg-blue-500/20 text-blue-100"
                    : "border-slate-800 bg-slate-900 text-slate-300 hover:border-slate-700 hover:bg-slate-800"
                } ${isArchived ? "opacity-50" : ""}`}
              >
                <button
                  onClick={() => onSelect(song.id)}
                  className="flex-1 truncate"
                >
                  <div className="truncate text-sm font-medium">{song.title}</div>
                  <div className="text-xs text-slate-400">
                    {song.original_filename && (
                      <span className="mr-2 text-slate-500">{song.original_filename}</span>
                    )}
                    {song.key ?? "--"}
                    {song.tempo ? ` | ${song.tempo} BPM` : ""}
                  </div>
                </button>
                {isArchived && (
                  <span className="rounded bg-slate-700 px-1.5 py-0.5 text-[10px] text-slate-400">
                    Archived
                  </span>
                )}
                <ThreeDotMenu
                  items={[
                    { label: "Rename", onClick: () => setRenamingSong(song) },
                    {
                      label: isArchived ? "Unarchive" : "Archive",
                      onClick: async () => {
                        await updateSong(song.id, { archived: !isArchived });
                        const updated = await listProjectSongs(projectId, showArchived);
                        onSongsChange?.(updated.songs);
                      },
                    },
                  ]}
                />
              </div>
            );
          })
        )}
      </div>
      {renamingSong && (
        <RenameModal
          label="Song Title"
          currentName={renamingSong.title}
          originalFilename={renamingSong.original_filename}
          onSave={async (newName) => {
            await updateSong(renamingSong.id, { title: newName });
            const updated = await listProjectSongs(projectId, showArchived);
            onSongsChange?.(updated.songs);
          }}
          onClose={() => setRenamingSong(null)}
        />
      )}
    </section>
  );
}
