interface TransportBarProps {
  currentTime: number;
  duration: number;
  playing: boolean;
  volume: number;
  speedPercent: number;
  noteMarkers: number[];
  loopActive: boolean;
  loopLabel?: string;
  onTogglePlay: () => void;
  onSeek: (time: number) => void;
  onSeekRelative: (delta: number) => void;
  onProgressClick: (time: number) => void;
  onVolumeChange: (v: number) => void;
  onSpeedChange: (speedPercent: number) => void;
  onClearLoop: () => void;
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

const SPEED_OPTIONS = Array.from({ length: 17 }, (_, i) => 40 + i * 10);

export function TransportBar({
  currentTime,
  duration,
  playing,
  volume,
  speedPercent,
  noteMarkers,
  loopActive,
  loopLabel,
  onTogglePlay,
  onSeek,
  onSeekRelative,
  onProgressClick,
  onVolumeChange,
  onSpeedChange,
  onClearLoop,
}: TransportBarProps) {
  return (
    <div className="border-t border-slate-800 bg-slate-900 px-4 py-2">
      <div className="mb-2 flex items-center gap-2">
        <button onClick={() => onSeekRelative(-10)} className="px-2 text-slate-400 hover:text-white" title="Back 10s">
          &#x23EA;
        </button>
        <button
          onClick={onTogglePlay}
          className="flex h-9 w-9 items-center justify-center rounded-full bg-blue-600 text-white hover:bg-blue-500"
        >
          {playing ? "\u23F8" : "\u25B6"}
        </button>
        <button onClick={() => onSeekRelative(10)} className="px-2 text-slate-400 hover:text-white" title="Forward 10s">
          &#x23E9;
        </button>

        <span className="w-12 text-right font-mono text-xs text-slate-300">{formatTime(currentTime)}</span>

        <div className="relative flex-1">
          <input
            type="range"
            min={0}
            max={duration || 1}
            step={0.05}
            value={currentTime}
            onChange={(e) => onSeek(parseFloat(e.target.value))}
            onClick={(e) => {
              const rect = (e.target as HTMLInputElement).getBoundingClientRect();
              if (rect.width <= 0) return;
              const ratio = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
              onProgressClick((duration || 0) * ratio);
            }}
            className="h-1 w-full accent-blue-500"
          />
          {noteMarkers.map((sec, idx) => {
            const left = duration > 0 ? (sec / duration) * 100 : 0;
            return (
              <span
                key={`${sec}-${idx}`}
                className="pointer-events-none absolute -top-1 h-2 w-1 rounded bg-amber-300"
                style={{ left: `${left}%` }}
              />
            );
          })}
        </div>

        <span className="w-12 font-mono text-xs text-slate-300">{formatTime(duration)}</span>

        <select
          value={speedPercent}
          onChange={(e) => onSpeedChange(parseInt(e.target.value, 10))}
          className="rounded border border-slate-700 bg-slate-950 px-2 py-1 text-xs text-slate-200"
        >
          {SPEED_OPTIONS.map((v) => (
            <option key={v} value={v}>
              {v}%
            </option>
          ))}
        </select>

        {loopActive ? (
          <button
            onClick={onClearLoop}
            className="rounded bg-indigo-800 px-2 py-1 text-xs text-indigo-100 hover:bg-indigo-700"
            title="Click to clear loop"
          >
            🔁 {loopLabel}
          </button>
        ) : null}

        <input
          type="range"
          min={0}
          max={1}
          step={0.05}
          value={volume}
          onChange={(e) => onVolumeChange(parseFloat(e.target.value))}
          className="h-1 w-20 accent-blue-500"
        />
      </div>
      <p className="text-[11px] text-slate-500">Tip: double-click a chord to add a chord note. Click progress to add a timed note.</p>
    </div>
  );
}
