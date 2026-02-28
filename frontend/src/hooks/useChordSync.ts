import { useMemo } from "react";
import type { Chord } from "../lib/types";

export function useChordSync(chords: Chord[], currentTime: number) {
  const currentIndex = useMemo(() => {
    // Binary search for current chord
    let lo = 0;
    let hi = chords.length - 1;
    while (lo <= hi) {
      const mid = Math.floor((lo + hi) / 2);
      if (currentTime < chords[mid].start) {
        hi = mid - 1;
      } else if (currentTime >= chords[mid].end) {
        lo = mid + 1;
      } else {
        return mid;
      }
    }
    return -1;
  }, [chords, currentTime]);

  const currentChord = currentIndex >= 0 ? chords[currentIndex] : null;

  const progress = currentChord
    ? (currentTime - currentChord.start) / (currentChord.end - currentChord.start)
    : 0;

  return { currentIndex, currentChord, progress };
}
