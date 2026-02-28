interface TransportBarProps {
  currentTime: number;
  duration: number;
  playing: boolean;
  volume: number;
  speedPercent: number;
  timeNoteMarkers: Array<{ id: number; timestampSec: number }>;
  loopActive: boolean;
  loopLabel?: string;
  onTogglePlay: () => void;
  onSeek: (time: number) => void;
  onSeekDragStart: () => void;
  onSeekDragEnd: () => void;
  onSeekRelative: (delta: number) => void;
  onNoteLaneClick: (time: number) => void;
  onNoteMarkerClick: (noteId: number) => void;
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
  timeNoteMarkers,
  loopActive,
  loopLabel,
  onTogglePlay,
  onSeek,
  onSeekDragStart,
  onSeekDragEnd,
  onSeekRelative,
  onNoteLaneClick,
  onNoteMarkerClick,
  onVolumeChange,
  onSpeedChange,
  onClearLoop,
}: TransportBarProps) {
  const clampTimeFromClientX = (target: HTMLDivElement, clientX: number) => {
    const rect = target.getBoundingClientRect();
    if (rect.width <= 0) return 0;
    const ratio = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width));
    return (duration || 0) * ratio;
  };

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
          <div
            role="button"
            tabIndex={0}
            title="Click to add/edit timed note"
            className="mb-1 h-4 w-full cursor-pointer rounded bg-slate-800/70"
            onClick={(e) => {
              const t = clampTimeFromClientX(e.currentTarget, e.clientX);
              onNoteLaneClick(t);
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                const t = duration * 0.5;
                onNoteLaneClick(t);
              }
            }}
          >
            <div className="relative h-full w-full">
              {timeNoteMarkers.map((m) => {
                const left = duration > 0 ? (m.timestampSec / duration) * 100 : 0;
                return (
                  <button
                    key={m.id}
                    type="button"
                    className="absolute top-1/2 h-3 w-3 -translate-y-1/2 -translate-x-1/2 rounded-full border border-yellow-100 bg-yellow-400 shadow"
                    style={{ left: `${left}%` }}
                    title="Edit note"
                    onClick={(e) => {
                      e.stopPropagation();
                      onNoteMarkerClick(m.id);
                    }}
                  />
                );
              })}
            </div>
          </div>

          <input
            type="range"
            min={0}
            max={duration || 1}
            step={0.05}
            value={currentTime}
            onChange={(e) => onSeek(parseFloat(e.target.value))}
            onMouseDown={onSeekDragStart}
            onMouseUp={onSeekDragEnd}
            onTouchStart={onSeekDragStart}
            onTouchEnd={onSeekDragEnd}
            onPointerDown={onSeekDragStart}
            onPointerUp={onSeekDragEnd}
            onPointerCancel={onSeekDragEnd}
            onBlur={onSeekDragEnd}
            className="h-1 w-full accent-blue-500"
          />
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
      <p className="text-[11px] text-slate-500">Tip: double-click a chord to add a chord note. Click the lane above progress to add/edit timed notes.</p>
    </div>
  );
}
