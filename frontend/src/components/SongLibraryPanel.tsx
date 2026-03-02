import { useState } from "react";
import type { SongSummary } from "../lib/types";
import type { ProcessMode } from "../lib/types";

interface SongLibraryPanelProps {
  songs: SongSummary[];
  selectedSongId: number | null;
  loading?: boolean;
  onSelect: (songId: number) => void;
  onUpload: (file: File, mode: ProcessMode) => void;
}

export function SongLibraryPanel({
  songs,
  selectedSongId,
  loading,
  onSelect,
  onUpload,
}: SongLibraryPanelProps) {
  const [mode, setMode] = useState<ProcessMode>("analysis_only");

  return (
    <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-3">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-slate-100">Song Library</h2>
        <div className="flex items-center gap-2">
          <select
            name="library-process-mode"
            value={mode}
            onChange={(e) => setMode(e.target.value as ProcessMode)}
            className="rounded border border-slate-700 bg-slate-900 px-2 py-1 text-xs text-slate-200"
          >
            <option value="analysis_only">Analyze chords only</option>
            <option value="analysis_and_stems">Analyze + split stems</option>
          </select>
          <label className="cursor-pointer rounded-md bg-blue-600 px-2.5 py-1 text-xs font-semibold text-white hover:bg-blue-500">
            {loading ? "Processing..." : "Upload"}
            <input
              type="file"
              accept=".mp3,.wav,.m4a,.aac,.mp4"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) onUpload(file, mode);
              }}
              disabled={loading}
            />
          </label>
        </div>
      </div>

      <div className="max-h-48 space-y-1 overflow-y-auto pr-1">
        {songs.length === 0 ? (
          <p className="text-xs text-slate-400">No songs yet. Upload one to get started.</p>
        ) : (
          songs.map((song) => {
            const active = song.id === selectedSongId;
            return (
              <button
                key={song.id}
                onClick={() => onSelect(song.id)}
                className={`w-full rounded-md border px-3 py-2 text-left transition-colors ${
                  active
                    ? "border-blue-500 bg-blue-500/20 text-blue-100"
                    : "border-slate-800 bg-slate-900 text-slate-300 hover:border-slate-700 hover:bg-slate-800"
                }`}
              >
                <div className="truncate text-sm font-medium">{song.title}</div>
                <div className="text-xs text-slate-400">
                  {song.key ?? "--"}
                  {song.tempo ? ` | ${song.tempo} BPM` : ""}
                </div>
              </button>
            );
          })
        )}
      </div>
    </section>
  );
}
