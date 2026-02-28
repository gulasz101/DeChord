import { useMemo } from "react";
import { getFretboardPositions, BASS_STRINGS, NUM_FRETS } from "../lib/music";

interface FretboardProps {
  chordLabel: string | null;
  nextChordLabel?: string | null;
}

export function Fretboard({ chordLabel, nextChordLabel }: FretboardProps) {
  const currentPositions = useMemo(
    () => (chordLabel ? getFretboardPositions(chordLabel) : []),
    [chordLabel],
  );
  const nextPositions = useMemo(
    () => (nextChordLabel ? getFretboardPositions(nextChordLabel) : []),
    [nextChordLabel],
  );

  const findPosition = (string: number, fret: number) => {
    const current = currentPositions.find((p) => p.string === string && p.fret === fret);
    const next = nextPositions.find((p) => p.string === string && p.fret === fret);
    return { current, next };
  };

  return (
    <div className="border-t border-slate-800 bg-slate-900 px-4 py-3">
      <div className="ml-8 flex">
        {Array.from({ length: NUM_FRETS + 1 }, (_, i) => (
          <div key={i} className="flex-1 text-center text-xs text-slate-500">
            {i}
          </div>
        ))}
      </div>

      {[...BASS_STRINGS].reverse().map((str, displayIdx) => {
        const stringIdx = BASS_STRINGS.length - 1 - displayIdx;
        return (
          <div key={str.name} className="flex h-8 items-center">
            <div className="w-8 pr-2 text-right font-mono text-xs text-slate-400">{str.name}</div>
            <div className="relative flex flex-1">
              <div className="absolute inset-y-1/2 left-0 right-0 h-px bg-slate-600" />
              {Array.from({ length: NUM_FRETS + 1 }, (_, fret) => {
                const { current, next } = findPosition(stringIdx, fret);
                const both = Boolean(current && next);
                return (
                  <div key={fret} className="relative flex flex-1 items-center justify-center">
                    {fret > 0 && <div className="absolute bottom-0 left-0 top-0 w-px bg-slate-700" />}
                    {both && (
                      <div className="z-10 flex h-5 w-5 items-center justify-center rounded-full bg-fuchsia-500 text-[10px] font-bold text-white">
                        {current?.note}
                      </div>
                    )}
                    {!both && current && (
                      <div className="z-10 flex h-5 w-5 items-center justify-center rounded-full bg-blue-500 text-[10px] font-bold text-white">
                        {current.note}
                      </div>
                    )}
                    {!both && !current && next && (
                      <div className="z-10 flex h-5 w-5 items-center justify-center rounded-full border border-amber-200 bg-amber-700 text-[10px] font-bold text-amber-100">
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

      <div className="mt-2 text-center text-sm font-semibold text-slate-200">
        <span className="text-blue-400">{chordLabel || "—"}</span>
        {nextChordLabel ? <span className="text-slate-500">  →  </span> : null}
        {nextChordLabel ? <span className="text-amber-100">{nextChordLabel}</span> : null}
      </div>
    </div>
  );
}
