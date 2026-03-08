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
    <div className="flex flex-wrap gap-1 overflow-y-auto rounded-xl border p-3" style={{ borderColor: "rgba(196, 168, 130, 0.1)", background: "rgba(26, 18, 9, 0.5)" }}>
      {chords.map((chord, i) => {
        const isCurrent = i === currentIndex;
        const isNext = i === currentIndex + 1;
        const inLoop = isInLoop(i);
        const hasNote = noteChordIndexes?.has(i);
        const progress = isCurrent && chord.end > chord.start ? ((currentTime - chord.start) / (chord.end - chord.start)) * 100 : 0;

        let bg = "rgba(61, 43, 31, 0.5)";
        let textColor = "#c4a882";
        if (isCurrent) { bg = "#b45309"; textColor = "#ffffff"; }
        else if (isNext) { bg = "rgba(196, 168, 130, 0.25)"; textColor = "#faf5eb"; }
        else if (inLoop) { bg = "rgba(107, 114, 52, 0.3)"; textColor = "#a3b236"; }

        return (
          <div key={i} ref={isCurrent ? activeRef : undefined} onClick={() => onChordClick(i)}
            style={{ width: getBlockWidth(chord), background: bg, color: textColor }}
            className="relative h-10 cursor-pointer select-none overflow-hidden rounded-lg font-mono text-sm transition-colors hover:brightness-110">
            {isCurrent && (
              <div className="absolute inset-y-0 left-0" style={{ width: `${progress}%`, background: "rgba(255, 255, 255, 0.15)" }} />
            )}
            <div className="relative z-10 flex h-full items-center justify-center">{chord.label}</div>
            {hasNote && (
              <div className="absolute right-1 top-1 h-2 w-2 rounded-full" style={{ background: "#d97706" }} />
            )}
            {loopStart === i && <div className="absolute bottom-0 left-0 top-0 w-1" style={{ background: "#6b7234" }} />}
            {loopEnd === i && <div className="absolute bottom-0 right-0 top-0 w-1" style={{ background: "#dc2626" }} />}
          </div>
        );
      })}
    </div>
  );
}
