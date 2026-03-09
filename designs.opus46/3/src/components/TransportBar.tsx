interface TransportBarProps {
  currentTime: number;
  duration: number;
  playing: boolean;
  volume: number;
  speedPercent: number;
  loopActive: boolean;
  loopLabel?: string;
  noteMarkers: Array<{ id: number; timestampSec: number }>;
  onTogglePlay: () => void;
  onSeek: (time: number) => void;
  onSeekRelative: (delta: number) => void;
  onVolumeChange: (v: number) => void;
  onSpeedChange: (s: number) => void;
  onClearLoop: () => void;
}

function formatTime(s: number): string {
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  return `${m}:${sec.toString().padStart(2, "0")}`;
}

const SPEED_OPTIONS = Array.from({ length: 17 }, (_, i) => 40 + i * 10);

export function TransportBar({ currentTime, duration, playing, volume, speedPercent, loopActive, loopLabel, noteMarkers, onTogglePlay, onSeek, onSeekRelative, onVolumeChange, onSpeedChange, onClearLoop }: TransportBarProps) {
  return (
    <div className="border px-4 py-3" style={{ borderColor: "#e0ddd6", background: "#ffffff", borderRadius: "2px" }}>
      <div className="flex items-center gap-3">
        {/* Skip back */}
        <button onClick={() => onSeekRelative(-10)} className="px-1.5 text-sm transition-colors hover:text-[#e63946]" style={{ color: "#6b6b6b" }}>&laquo;</button>

        {/* Play/Pause */}
        <button onClick={onTogglePlay} className="flex h-9 w-9 items-center justify-center text-white text-sm transition-all hover:brightness-110" style={{ background: "#1a1a1a", borderRadius: "2px" }}>
          {playing ? "||" : "\u25B6"}
        </button>

        {/* Skip forward */}
        <button onClick={() => onSeekRelative(10)} className="px-1.5 text-sm transition-colors hover:text-[#e63946]" style={{ color: "#6b6b6b" }}>&raquo;</button>

        {/* Time */}
        <span className="w-11 text-right font-mono text-xs" style={{ color: "#1a1a1a" }}>{formatTime(currentTime)}</span>

        {/* Progress + note lane */}
        <div className="relative flex-1">
          {/* Note markers */}
          <div className="mb-1 h-3 w-full" style={{ background: "#f0ede6", borderRadius: "1px" }}>
            <div className="relative h-full w-full">
              {noteMarkers.map((m) => {
                const left = duration > 0 ? (m.timestampSec / duration) * 100 : 0;
                return (
                  <div key={m.id} className="absolute top-1/2 h-2.5 w-2.5 -translate-x-1/2 -translate-y-1/2" style={{ left: `${left}%`, background: "#e63946", borderRadius: "1px" }} />
                );
              })}
            </div>
          </div>

          {/* Seek slider */}
          <input type="range" min={0} max={duration || 1} step={0.05} value={currentTime}
            onChange={(e) => onSeek(parseFloat(e.target.value))}
            className="h-1 w-full accent-[#e63946]" />
        </div>

        {/* Duration */}
        <span className="w-11 font-mono text-xs" style={{ color: "#6b6b6b" }}>{formatTime(duration)}</span>

        {/* Speed */}
        <select value={speedPercent} onChange={(e) => onSpeedChange(parseInt(e.target.value, 10))}
          className="border-b bg-transparent px-1 py-1 text-xs" style={{ borderColor: "#d4d0c8", color: "#1a1a1a" }}>
          {SPEED_OPTIONS.map((v) => <option key={v} value={v}>{v}%</option>)}
        </select>

        {/* Loop */}
        {loopActive && (
          <button onClick={onClearLoop} className="px-2.5 py-1 text-xs font-medium transition-colors hover:text-[#e63946]" style={{ color: "#2d6a30", border: "1px solid #e0ddd6", borderRadius: "2px" }}>
            Loop: {loopLabel}
          </button>
        )}

        {/* Volume */}
        <input type="range" min={0} max={1} step={0.05} value={volume}
          onChange={(e) => onVolumeChange(parseFloat(e.target.value))}
          className="h-1 w-20 accent-[#e63946]" />
      </div>
    </div>
  );
}
