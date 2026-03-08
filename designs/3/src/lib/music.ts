const NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];

const CHORD_INTERVALS: Record<string, number[]> = {
  "": [0, 4, 7],
  m: [0, 3, 7],
  "7": [0, 4, 7, 10],
  maj7: [0, 4, 7, 11],
  m7: [0, 3, 7, 10],
  dim: [0, 3, 6],
  aug: [0, 4, 8],
  sus2: [0, 2, 7],
  sus4: [0, 5, 7],
};

const BASS_STRINGS = [
  { name: "E", midi: 28 },
  { name: "A", midi: 33 },
  { name: "D", midi: 38 },
  { name: "G", midi: 43 },
];

const NUM_FRETS = 12;

function noteNameToIndex(name: string): number {
  const normalized = name
    .replace("Db", "C#").replace("Eb", "D#").replace("Gb", "F#")
    .replace("Ab", "G#").replace("Bb", "A#");
  const idx = NOTE_NAMES.indexOf(normalized);
  if (idx === -1) return 0;
  return idx;
}

function parseChordLabel(label: string): { root: number; quality: string } | null {
  if (label === "N" || label === "X" || !label) return null;
  const match = label.match(/^([A-G][#b]?)(.*)$/);
  if (!match) return null;
  return { root: noteNameToIndex(match[1]), quality: match[2] };
}

function getChordNotes(label: string): number[] {
  const parsed = parseChordLabel(label);
  if (!parsed) return [];
  const intervals = CHORD_INTERVALS[parsed.quality] ?? CHORD_INTERVALS[""];
  return intervals.map((i) => (parsed.root + i) % 12);
}

export interface FretPosition {
  string: number;
  fret: number;
  note: string;
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
        positions.push({ string: s, fret, note: NOTE_NAMES[noteIndex] });
      }
    }
  }
  return positions;
}

export { NOTE_NAMES, BASS_STRINGS, NUM_FRETS };
