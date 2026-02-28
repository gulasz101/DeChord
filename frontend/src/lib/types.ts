export interface Chord {
  start: number;
  end: number;
  label: string;
}

export interface AnalysisResult {
  key: string;
  tempo: number;
  duration: number;
  chords: Chord[];
}

export interface JobStatus {
  status: "queued" | "processing" | "complete" | "error";
  progress?: string;
  error?: string;
}
