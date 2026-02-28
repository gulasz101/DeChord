// frontend/src/components/Fretboard.tsx
import { useMemo } from "react";
import { getFretboardPositions, BASS_STRINGS, NUM_FRETS } from "../lib/music";

interface FretboardProps {
  chordLabel: string | null;
}

export function Fretboard({ chordLabel }: FretboardProps) {
  const positions = useMemo(
    () => (chordLabel ? getFretboardPositions(chordLabel) : []),
    [chordLabel],
  );

  const isActive = (string: number, fret: number) =>
    positions.some((p) => p.string === string && p.fret === fret);

  return (
    <div className="px-4 py-3 bg-gray-900 border-t border-gray-800">
      {/* Fret numbers */}
      <div className="flex ml-8">
        {Array.from({ length: NUM_FRETS + 1 }, (_, i) => (
          <div
            key={i}
            className="flex-1 text-center text-xs text-gray-600"
          >
            {i}
          </div>
        ))}
      </div>
      {/* Strings (G at top, E at bottom — visual convention) */}
      {[...BASS_STRINGS].reverse().map((str, displayIdx) => {
        const stringIdx = BASS_STRINGS.length - 1 - displayIdx;
        return (
          <div key={str.name} className="flex items-center h-8">
            <div className="w-8 text-right pr-2 text-xs text-gray-500 font-mono">
              {str.name}
            </div>
            <div className="flex-1 flex relative">
              {/* String line */}
              <div className="absolute inset-y-1/2 left-0 right-0 h-px bg-gray-600" />
              {Array.from({ length: NUM_FRETS + 1 }, (_, fret) => (
                <div key={fret} className="flex-1 flex items-center justify-center relative">
                  {/* Fret line */}
                  {fret > 0 && (
                    <div className="absolute left-0 top-0 bottom-0 w-px bg-gray-700" />
                  )}
                  {/* Note dot */}
                  {isActive(stringIdx, fret) && (
                    <div className="w-5 h-5 rounded-full bg-blue-500 text-[10px] flex items-center justify-center text-white font-bold z-10">
                      {positions.find(
                        (p) => p.string === stringIdx && p.fret === fret,
                      )?.note}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        );
      })}
      {/* Current chord label */}
      <div className="text-center mt-2 text-lg font-bold text-blue-400">
        {chordLabel || "—"}
      </div>
    </div>
  );
}
