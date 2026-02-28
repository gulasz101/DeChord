import { useRef, useEffect, useCallback } from "react";
import type { Chord } from "../lib/types";

interface ChordTimelineProps {
  chords: Chord[];
  currentIndex: number;
  currentTime: number;
  duration: number;
  loopStart: number | null;
  loopEnd: number | null;
  noteChordIndexes?: Set<number>;
  onChordClick: (index: number) => void;
  onChordNoteRequest?: (index: number) => void;
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
  noteChordIndexes,
  onChordClick,
  onChordNoteRequest,
}: ChordTimelineProps) {
  const activeRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (activeRef.current) {
      activeRef.current.scrollIntoView({ behavior: "smooth", block: "center" });
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
    <div className="flex flex-wrap gap-1 p-4 overflow-y-auto">
      {chords.map((chord, i) => {
        const isCurrent = i === currentIndex;
        const isNext = i === currentIndex + 1;
        const inLoop = isInLoop(i);
        const hasNote = noteChordIndexes?.has(i);
        const progress =
          isCurrent && chord.end > chord.start
            ? ((currentTime - chord.start) / (chord.end - chord.start)) * 100
            : 0;

        return (
          <div
            key={i}
            ref={isCurrent ? activeRef : undefined}
            onClick={() => onChordClick(i)}
            onDoubleClick={() => onChordNoteRequest?.(i)}
            style={{ width: getBlockWidth(chord) }}
            className={`relative h-10 cursor-pointer select-none overflow-hidden rounded text-sm font-mono transition-colors ${
              isCurrent
                ? "bg-blue-600 text-white"
                : isNext
                  ? "bg-amber-700/80 text-amber-100"
                : inLoop
                  ? "bg-indigo-800 text-indigo-200"
                  : "bg-slate-800 text-slate-200 hover:bg-slate-700"
            }`}
          >
            {isCurrent && (
              <div className="absolute inset-y-0 left-0 bg-blue-300/30" style={{ width: `${progress}%` }} />
            )}

            <div className="relative z-10 flex h-full items-center justify-center">
              {chord.label}
            </div>
            {hasNote && (
              <span className="absolute right-1 top-1 z-10 h-2.5 w-2.5 rounded-full border border-yellow-200 bg-yellow-400 shadow" />
            )}

            {loopStart === i && <div className="absolute bottom-0 left-0 top-0 w-1 bg-green-400" />}
            {loopEnd === i && <div className="absolute bottom-0 right-0 top-0 w-1 bg-red-400" />}
          </div>
        );
      })}
    </div>
  );
}
