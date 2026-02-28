export interface Chord {
  start: number;
  end: number;
  label: string;
}

export interface AnalysisResult {
  song_id?: number;
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

export interface UploadResponse {
  job_id: string;
  song_id: number;
}

export interface SongSummary {
  id: number;
  title: string;
  original_filename: string | null;
  created_at: string;
  key: string | null;
  tempo: number | null;
  duration: number | null;
}

export interface SongMeta {
  id: number;
  title: string;
  original_filename: string | null;
  mime_type: string | null;
  created_at: string;
}

export interface SongNote {
  id: number;
  type: "time" | "chord";
  timestamp_sec: number | null;
  chord_index: number | null;
  text: string;
  toast_duration_sec: number | null;
}

export interface PlaybackPrefs {
  speed_percent: number;
  volume: number;
  loop_start_index: number | null;
  loop_end_index: number | null;
}

export interface SongDetailResponse {
  song: SongMeta;
  analysis: AnalysisResult | null;
  notes: SongNote[];
  playback_prefs: PlaybackPrefs;
}

export interface SongsListResponse {
  songs: SongSummary[];
}
