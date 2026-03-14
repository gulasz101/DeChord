import React from "react";
import type { NoteMarker } from "../../lib/types";

interface TransportBarProps {
  currentTime: number;
  duration: number;
  playing: boolean;
  volume: number;
  speedPercent: number;
  loopActive: boolean;
  loopLabel?: string;
  noteMarkers: NoteMarker[];
  currentUserId: number | null;
  onTogglePlay: () => void;
  onSeek: (time: number) => void;
  onSeekRelative: (delta: number) => void;
  onVolumeChange: (v: number) => void;
  onSpeedChange: (s: number) => void;
  onClearLoop: () => void;
  onCommentLaneClick: (timestampSec: number) => void;
  onMarkerClick: (noteId: number, timestampSec: number) => void;
}

function formatTime(s: number): string {
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  return `${m}:${sec.toString().padStart(2, "0")}`;
}

interface CommentDotProps {
  marker: NoteMarker;
  left: number;
  isOwn: boolean;
  onMarkerClick: (noteId: number, timestampSec: number) => void;
}

function CommentDot({ marker, left, isOwn, onMarkerClick }: CommentDotProps) {
  const [hovered, setHovered] = React.useState(false);

  return (
    <div
      data-testid={`comment-marker-${marker.id}`}
      data-own={String(isOwn)}
      className="absolute top-1/2 -translate-x-1/2 -translate-y-1/2 cursor-pointer"
      style={{ left: `${left}%` }}
      onClick={(e) => {
        e.stopPropagation();
        onMarkerClick(marker.id, marker.timestampSec);
      }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <div
        className="h-2.5 w-2.5 rounded-full transition-transform hover:scale-125"
        style={
          isOwn
            ? { background: "#a78bfa", border: "1.5px solid #e2e2f0" }
            : { background: "transparent", border: "1.5px solid #a78bfa" }
        }
      />
      {hovered && (marker.authorName || marker.text) && (
        <div
          className="pointer-events-none absolute bottom-4 left-1/2 z-50 -translate-x-1/2 rounded-md px-3 py-2 shadow-xl"
          style={{
            background: "rgba(17, 22, 56, 0.97)",
            border: "1px solid rgba(167, 139, 250, 0.4)",
            boxShadow: "0 4px 16px rgba(124, 58, 237, 0.3)",
            whiteSpace: "nowrap",
            minWidth: "120px",
          }}
        >
          {marker.authorName && (
            <div className="mb-0.5 text-[10px] font-semibold" style={{ color: "#a78bfa" }}>
              {marker.authorName}
            </div>
          )}
          {marker.text && (
            <div className="text-[10px]" style={{ color: "#e2e2f0" }}>
              {marker.text}
            </div>
          )}
          <div className="mt-1 text-[9px]" style={{ color: "#7a7a90" }}>
            @ {formatTime(marker.timestampSec)}
            {marker.toastDurationSec != null && ` · shows for ${marker.toastDurationSec}s`}
          </div>
        </div>
      )}
    </div>
  );
}

const SPEED_OPTIONS = Array.from({ length: 17 }, (_, i) => 40 + i * 10);

export function TransportBar({ currentTime, duration, playing, volume, speedPercent, loopActive, loopLabel, noteMarkers, currentUserId, onTogglePlay, onSeek, onSeekRelative, onVolumeChange, onSpeedChange, onClearLoop, onCommentLaneClick, onMarkerClick }: TransportBarProps) {
  return (
    <div className="border px-4 py-3" style={{ borderRadius: "4px", borderColor: "rgba(192, 192, 192, 0.06)", background: "rgba(17, 22, 56, 0.7)", backdropFilter: "blur(16px)" }}>
      <div className="flex items-center gap-3">
        {/* Skip back */}
        <button onClick={() => onSeekRelative(-10)} className="px-1.5 text-lg transition-colors hover:text-purple-300" style={{ color: "#c0c0c0" }}>⏪</button>

        {/* Play/Pause */}
        <button onClick={onTogglePlay} className="flex h-10 w-10 items-center justify-center text-white transition-all hover:brightness-110 hover:shadow-lg hover:shadow-purple-500/20" style={{ borderRadius: "4px", background: "linear-gradient(135deg, #7c3aed, #5b21b6)" }}>
          {playing ? "⏸" : "▶"}
        </button>

        {/* Skip forward */}
        <button onClick={() => onSeekRelative(10)} className="px-1.5 text-lg transition-colors hover:text-purple-300" style={{ color: "#c0c0c0" }}>⏩</button>

        {/* Time */}
        <span className="w-11 text-right font-mono text-xs" style={{ color: "#e2e2f0" }}>{formatTime(currentTime)}</span>

        {/* Progress + note lane */}
        <div className="relative flex-1">
          {/* Comment lane */}
          <div
            data-testid="comment-lane"
            className="relative mb-1 w-full cursor-crosshair overflow-visible rounded"
            style={{ height: "12px", background: "rgba(30, 30, 58, 0.7)", border: "1px solid rgba(124, 58, 237, 0.15)" }}
            onClick={(e) => {
              const rect = e.currentTarget.getBoundingClientRect();
              const ts = ((e.clientX - rect.left) / rect.width) * (duration || 1);
              onCommentLaneClick(Math.max(0, Math.min(ts, duration)));
            }}
          >
            {noteMarkers.map((m) => {
              const left = duration > 0 ? (m.timestampSec / duration) * 100 : 0;
              const isOwn = m.userId !== null && m.userId === currentUserId;
              return (
                <CommentDot
                  key={m.id}
                  marker={m}
                  left={left}
                  isOwn={isOwn}
                  onMarkerClick={onMarkerClick}
                />
              );
            })}
            <span
              className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 text-[8px] tracking-wide"
              style={{ color: "rgba(167, 139, 250, 0.3)" }}
            >
              click to add
            </span>
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
