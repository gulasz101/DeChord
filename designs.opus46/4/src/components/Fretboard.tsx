import { useMemo } from "react";
import { getFretboardPositions, BASS_STRINGS, NUM_FRETS } from "../lib/music";

interface FretboardProps {
  chordLabel: string | null;
  nextChordLabel?: string | null;
}

export function Fretboard({ chordLabel, nextChordLabel }: FretboardProps) {
  const currentPositions = useMemo(() => (chordLabel ? getFretboardPositions(chordLabel) : []), [chordLabel]);
  const nextPositions = useMemo(() => (nextChordLabel ? getFretboardPositions(nextChordLabel) : []), [nextChordLabel]);

  const findPosition = (string: number, fret: number) => ({
    current: currentPositions.find((p) => p.string === string && p.fret === fret),
    next: nextPositions.find((p) => p.string === string && p.fret === fret),
  });

  return (
    <div className="px-4 py-3" style={{ border: "3px solid #000", background: "#fff" }}>
      {/* Fret numbers */}
      <div className="ml-8 flex">
        {Array.from({ length: NUM_FRETS + 1 }, (_, i) => (
          <div key={i} className="flex-1 text-center text-[10px] font-bold" style={{ color: "#888" }}>{i}</div>
        ))}
      </div>

      {/* Strings */}
      {[...BASS_STRINGS].reverse().map((str, displayIdx) => {
        const stringIdx = BASS_STRINGS.length - 1 - displayIdx;
        return (
          <div key={str.name} className="flex h-8 items-center">
            <div className="w-8 pr-2 text-right font-mono text-xs font-bold" style={{ color: "#000" }}>{str.name}</div>
            <div className="relative flex flex-1">
              <div className="absolute inset-y-1/2 left-0 right-0 h-px" style={{ background: "#000" }} />
              {Array.from({ length: NUM_FRETS + 1 }, (_, fret) => {
                const { current, next } = findPosition(stringIdx, fret);
                const both = Boolean(current && next);
                return (
                  <div key={fret} className="relative flex flex-1 items-center justify-center">
                    {fret > 0 && <div className="absolute bottom-0 left-0 top-0 w-0.5" style={{ background: "#333" }} />}
                    {both && (
                      <div className="z-10 flex h-6 w-6 items-center justify-center text-[10px] font-bold" style={{ background: "#FFE500", border: "2px solid #000", color: "#000" }}>
                        {current?.note}
                      </div>
                    )}
                    {!both && current && (
                      <div className="z-10 flex h-6 w-6 items-center justify-center text-[10px] font-bold" style={{ background: "#000", color: "#FFE500" }}>
                        {current.note}
                      </div>
                    )}
                    {!both && !current && next && (
                      <div className="z-10 flex h-6 w-6 items-center justify-center text-[10px] font-bold" style={{ border: "2px solid #FF0000", background: "transparent", color: "#FF0000" }}>
                        {next.note}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        );
      })}

      {/* Current / next chord label */}
      <div className="mt-2 text-center text-sm font-bold uppercase">
        <span style={{ color: "#000", background: "#FFE500", padding: "2px 8px" }}>{chordLabel || "—"}</span>
        {nextChordLabel && <span style={{ color: "#888" }}>{"  →  "}</span>}
        {nextChordLabel && <span style={{ color: "#FF0000" }}>{nextChordLabel}</span>}
      </div>
    </div>
  );
}
