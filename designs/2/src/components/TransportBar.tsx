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
    <div className="border px-4 py-3" style={{ borderColor: "rgba(0, 255, 65, 0.12)", background: "rgba(10, 10, 10, 0.9)" }}>
      <div className="flex items-center gap-3">
        {/* Skip back */}
        <button onClick={() => onSeekRelative(-10)} className="px-1.5 font-mono text-sm transition-colors hover:text-green-300" style={{ color: "#00ff41" }}>&lt;&lt;</button>

        {/* Play/Pause */}
        <button onClick={onTogglePlay} className="flex h-10 w-10 items-center justify-center border-2 font-mono text-sm font-bold transition-all hover:bg-green-900/20" style={{ borderColor: "#00ff41", color: "#00ff41", boxShadow: "0 0 12px rgba(0, 255, 65, 0.2)" }}>
          {playing ? "||" : "|>"}
        </button>

        {/* Skip forward */}
        <button onClick={() => onSeekRelative(10)} className="px-1.5 font-mono text-sm transition-colors hover:text-green-300" style={{ color: "#00ff41" }}>&gt;&gt;</button>

        {/* Time */}
        <span className="w-11 text-right font-mono text-xs" style={{ color: "#00ff41" }}>{formatTime(currentTime)}</span>

        {/* Progress + note lane */}
        <div className="relative flex-1">
          {/* Note markers */}
          <div className="mb-1 h-3 w-full" style={{ background: "rgba(26, 26, 26, 0.8)" }}>
            <div className="relative h-full w-full">
              {noteMarkers.map((m) => {
                const left = duration > 0 ? (m.timestampSec / duration) * 100 : 0;
                return (
                  <div key={m.id} className="absolute top-1/2 h-2.5 w-2.5 -translate-x-1/2 -translate-y-1/2" style={{ left: `${left}%`, background: "#00e5ff", border: "1px solid #0a0a0a" }} />
                );
              })}
            </div>
          </div>

          {/* Seek slider */}
          <input type="range" min={0} max={duration || 1} step={0.05} value={currentTime}
            onChange={(e) => onSeek(parseFloat(e.target.value))}
            className="h-1 w-full" />
        </div>

        {/* Duration */}
        <span className="w-11 font-mono text-xs" style={{ color: "#3a3a3a" }}>{formatTime(duration)}</span>

        {/* Speed */}
        <select value={speedPercent} onChange={(e) => onSpeedChange(parseInt(e.target.value, 10))}
          className="border px-2 py-1 font-mono text-xs" style={{ background: "#111111", borderColor: "rgba(0, 255, 65, 0.2)", color: "#00ff41" }}>
          {SPEED_OPTIONS.map((v) => <option key={v} value={v}>{v}%</option>)}
        </select>

        {/* Loop */}
        {loopActive && (
          <button onClick={onClearLoop} className="border px-2.5 py-1 font-mono text-xs font-medium transition-colors hover:brightness-110" style={{ borderColor: "rgba(255, 0, 255, 0.3)", background: "rgba(255, 0, 255, 0.08)", color: "#ff00ff" }}>
            [loop] {loopLabel}
          </button>
        )}

        {/* Volume */}
        <input type="range" min={0} max={1} step={0.05} value={volume}
          onChange={(e) => onVolumeChange(parseFloat(e.target.value))}
          className="h-1 w-20" />
      </div>
    </div>
  );
}
