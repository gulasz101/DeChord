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

    let bg = "rgba(26, 26, 26, 0.8)";
    let textColor = "#3a3a3a";
    if (isCurrent) { bg = "#00ff41"; textColor = "#0a0a0a"; }
    else if (isNext) { bg = "rgba(0, 229, 255, 0.2)"; textColor = "#00e5ff"; }
    else if (inLoop) { bg = "rgba(255, 0, 255, 0.15)"; textColor = "#ff00ff"; }

    return (
      <div key={i} ref={isCurrent ? activeRef : undefined} onClick={() => onChordClick(i)}
        style={{ background: bg, color: textColor }}
        className={`relative cursor-pointer select-none overflow-hidden rounded-sm font-mono transition-colors hover:brightness-110 ${
          big ? "h-14 min-w-[80px] flex-1 text-base" : "h-10 min-w-[48px] flex-1 text-sm"
        }`}>
        {isCurrent && (
          <div className="absolute inset-y-0 left-0" style={{ width: `${progress}%`, background: "rgba(0, 0, 0, 0.2)" }} />
        )}
        <div className="relative z-10 flex h-full flex-col items-center justify-center">
          <span className="font-semibold">{chord.label}</span>
          {big && <span className="text-[10px] opacity-60">{((chord.end - chord.start)).toFixed(1)}s</span>}
        </div>
        {hasNote && (
          <div className="absolute right-1.5 top-1.5 h-2 w-2" style={{ background: "#00e5ff" }} />
        )}
        {loopStart === i && <div className="absolute bottom-0 left-0 top-0 w-1" style={{ background: "#ff00ff" }} />}
        {loopEnd === i && <div className="absolute bottom-0 right-0 top-0 w-1" style={{ background: "#ff4444" }} />}
      </div>
    );
  };

  if (!showAll) {
    // Windowed view: bigger blocks, current section label
    return (
      <div className="border p-3" style={{ borderColor: "rgba(0, 255, 65, 0.1)", background: "rgba(10, 10, 10, 0.8)" }}>
        {/* Section header + toggle */}
        <div className="mb-2 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="font-mono text-xs font-semibold uppercase tracking-widest" style={{ color: "#00ff41" }}>{currentSectionName}</span>
            <span className="font-mono text-[10px]" style={{ color: "#3a3a3a" }}>
              {currentIndex + 1} / {chords.length}
            </span>
          </div>
          <button onClick={() => setShowAll(true)} className="border px-3 py-1 font-mono text-[11px] font-medium transition-colors hover:bg-green-900/10"
            style={{ borderColor: "rgba(0, 255, 65, 0.15)", color: "#00ff41" }}>
            all_sections &gt;&gt;
          </button>
        </div>

        {/* Windowed chord blocks */}
        <div className="flex gap-1.5">
          {windowStart > 0 && (
            <button onClick={() => onChordClick(windowStart - 1)} className="flex h-14 w-8 shrink-0 items-center justify-center rounded-sm font-mono text-xs" style={{ background: "rgba(26, 26, 26, 0.5)", color: "#3a3a3a" }}>
              &lt;
            </button>
          )}
          {chords.slice(windowStart, windowEnd + 1).map((chord, wi) => renderChordBlock(chord, windowStart + wi, true))}
          {windowEnd < chords.length - 1 && (
            <button onClick={() => onChordClick(windowEnd + 1)} className="flex h-14 w-8 shrink-0 items-center justify-center rounded-sm font-mono text-xs" style={{ background: "rgba(26, 26, 26, 0.5)", color: "#3a3a3a" }}>
              &gt;
            </button>
          )}
        </div>
      </div>
    );
  }

  // Full view: all chords grouped by section
  return (
    <div className="border p-3" style={{ borderColor: "rgba(0, 255, 65, 0.1)", background: "rgba(10, 10, 10, 0.8)" }}>
      {/* Header + collapse */}
      <div className="mb-3 flex items-center justify-between">
        <span className="font-mono text-xs font-semibold uppercase tracking-widest" style={{ color: "#00ff41" }}>// all sections</span>
        <button onClick={() => setShowAll(false)} className="border px-3 py-1 font-mono text-[11px] font-medium transition-colors hover:bg-green-900/10"
          style={{ borderColor: "rgba(0, 255, 65, 0.15)", color: "#00ff41" }}>
          collapse &lt;&lt;
        </button>
      </div>

      {/* Sections */}
      <div className="space-y-3 max-h-64 overflow-y-auto">
        {sections.map((section) => {
          const isCurSection = currentIndex >= section.startIndex && currentIndex <= section.endIndex;
          return (
            <div key={`${section.name}-${section.startIndex}`}>
              <div className="mb-1 flex items-center gap-2">
                <span className="font-mono text-[11px] font-semibold uppercase tracking-widest" style={{ color: isCurSection ? "#00ff41" : "#3a3a3a" }}>
                  {section.name}
                </span>
                <div className="h-px flex-1" style={{ background: "rgba(0, 255, 65, 0.08)" }} />
                <span className="font-mono text-[10px]" style={{ color: "#3a3a3a" }}>
                  {section.endIndex - section.startIndex + 1} chords
                </span>
              </div>
              <div className="flex flex-wrap gap-1">
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
