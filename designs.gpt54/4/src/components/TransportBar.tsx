interface TransportBarProps {
  currentTime: number;
  duration: number;
  playing: boolean;
  volume: number;
  speedPercent: number;
  timeNoteMarkers: Array<{ id: string; timestampSec: number }>;
  loopActive: boolean;
  loopLabel?: string;
  onTogglePlay: () => void;
  onSeek: (time: number) => void;
  onSeekDragStart: () => void;
  onSeekDragEnd: () => void;
  onSeekRelative: (delta: number) => void;
  onNoteLaneClick: (time: number) => void;
  onNoteMarkerClick: (noteId: string) => void;
  onVolumeChange: (volume: number) => void;
  onSpeedChange: (speedPercent: number) => void;
  onClearLoop: () => void;
}

const SPEED_OPTIONS = Array.from({ length: 17 }, (_, index) => 40 + index * 10);

function formatTime(seconds: number): string {
  const minutes = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${minutes}:${secs.toString().padStart(2, "0")}`;
}

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
    if (rect.width <= 0) {
      return 0;
    }
    const ratio = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width));
    return (duration || 0) * ratio;
  };

  return (
    <div className="sticky bottom-0 z-40 border-t border-[var(--line-strong)] bg-[var(--transport-bg)]/95 px-4 py-3 backdrop-blur">
      <div className="mb-2 flex items-center gap-2">
        <button className="px-2 text-[var(--muted)] hover:text-[var(--text)]" onClick={() => onSeekRelative(-10)} title="Back 10s">
          &#x23EA;
        </button>
        <button
          className="flex h-10 w-10 items-center justify-center rounded-full bg-[var(--accent)] text-white shadow-[var(--shadow-soft)] hover:opacity-90"
          onClick={onTogglePlay}
        >
          {playing ? "\u23F8" : "\u25B6"}
        </button>
        <button className="px-2 text-[var(--muted)] hover:text-[var(--text)]" onClick={() => onSeekRelative(10)} title="Forward 10s">
          &#x23E9;
        </button>

        <span className="w-12 text-right font-mono text-xs text-[var(--text-soft)]">{formatTime(currentTime)}</span>

        <div className="relative flex-1">
          <div
            className="mb-1 h-4 w-full cursor-pointer rounded-full bg-[var(--lane-bg)]"
            onClick={(event) => onNoteLaneClick(clampTimeFromClientX(event.currentTarget, event.clientX))}
            onKeyDown={(event) => {
              if (event.key === "Enter" || event.key === " ") {
                onNoteLaneClick(duration * 0.5);
              }
            }}
            role="button"
            tabIndex={0}
            title="Click to add or inspect a timed note"
          >
            <div className="relative h-full w-full">
              {timeNoteMarkers.map((marker) => {
                const left = duration > 0 ? (marker.timestampSec / duration) * 100 : 0;
                return (
                  <button
                    key={marker.id}
                    className="absolute top-1/2 h-3 w-3 -translate-x-1/2 -translate-y-1/2 rounded-full border border-[var(--marker-border)] bg-[var(--marker-bg)] shadow"
                    onClick={(event) => {
                      event.stopPropagation();
                      onNoteMarkerClick(marker.id);
                    }}
                    style={{ left: `${left}%` }}
                    title="Inspect note"
                    type="button"
                  />
                );
              })}
            </div>
          </div>

          <input
            className="h-1 w-full accent-[var(--accent)]"
            max={duration || 1}
            min={0}
            onBlur={onSeekDragEnd}
            onChange={(event) => onSeek(parseFloat(event.target.value))}
            onMouseDown={onSeekDragStart}
            onMouseUp={onSeekDragEnd}
            onPointerCancel={onSeekDragEnd}
            onPointerDown={onSeekDragStart}
            onPointerUp={onSeekDragEnd}
            onTouchEnd={onSeekDragEnd}
            onTouchStart={onSeekDragStart}
            step={0.05}
            type="range"
            value={currentTime}
          />
        </div>

        <span className="w-12 font-mono text-xs text-[var(--text-soft)]">{formatTime(duration)}</span>

        <select
          className="rounded-full border border-[var(--line)] bg-[var(--page-strong)] px-2 py-1 text-xs text-[var(--text)]"
          onChange={(event) => onSpeedChange(parseInt(event.target.value, 10))}
          value={speedPercent}
        >
          {SPEED_OPTIONS.map((speed) => (
            <option key={speed} value={speed}>
              {speed}%
            </option>
          ))}
        </select>

        {loopActive ? (
          <button
            className="rounded-full bg-[var(--loop-bg)] px-3 py-1 text-xs text-[var(--loop-text)]"
            onClick={onClearLoop}
            title="Clear loop"
          >
            🔁 {loopLabel}
          </button>
        ) : null}

        <input
          className="h-1 w-20 accent-[var(--accent)]"
          max={1}
          min={0}
          onChange={(event) => onVolumeChange(parseFloat(event.target.value))}
          step={0.05}
          type="range"
          value={volume}
        />
      </div>
      <p className="text-[11px] text-[var(--muted)]">
        Player notes stay visible in the lane above progress. Chord notes and timeline comments remain attached to rehearsal time.
      </p>
    </div>
  );
}
