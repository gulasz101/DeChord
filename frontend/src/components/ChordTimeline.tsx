import { useRef, useEffect, useCallback } from "react";
import type { Chord } from "../lib/types";

interface ChordTimelineProps {
  chords: Chord[];
  currentIndex: number;
  currentTime: number;
  duration: number;
  loopStart: number | null;
  loopEnd: number | null;
  onChordClick: (index: number) => void;
  onSeek: (time: number) => void;
}

const PIXELS_PER_SECOND = 40;
const MIN_BLOCK_WIDTH = 48;

export function ChordTimeline({
  chords,
  currentIndex,
  currentTime,
  loopStart,
  loopEnd,
  onChordClick,
}: ChordTimelineProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const activeRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to keep current chord visible
  useEffect(() => {
    if (activeRef.current) {
      activeRef.current.scrollIntoView({
        behavior: "smooth",
        block: "center",
      });
    }
  }, [currentIndex]);

  const getBlockWidth = useCallback((chord: Chord) => {
    const w = (chord.end - chord.start) * PIXELS_PER_SECOND;
    return Math.max(w, MIN_BLOCK_WIDTH);
  }, []);

  const isInLoop = useCallback(
    (index: number) => {
      if (loopStart === null || loopEnd === null) return false;
      return index >= loopStart && index <= loopEnd;
    },
    [loopStart, loopEnd],
  );

  return (
    <div ref={containerRef} className="flex flex-wrap gap-1 p-4 overflow-y-auto">
      {chords.map((chord, i) => {
        const isCurrent = i === currentIndex;
        const inLoop = isInLoop(i);
        const progress =
          isCurrent && chord.end > chord.start
            ? ((currentTime - chord.start) / (chord.end - chord.start)) * 100
            : 0;

        return (
          <div
            key={i}
            ref={isCurrent ? activeRef : undefined}
            onClick={() => onChordClick(i)}
            style={{ width: getBlockWidth(chord) }}
            className={`relative h-10 flex items-center justify-center rounded text-sm font-mono cursor-pointer select-none overflow-hidden transition-colors ${
              isCurrent
                ? "bg-blue-600 text-white"
                : inLoop
                  ? "bg-indigo-800 text-indigo-200"
                  : "bg-gray-800 text-gray-300 hover:bg-gray-700"
            }`}
          >
            {/* Progress fill for current chord */}
            {isCurrent && (
              <div
                className="absolute inset-y-0 left-0 bg-blue-400/30"
                style={{ width: `${progress}%` }}
              />
            )}
            <span className="relative z-10">{chord.label}</span>
            {/* Loop boundary markers */}
            {loopStart === i && (
              <div className="absolute left-0 top-0 bottom-0 w-1 bg-green-400" />
            )}
            {loopEnd === i && (
              <div className="absolute right-0 top-0 bottom-0 w-1 bg-red-400" />
            )}
          </div>
        );
      })}
    </div>
  );
}
