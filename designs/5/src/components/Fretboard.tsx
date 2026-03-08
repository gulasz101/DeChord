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
    <div className="rounded-xl border px-4 py-3" style={{ borderColor: "rgba(192, 192, 192, 0.06)", background: "rgba(17, 22, 56, 0.7)", backdropFilter: "blur(12px)" }}>
      {/* Fret numbers */}
      <div className="ml-8 flex">
        {Array.from({ length: NUM_FRETS + 1 }, (_, i) => (
          <div key={i} className="flex-1 text-center text-[10px]" style={{ color: "#5a5a6e" }}>{i}</div>
        ))}
      </div>

      {/* Strings */}
      {[...BASS_STRINGS].reverse().map((str, displayIdx) => {
        const stringIdx = BASS_STRINGS.length - 1 - displayIdx;
        return (
          <div key={str.name} className="flex h-8 items-center">
            <div className="w-8 pr-2 text-right font-mono text-xs" style={{ color: "#c0c0c0" }}>{str.name}</div>
            <div className="relative flex flex-1">
              <div className="absolute inset-y-1/2 left-0 right-0 h-px" style={{ background: "rgba(192, 192, 192, 0.15)" }} />
              {Array.from({ length: NUM_FRETS + 1 }, (_, fret) => {
                const { current, next } = findPosition(stringIdx, fret);
                const both = Boolean(current && next);
                return (
                  <div key={fret} className="relative flex flex-1 items-center justify-center">
                    {fret > 0 && <div className="absolute bottom-0 left-0 top-0 w-px" style={{ background: "rgba(192, 192, 192, 0.08)" }} />}
                    {both && (
                      <div className="z-10 flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-bold text-white" style={{ background: "linear-gradient(135deg, #7c3aed, #14b8a6)" }}>
                        {current?.note}
                      </div>
                    )}
                    {!both && current && (
                      <div className="z-10 flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-bold text-white" style={{ background: "#7c3aed" }}>
                        {current.note}
                      </div>
                    )}
                    {!both && !current && next && (
                      <div className="z-10 flex h-5 w-5 items-center justify-center rounded-full border text-[10px] font-bold" style={{ borderColor: "#14b8a6", background: "rgba(20, 184, 166, 0.15)", color: "#14b8a6" }}>
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
      <div className="mt-2 text-center text-sm font-semibold">
        <span style={{ color: "#a78bfa" }}>{chordLabel || "—"}</span>
        {nextChordLabel && <span style={{ color: "#5a5a6e" }}>{"  →  "}</span>}
        {nextChordLabel && <span style={{ color: "#14b8a6" }}>{nextChordLabel}</span>}
      </div>
    </div>
  );
}
