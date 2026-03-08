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
    <div className="rounded-xl border px-4 py-3" style={{ borderColor: "rgba(192, 192, 192, 0.06)", background: "rgba(17, 22, 56, 0.7)", backdropFilter: "blur(16px)" }}>
      <div className="flex items-center gap-3">
        {/* Skip back */}
        <button onClick={() => onSeekRelative(-10)} className="px-1.5 text-lg transition-colors hover:text-purple-300" style={{ color: "#c0c0c0" }}>⏪</button>

        {/* Play/Pause */}
        <button onClick={onTogglePlay} className="flex h-10 w-10 items-center justify-center rounded-full text-white transition-all hover:brightness-110 hover:shadow-lg hover:shadow-purple-500/20" style={{ background: "linear-gradient(135deg, #7c3aed, #5b21b6)" }}>
          {playing ? "⏸" : "▶"}
        </button>

        {/* Skip forward */}
        <button onClick={() => onSeekRelative(10)} className="px-1.5 text-lg transition-colors hover:text-purple-300" style={{ color: "#c0c0c0" }}>⏩</button>

        {/* Time */}
        <span className="w-11 text-right font-mono text-xs" style={{ color: "#e2e2f0" }}>{formatTime(currentTime)}</span>

        {/* Progress + note lane */}
        <div className="relative flex-1">
          {/* Note markers */}
          <div className="mb-1 h-3 w-full rounded" style={{ background: "rgba(30, 30, 58, 0.6)" }}>
            <div className="relative h-full w-full">
              {noteMarkers.map((m) => {
                const left = duration > 0 ? (m.timestampSec / duration) * 100 : 0;
                return (
                  <div key={m.id} className="absolute top-1/2 h-2.5 w-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full" style={{ left: `${left}%`, background: "#a78bfa", border: "1px solid #e2e2f0" }} />
                );
              })}
            </div>
          </div>

          {/* Seek slider */}
          <input type="range" min={0} max={duration || 1} step={0.05} value={currentTime}
            onChange={(e) => onSeek(parseFloat(e.target.value))}
            className="h-1 w-full accent-purple-500" />
        </div>

        {/* Duration */}
        <span className="w-11 font-mono text-xs" style={{ color: "#8a8a9a" }}>{formatTime(duration)}</span>

        {/* Speed */}
        <select value={speedPercent} onChange={(e) => onSpeedChange(parseInt(e.target.value, 10))}
          className="rounded-lg border px-2 py-1 text-xs" style={{ background: "rgba(10, 14, 39, 0.6)", borderColor: "rgba(192, 192, 192, 0.12)", color: "#e2e2f0" }}>
          {SPEED_OPTIONS.map((v) => <option key={v} value={v}>{v}%</option>)}
        </select>

        {/* Loop */}
        {loopActive && (
          <button onClick={onClearLoop} className="rounded-lg px-2.5 py-1 text-xs font-medium transition-colors hover:brightness-110" style={{ background: "rgba(124, 58, 237, 0.2)", color: "#a78bfa" }}>
            🔁 {loopLabel}
          </button>
        )}

        {/* Volume */}
        <input type="range" min={0} max={1} step={0.05} value={volume}
          onChange={(e) => onVolumeChange(parseFloat(e.target.value))}
          className="h-1 w-20 accent-teal-500" />
      </div>
    </div>
  );
}
