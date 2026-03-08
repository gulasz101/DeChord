import { useMemo } from "react";
import { BASS_STRINGS, NUM_FRETS, getFretboardPositions } from "../lib/music";

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
    const current = currentPositions.find((position) => position.string === string && position.fret === fret);
    const next = nextPositions.find((position) => position.string === string && position.fret === fret);
    return { current, next };
  };

  return (
    <div className="rounded-[var(--radius-lg)] border border-[var(--line)] bg-[var(--panel)] px-4 py-3 shadow-[var(--shadow-soft)]">
      <div className="ml-8 flex">
        {Array.from({ length: NUM_FRETS + 1 }, (_, fret) => (
          <div key={fret} className="flex-1 text-center text-xs text-[var(--muted)]">
            {fret}
          </div>
        ))}
      </div>

      {[...BASS_STRINGS].reverse().map((bassString, displayIndex) => {
        const stringIndex = BASS_STRINGS.length - 1 - displayIndex;
        return (
          <div key={bassString.name} className="flex h-8 items-center">
            <div className="w-8 pr-2 text-right font-mono text-xs text-[var(--muted)]">{bassString.name}</div>
            <div className="relative flex flex-1">
              <div className="absolute inset-y-1/2 left-0 right-0 h-px bg-[var(--track-grid)]" />
              {Array.from({ length: NUM_FRETS + 1 }, (_, fret) => {
                const { current, next } = findPosition(stringIndex, fret);
                const both = Boolean(current && next);
                return (
                  <div key={fret} className="relative flex flex-1 items-center justify-center">
                    {fret > 0 ? <div className="absolute bottom-0 left-0 top-0 w-px bg-[var(--line)]" /> : null}
                    {both ? (
                      <div className="z-10 flex h-5 w-5 items-center justify-center rounded-full bg-[var(--overlap)] text-[10px] font-bold text-white">
                        {current?.note}
                      </div>
                    ) : null}
                    {!both && current ? (
                      <div className="z-10 flex h-5 w-5 items-center justify-center rounded-full bg-[var(--accent)] text-[10px] font-bold text-white">
                        {current.note}
                      </div>
                    ) : null}
                    {!both && !current && next ? (
                      <div className="z-10 flex h-5 w-5 items-center justify-center rounded-full border border-[var(--next-border)] bg-[var(--next-bg)] text-[10px] font-bold text-[var(--next-text)]">
                        {next.note}
                      </div>
                    ) : null}
                  </div>
                );
              })}
            </div>
          </div>
        );
      })}

      <div className="mt-2 text-center text-sm font-semibold text-[var(--text)]">
        <span className="text-[var(--accent)]">{chordLabel || "—"}</span>
        {nextChordLabel ? <span className="text-[var(--muted)]">  →  </span> : null}
        {nextChordLabel ? <span className="text-[var(--next-text)]">{nextChordLabel}</span> : null}
      </div>
    </div>
  );
}
