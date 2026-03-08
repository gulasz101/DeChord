import { useRef, useEffect, useCallback } from "react";
import type { Chord } from "../lib/types";

interface ChordTimelineProps {
  chords: Chord[];
  currentIndex: number;
  currentTime: number;
  loopStart: number | null;
  loopEnd: number | null;
  noteChordIndexes?: Set<number>;
  onChordClick: (index: number) => void;
  onSeek: (time: number) => void;
}

const PIXELS_PER_SECOND = 40;
const MIN_BLOCK_WIDTH = 48;

export function ChordTimeline({ chords, currentIndex, currentTime, loopStart, loopEnd, noteChordIndexes, onChordClick }: ChordTimelineProps) {
  const activeRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    activeRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
  }, [currentIndex]);

  const getBlockWidth = useCallback((chord: Chord) => Math.max((chord.end - chord.start) * PIXELS_PER_SECOND, MIN_BLOCK_WIDTH), []);

  const isInLoop = useCallback((index: number) => {
    if (loopStart === null || loopEnd === null) return false;
    return index >= loopStart && index <= loopEnd;
  }, [loopStart, loopEnd]);

  return (
    <div className="flex flex-wrap gap-1 overflow-y-auto border p-3" style={{ borderColor: "rgba(0, 255, 65, 0.1)", background: "rgba(10, 10, 10, 0.8)" }}>
      {chords.map((chord, i) => {
        const isCurrent = i === currentIndex;
        const isNext = i === currentIndex + 1;
        const inLoop = isInLoop(i);
        const hasNote = noteChordIndexes?.has(i);
        const progress = isCurrent && chord.end > chord.start ? ((currentTime - chord.start) / (chord.end - chord.start)) * 100 : 0;

        let bg = "rgba(26, 26, 26, 0.8)";
        let textColor = "#3a3a3a";
        if (isCurrent) { bg = "#00ff41"; textColor = "#0a0a0a"; }
        else if (isNext) { bg = "rgba(0, 229, 255, 0.2)"; textColor = "#00e5ff"; }
        else if (inLoop) { bg = "rgba(255, 0, 255, 0.15)"; textColor = "#ff00ff"; }

        return (
          <div key={i} ref={isCurrent ? activeRef : undefined} onClick={() => onChordClick(i)}
            style={{ width: getBlockWidth(chord), background: bg, color: textColor }}
            className="relative h-10 cursor-pointer select-none overflow-hidden rounded-sm font-mono text-sm transition-colors hover:brightness-110">
            {isCurrent && (
              <div className="absolute inset-y-0 left-0" style={{ width: `${progress}%`, background: "rgba(0, 0, 0, 0.2)" }} />
            )}
            <div className="relative z-10 flex h-full items-center justify-center">{chord.label}</div>
            {hasNote && (
              <div className="absolute right-1 top-1 h-2 w-2" style={{ background: "#00e5ff" }} />
            )}
            {loopStart === i && <div className="absolute bottom-0 left-0 top-0 w-1" style={{ background: "#ff00ff" }} />}
            {loopEnd === i && <div className="absolute bottom-0 right-0 top-0 w-1" style={{ background: "#ff4444" }} />}
          </div>
        );
      })}
    </div>
  );
}
