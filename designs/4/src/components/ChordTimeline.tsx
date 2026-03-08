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
    <div className="flex flex-wrap gap-0.5 overflow-y-auto p-3" style={{ border: "3px solid #000", background: "#fff" }}>
      {chords.map((chord, i) => {
        const isCurrent = i === currentIndex;
        const isNext = i === currentIndex + 1;
        const inLoop = isInLoop(i);
        const hasNote = noteChordIndexes?.has(i);
        const progress = isCurrent && chord.end > chord.start ? ((currentTime - chord.start) / (chord.end - chord.start)) * 100 : 0;

        let bg = "#f5f5f5";
        let textColor = "#000";
        let borderColor = "#000";
        if (isCurrent) { bg = "#FFE500"; textColor = "#000"; borderColor = "#000"; }
        else if (isNext) { bg = "#ddd"; textColor = "#000"; }
        else if (inLoop) { bg = "#e0e0e0"; textColor = "#000"; borderColor = "#FFE500"; }

        return (
          <div key={i} ref={isCurrent ? activeRef : undefined} onClick={() => onChordClick(i)}
            style={{ width: getBlockWidth(chord), background: bg, color: textColor, border: `2px solid ${borderColor}` }}
            className="relative h-10 cursor-pointer select-none overflow-hidden font-mono text-sm font-bold transition-colors hover:bg-yellow-200">
            {isCurrent && (
              <div className="absolute inset-y-0 left-0" style={{ width: `${progress}%`, background: "rgba(0, 0, 0, 0.1)" }} />
            )}
            <div className="relative z-10 flex h-full items-center justify-center uppercase">{chord.label}</div>
            {hasNote && (
              <div className="absolute right-1 top-1 h-2.5 w-2.5" style={{ background: "#FF0000" }} />
            )}
            {loopStart === i && <div className="absolute bottom-0 left-0 top-0 w-1" style={{ background: "#000" }} />}
            {loopEnd === i && <div className="absolute bottom-0 right-0 top-0 w-1" style={{ background: "#FF0000" }} />}
          </div>
        );
      })}
    </div>
  );
}
