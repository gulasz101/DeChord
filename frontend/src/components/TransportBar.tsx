// frontend/src/components/TransportBar.tsx
interface TransportBarProps {
  currentTime: number;
  duration: number;
  playing: boolean;
  volume: number;
  loopActive: boolean;
  loopLabel?: string;
  onTogglePlay: () => void;
  onSeek: (time: number) => void;
  onSeekRelative: (delta: number) => void;
  onVolumeChange: (v: number) => void;
  onClearLoop: () => void;
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export function TransportBar({
  currentTime,
  duration,
  playing,
  volume,
  loopActive,
  loopLabel,
  onTogglePlay,
  onSeek,
  onSeekRelative,
  onVolumeChange,
  onClearLoop,
}: TransportBarProps) {
  return (
    <div className="flex items-center gap-3 px-4 py-2 bg-gray-900 border-t border-gray-800">
      {/* Playback controls */}
      <button
        onClick={() => onSeekRelative(-10)}
        className="text-gray-400 hover:text-white text-sm px-1"
        title="Back 10s"
      >
        &#x23EA;
      </button>
      <button
        onClick={onTogglePlay}
        className="w-8 h-8 flex items-center justify-center rounded-full bg-blue-600 hover:bg-blue-500 text-white"
      >
        {playing ? "\u23F8" : "\u25B6"}
      </button>
      <button
        onClick={() => onSeekRelative(10)}
        className="text-gray-400 hover:text-white text-sm px-1"
        title="Forward 10s"
      >
        &#x23E9;
      </button>

      {/* Time & progress */}
      <span className="text-xs text-gray-400 font-mono w-12 text-right">
        {formatTime(currentTime)}
      </span>
      <input
        type="range"
        min={0}
        max={duration || 1}
        step={0.1}
        value={currentTime}
        onChange={(e) => onSeek(parseFloat(e.target.value))}
        className="flex-1 h-1 accent-blue-500"
      />
      <span className="text-xs text-gray-400 font-mono w-12">
        {formatTime(duration)}
      </span>

      {/* Loop indicator */}
      {loopActive && (
        <button
          onClick={onClearLoop}
          className="text-xs px-2 py-1 rounded bg-indigo-800 text-indigo-200 hover:bg-indigo-700"
          title="Click to clear loop"
        >
          🔁 {loopLabel}
        </button>
      )}

      {/* Volume */}
      <input
        type="range"
        min={0}
        max={1}
        step={0.05}
        value={volume}
        onChange={(e) => onVolumeChange(parseFloat(e.target.value))}
        className="w-20 h-1 accent-blue-500"
      />
    </div>
  );
}
