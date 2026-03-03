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

export type ProcessMode = "analysis_only" | "analysis_and_stems";

export type JobStage =
  | "queued"
  | "analyzing_chords"
  | "splitting_stems"
  | "transcribing_bass_midi"
  | "generating_tabs"
  | "persisting"
  | "complete"
  | "error";

export interface JobStatus {
  status: "queued" | "processing" | "complete" | "error";
  stage?: JobStage;
  stage_history?: JobStage[];
  progress_pct?: number;
  stage_progress_pct?: number;
  message?: string;
  stems_status?: "queued" | "complete" | "failed" | "not_requested";
  stems_error?: string | null;
  midi_status?: "queued" | "complete" | "failed" | "not_requested";
  midi_error?: string | null;
  tab_status?: "queued" | "complete" | "failed" | "not_requested";
  tab_error?: string | null;
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

export interface StemInfo {
  stem_key: string;
  relative_path: string;
  mime_type: string | null;
  duration: number | null;
}

export interface SongStemsResponse {
  stems: StemInfo[];
}
