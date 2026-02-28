import type { SongSummary } from "../lib/types";

interface SongLibraryPanelProps {
  songs: SongSummary[];
  selectedSongId: number | null;
  onSelect: (songId: number) => void;
}

export function SongLibraryPanel({
  songs,
  selectedSongId,
  onSelect,
}: SongLibraryPanelProps) {
  return (
    <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-3">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-slate-100">Song Library</h2>
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
