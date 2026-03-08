import { useRef, useEffect, useCallback, useState, useMemo } from "react";
import type { Chord, ChordSection } from "../lib/types";

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

const WINDOW_RADIUS = 3; // Show 3 chords before and after current

export function ChordTimeline({ chords, currentIndex, currentTime, loopStart, loopEnd, noteChordIndexes, onChordClick }: ChordTimelineProps) {
  const activeRef = useRef<HTMLDivElement>(null);
  const [showAll, setShowAll] = useState(false);

  useEffect(() => {
    activeRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "center" });
  }, [currentIndex]);

  const isInLoop = useCallback((index: number) => {
    if (loopStart === null || loopEnd === null) return false;
    return index >= loopStart && index <= loopEnd;
  }, [loopStart, loopEnd]);

  // Derive sections from chord data
  const sections = useMemo((): ChordSection[] => {
    if (chords.length === 0) return [];
    const result: ChordSection[] = [];
    let currentSection = chords[0]?.section ?? "Unknown";
    let startIdx = 0;
    for (let i = 1; i < chords.length; i++) {
      const sec = chords[i].section ?? "Unknown";
      if (sec !== currentSection) {
        result.push({ name: currentSection, startIndex: startIdx, endIndex: i - 1 });
        currentSection = sec;
        startIdx = i;
      }
    }
    result.push({ name: currentSection, startIndex: startIdx, endIndex: chords.length - 1 });
    return result;
  }, [chords]);

  // Current section
  const currentSectionName = chords[currentIndex]?.section ?? "";

  // Windowed chords (default view)
  const windowStart = Math.max(0, currentIndex - WINDOW_RADIUS);
  const windowEnd = Math.min(chords.length - 1, currentIndex + WINDOW_RADIUS);

  const renderChordBlock = (chord: Chord, i: number, big: boolean) => {
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
        style={{ background: bg, color: textColor, border: `2px solid ${borderColor}` }}
        className={`relative cursor-pointer select-none overflow-hidden font-mono font-bold uppercase transition-colors hover:bg-yellow-200 ${
          big ? "h-14 min-w-[80px] flex-1 text-base" : "h-10 min-w-[48px] flex-1 text-sm"
        }`}>
        {isCurrent && (
          <div className="absolute inset-y-0 left-0" style={{ width: `${progress}%`, background: "rgba(0, 0, 0, 0.1)" }} />
        )}
        <div className="relative z-10 flex h-full flex-col items-center justify-center">
          <span className="font-bold">{chord.label}</span>
          {big && <span className="text-[10px] font-bold" style={{ color: "#555" }}>{((chord.end - chord.start)).toFixed(1)}s</span>}
        </div>
        {hasNote && (
          <div className="absolute right-1 top-1 h-2.5 w-2.5" style={{ background: "#FF0000" }} />
        )}
        {loopStart === i && <div className="absolute bottom-0 left-0 top-0 w-1" style={{ background: "#000" }} />}
        {loopEnd === i && <div className="absolute bottom-0 right-0 top-0 w-1" style={{ background: "#FF0000" }} />}
      </div>
    );
  };

  if (!showAll) {
    // Windowed view: bigger blocks, current section label
    return (
      <div className="p-3" style={{ border: "3px solid #000", background: "#fff" }}>
        {/* Section header + toggle */}
        <div className="mb-2 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-xs font-bold uppercase tracking-widest" style={{ color: "#000", fontFamily: "Archivo Black, sans-serif" }}>{currentSectionName}</span>
            <span className="text-[10px] font-bold uppercase" style={{ color: "#888" }}>
              {currentIndex + 1} / {chords.length}
            </span>
          </div>
          <button onClick={() => setShowAll(true)}
            className="px-3 py-1 text-[11px] font-bold uppercase tracking-wider transition-colors hover:bg-yellow-200"
            style={{ border: "2px solid #000", color: "#000", background: "#f5f5f5" }}>
            All Sections
          </button>
        </div>

        {/* Windowed chord blocks */}
        <div className="flex gap-0.5">
          {windowStart > 0 && (
            <button onClick={() => onChordClick(windowStart - 1)}
              className="flex h-14 w-8 shrink-0 items-center justify-center text-xs font-bold"
              style={{ background: "#f5f5f5", color: "#000", border: "2px solid #000" }}>
              &lsaquo;
            </button>
          )}
          {chords.slice(windowStart, windowEnd + 1).map((chord, wi) => renderChordBlock(chord, windowStart + wi, true))}
          {windowEnd < chords.length - 1 && (
            <button onClick={() => onChordClick(windowEnd + 1)}
              className="flex h-14 w-8 shrink-0 items-center justify-center text-xs font-bold"
              style={{ background: "#f5f5f5", color: "#000", border: "2px solid #000" }}>
              &rsaquo;
            </button>
          )}
        </div>
      </div>
    );
  }

  // Full view: all chords grouped by section
  return (
    <div className="p-3" style={{ border: "3px solid #000", background: "#fff" }}>
      {/* Header + collapse */}
      <div className="mb-3 flex items-center justify-between">
        <span className="text-xs font-bold uppercase tracking-widest" style={{ color: "#000", fontFamily: "Archivo Black, sans-serif" }}>All Sections</span>
        <button onClick={() => setShowAll(false)}
          className="px-3 py-1 text-[11px] font-bold uppercase tracking-wider transition-colors hover:bg-yellow-200"
          style={{ border: "2px solid #000", color: "#000", background: "#f5f5f5" }}>
          Collapse
        </button>
      </div>

      {/* Sections */}
      <div className="max-h-64 space-y-3 overflow-y-auto">
        {sections.map((section) => {
          const isCurSection = currentIndex >= section.startIndex && currentIndex <= section.endIndex;
          return (
            <div key={`${section.name}-${section.startIndex}`}>
              <div className="mb-1 flex items-center gap-2">
                <span className="text-[11px] font-bold uppercase tracking-widest" style={{ color: isCurSection ? "#000" : "#888", fontFamily: "Archivo Black, sans-serif" }}>
                  {section.name}
                </span>
                <div className="h-0.5 flex-1" style={{ background: "#000" }} />
                <span className="text-[10px] font-bold uppercase" style={{ color: "#888" }}>
                  {section.endIndex - section.startIndex + 1} chords
                </span>
              </div>
              <div className="flex flex-wrap gap-0.5">
                {chords.slice(section.startIndex, section.endIndex + 1).map((chord, si) =>
                  renderChordBlock(chord, section.startIndex + si, false)
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
