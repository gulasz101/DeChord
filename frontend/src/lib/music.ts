const NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];

// Semitone intervals from root for each chord quality
const CHORD_INTERVALS: Record<string, number[]> = {
  "": [0, 4, 7],            // major
  m: [0, 3, 7],             // minor
  "7": [0, 4, 7, 10],       // dominant 7th
  maj7: [0, 4, 7, 11],      // major 7th
  m7: [0, 3, 7, 10],        // minor 7th
  dim: [0, 3, 6],           // diminished
  aug: [0, 4, 8],           // augmented
  sus2: [0, 2, 7],          // suspended 2nd
  sus4: [0, 5, 7],          // suspended 4th
};

/** Bass string open notes (low to high): E1, A1, D2, G2 */
const BASS_STRINGS = [
  { name: "E", midi: 28 },  // E1
  { name: "A", midi: 33 },  // A1
  { name: "D", midi: 38 },  // D2
  { name: "G", midi: 43 },  // G2
];

const NUM_FRETS = 12;

export function noteNameToIndex(name: string): number {
  // Handle flats by converting to sharps
  const normalized = name
    .replace("Db", "C#")
    .replace("Eb", "D#")
    .replace("Gb", "F#")
    .replace("Ab", "G#")
    .replace("Bb", "A#");
  const idx = NOTE_NAMES.indexOf(normalized);
  if (idx === -1) throw new Error(`Unknown note: ${name}`);
  return idx;
}

export function parseChordLabel(label: string): { root: number; quality: string } | null {
  if (label === "N" || label === "X" || !label) return null;

  // Match root note (with optional # or b) and quality
  const match = label.match(/^([A-G][#b]?)(.*)$/);
  if (!match) return null;

  const root = noteNameToIndex(match[1]);
  const quality = match[2];
  return { root, quality };
}

export function getChordNotes(label: string): number[] {
  const parsed = parseChordLabel(label);
  if (!parsed) return [];

  const intervals = CHORD_INTERVALS[parsed.quality] ?? CHORD_INTERVALS[""];
  return intervals.map((i) => (parsed.root + i) % 12);
}

export interface FretPosition {
  string: number; // 0=E, 1=A, 2=D, 3=G
  fret: number;   // 0-12
  note: string;   // note name
}

export function getFretboardPositions(label: string): FretPosition[] {
  const chordNotes = getChordNotes(label);
  if (chordNotes.length === 0) return [];

  const positions: FretPosition[] = [];

  for (let s = 0; s < BASS_STRINGS.length; s++) {
    const openMidi = BASS_STRINGS[s].midi;
    for (let fret = 0; fret <= NUM_FRETS; fret++) {
      const midi = openMidi + fret;
      const noteIndex = midi % 12;
      if (chordNotes.includes(noteIndex)) {
        positions.push({
          string: s,
          fret,
          note: NOTE_NAMES[noteIndex],
        });
      }
    }
  }

  return positions;
}

export { NOTE_NAMES, BASS_STRINGS, NUM_FRETS };
