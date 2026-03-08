import { useCallback, useEffect, useRef } from "react";

export interface ChordBlock {
  start: number;
  end: number;
  label: string;
}

interface ChordTimelineProps {
  chords: ChordBlock[];
  currentIndex: number;
  currentTime: number;
  loopStart: number | null;
  loopEnd: number | null;
  noteChordIndexes?: Set<number>;
  onChordClick: (index: number) => void;
  onChordNoteRequest?: (index: number) => void;
  onChordNoteEdit?: (index: number) => void;
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
  onChordNoteEdit,
}: ChordTimelineProps) {
  const activeRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    activeRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "center" });
  }, [currentIndex]);

  const getBlockWidth = useCallback((chord: ChordBlock) => {
    const width = (chord.end - chord.start) * PIXELS_PER_SECOND;
    return Math.max(width, MIN_BLOCK_WIDTH);
  }, []);

  const isInLoop = useCallback(
    (index: number) => loopStart !== null && loopEnd !== null && index >= loopStart && index <= loopEnd,
    [loopEnd, loopStart],
  );

  return (
    <div className="overflow-x-auto rounded-[var(--radius-lg)] border border-[var(--line)] bg-[var(--panel)] p-4 shadow-[var(--shadow-soft)]">
      <div className="flex gap-1">
        {chords.map((chord, index) => {
          const isCurrent = index === currentIndex;
          const isNext = index === currentIndex + 1;
          const inLoop = isInLoop(index);
          const hasNote = noteChordIndexes?.has(index);
          const progress =
            isCurrent && chord.end > chord.start
              ? ((currentTime - chord.start) / (chord.end - chord.start)) * 100
              : 0;

          return (
            <div
              key={`${chord.label}-${index}`}
              className={`relative h-11 cursor-pointer select-none overflow-hidden rounded-[var(--radius-md)] text-sm font-mono transition-colors ${
                isCurrent
                  ? "bg-[var(--current-chord)] text-white"
                  : isNext
                    ? "bg-[var(--next-chord)] text-[var(--next-chord-text)]"
                    : inLoop
                      ? "bg-[var(--loop-chord)] text-[var(--loop-chord-text)]"
                      : "bg-[var(--chord-bg)] text-[var(--text)] hover:bg-[var(--chord-hover)]"
              }`}
              onClick={() => onChordClick(index)}
              onDoubleClick={() => onChordNoteRequest?.(index)}
              ref={isCurrent ? activeRef : undefined}
              style={{ width: getBlockWidth(chord) }}
            >
              {isCurrent ? (
                <div className="absolute inset-y-0 left-0 bg-[var(--current-progress)]" style={{ width: `${progress}%` }} />
              ) : null}
              <div className="relative z-10 flex h-full items-center justify-center px-3">{chord.label}</div>
              {hasNote ? (
                <button
                  className="absolute right-1 top-1 z-20 h-2.5 w-2.5 rounded-full border border-[var(--marker-border)] bg-[var(--marker-bg)] shadow"
                  onClick={(event) => {
                    event.stopPropagation();
                    onChordNoteEdit?.(index);
                  }}
                  title="Inspect chord note"
                  type="button"
                />
              ) : null}
              {loopStart === index ? <div className="absolute bottom-0 left-0 top-0 w-1 bg-[var(--loop-start)]" /> : null}
              {loopEnd === index ? <div className="absolute bottom-0 right-0 top-0 w-1 bg-[var(--loop-end)]" /> : null}
            </div>
          );
        })}
      </div>
    </div>
  );
}
