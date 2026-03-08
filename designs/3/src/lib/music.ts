const NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];

const CHORD_INTERVALS: Record<string, number[]> = {
  "": [0, 4, 7],
  m: [0, 3, 7],
  "7": [0, 4, 7, 10],
  maj7: [0, 4, 7, 11],
  m7: [0, 3, 7, 10],
  sus2: [0, 2, 7],
  sus4: [0, 5, 7],
};

export const BASS_STRINGS = [
  { name: "E", midi: 28 },
  { name: "A", midi: 33 },
  { name: "D", midi: 38 },
  { name: "G", midi: 43 },
];

export const NUM_FRETS = 12;

export interface FretPosition {
  string: number;
  fret: number;
  note: string;
}

function noteNameToIndex(name: string): number {
  const normalized = name
    .replace("Db", "C#")
    .replace("Eb", "D#")
    .replace("Gb", "F#")
    .replace("Ab", "G#")
    .replace("Bb", "A#");
  const index = NOTE_NAMES.indexOf(normalized);
  if (index === -1) {
    throw new Error(`Unknown note: ${name}`);
  }
  return index;
}

function parseChordLabel(label: string) {
  if (!label || label === "N" || label === "X") {
    return null;
  }
  const match = label.match(/^([A-G][#b]?)(.*)$/);
  if (!match) {
    return null;
  }
  return {
    root: noteNameToIndex(match[1]),
    quality: match[2],
  };
}

function getChordNotes(label: string): number[] {
  const parsed = parseChordLabel(label);
  if (!parsed) {
    return [];
  }
  const intervals = CHORD_INTERVALS[parsed.quality] ?? CHORD_INTERVALS[""];
  return intervals.map((interval) => (parsed.root + interval) % 12);
}

export function getFretboardPositions(label: string): FretPosition[] {
  const chordNotes = getChordNotes(label);
  if (chordNotes.length === 0) {
    return [];
  }

  const positions: FretPosition[] = [];
  for (let string = 0; string < BASS_STRINGS.length; string += 1) {
    const openMidi = BASS_STRINGS[string].midi;
    for (let fret = 0; fret <= NUM_FRETS; fret += 1) {
      const noteIndex = (openMidi + fret) % 12;
      if (chordNotes.includes(noteIndex)) {
        positions.push({
          string,
          fret,
          note: NOTE_NAMES[noteIndex],
        });
      }
    }
  }
  return positions;
}
