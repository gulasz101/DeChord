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

export interface CompletedAnalysisResult extends AnalysisResult {
  song_id: number;
}

export type ProcessMode = "analysis_only" | "analysis_and_stems";
export type TabGenerationQuality = "standard" | "high_accuracy" | "high_accuracy_aggressive";

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

export interface SongTabMeta {
  id: number;
  source_stem_key: string;
  source_midi_id: number;
  tab_format: string;
  tuning: string;
  strings: number;
  generator_version: string;
  status: string;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface SongTabsResponse {
  tab: SongTabMeta | null;
}

export interface SongTabRegeneratePayload {
  source_stem_key: string;
}

export interface IdentityUser {
  id: number;
  display_name: string;
  fingerprint_token: string | null;
  username: string | null;
  is_claimed: boolean;
}

export interface IdentityResponse {
  user: IdentityUser;
}

export interface IdentityClaimPayload {
  user_id: number;
  username: string;
  password: string;
}

export interface BandSummary {
  id: number;
  name: string;
  owner_user_id: number;
  created_at: string;
  project_count: number;
}

export interface BandsListResponse {
  bands: BandSummary[];
}

export interface BandCreatePayload {
  name: string;
}

export interface BandCreateResponse {
  band: BandSummary;
}

export interface ProjectSummary {
  id: number;
  band_id: number;
  name: string;
  description: string | null;
  created_at: string;
  song_count: number;
}

export interface ProjectsListResponse {
  projects: ProjectSummary[];
}

export interface ProjectCreatePayload {
  name: string;
  description?: string;
}

export interface ProjectCreateResponse {
  project: ProjectSummary;
}

export interface ProjectSongSummary {
  id: number;
  project_id: number;
  title: string;
  original_filename: string | null;
  created_at: string;
  key: string | null;
  tempo: number | null;
  duration: number | null;
}

export interface ProjectSongsListResponse {
  songs: ProjectSongSummary[];
}
