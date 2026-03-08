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
    <div className="border px-4 py-3" style={{ borderColor: "rgba(0, 255, 65, 0.12)", background: "rgba(10, 10, 10, 0.9)" }}>
      {/* Fret numbers */}
      <div className="ml-8 flex">
        {Array.from({ length: NUM_FRETS + 1 }, (_, i) => (
          <div key={i} className="flex-1 text-center font-mono text-[10px]" style={{ color: "#3a3a3a" }}>{i}</div>
        ))}
      </div>

      {/* Strings */}
      {[...BASS_STRINGS].reverse().map((str, displayIdx) => {
        const stringIdx = BASS_STRINGS.length - 1 - displayIdx;
        return (
          <div key={str.name} className="flex h-8 items-center">
            <div className="w-8 pr-2 text-right font-mono text-xs" style={{ color: "#00e5ff" }}>{str.name}</div>
            <div className="relative flex flex-1">
              <div className="absolute inset-y-1/2 left-0 right-0 h-px" style={{ background: "rgba(0, 255, 65, 0.15)" }} />
              {Array.from({ length: NUM_FRETS + 1 }, (_, fret) => {
                const { current, next } = findPosition(stringIdx, fret);
                const both = Boolean(current && next);
                return (
                  <div key={fret} className="relative flex flex-1 items-center justify-center">
                    {fret > 0 && <div className="absolute bottom-0 left-0 top-0 w-px" style={{ background: "rgba(0, 255, 65, 0.08)" }} />}
                    {both && (
                      <div className="z-10 flex h-5 w-5 items-center justify-center font-mono text-[10px] font-bold" style={{ background: "#ff00ff", color: "#ffffff", boxShadow: "0 0 8px rgba(255, 0, 255, 0.5)" }}>
                        {current?.note}
                      </div>
                    )}
                    {!both && current && (
                      <div className="z-10 flex h-5 w-5 items-center justify-center font-mono text-[10px] font-bold" style={{ background: "#00ff41", color: "#0a0a0a", boxShadow: "0 0 8px rgba(0, 255, 65, 0.5)" }}>
                        {current.note}
                      </div>
                    )}
                    {!both && !current && next && (
                      <div className="z-10 flex h-5 w-5 items-center justify-center border font-mono text-[10px] font-bold" style={{ borderColor: "#00e5ff", background: "rgba(0, 229, 255, 0.1)", color: "#00e5ff" }}>
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
      <div className="mt-2 text-center font-mono text-sm font-semibold">
        <span className="glow-green" style={{ color: "#00ff41" }}>{chordLabel || "---"}</span>
        {nextChordLabel && <span style={{ color: "#3a3a3a" }}>{"  >>  "}</span>}
        {nextChordLabel && <span className="glow-cyan" style={{ color: "#00e5ff" }}>{nextChordLabel}</span>}
      </div>
    </div>
  );
}
