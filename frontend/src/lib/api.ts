import type {
  JobStatus,
  AnalysisResult,
  UploadResponse,
  SongDetailResponse,
  SongsListResponse,
  SongStemsResponse,
  SongTabsResponse,
  SongNote,
  PlaybackPrefs,
  ProcessMode,
  TabGenerationQuality,
  IdentityResponse,
  IdentityClaimPayload,
  BandsListResponse,
  ProjectsListResponse,
  ProjectSongsListResponse,
} from "./types";

const BASE = "";

export async function uploadAudio(
  file: File,
  processMode: ProcessMode = "analysis_only",
  tabGenerationQuality: TabGenerationQuality = "standard",
): Promise<UploadResponse> {
  const form = new FormData();
  form.append("file", file);
  form.append("process_mode", processMode);
  form.append("tabGenerationQuality", tabGenerationQuality);
  const res = await fetch(`${BASE}/api/analyze`, { method: "POST", body: form });
  if (!res.ok) throw new Error("Upload failed");
  return res.json();
}

export async function getJobStatus(jobId: string): Promise<JobStatus> {
  const res = await fetch(`${BASE}/api/status/${jobId}`);
  if (!res.ok) throw new Error("Status check failed");
  return res.json();
}

export async function getResult(jobId: string): Promise<AnalysisResult> {
  const res = await fetch(`${BASE}/api/result/${jobId}`);
  if (!res.ok) throw new Error("Result fetch failed");
  return res.json();
}

export function getAudioUrl(songId: number): string {
  return `${BASE}/api/audio/${songId}`;
}

export function getStemAudioUrl(songId: number, stemKey: string): string {
  return `${BASE}/api/audio/${songId}/stems/${encodeURIComponent(stemKey)}`;
}

export function getStemDownloadUrl(songId: number, stemKey: string): string {
  return `${BASE}/api/songs/${songId}/stems/${encodeURIComponent(stemKey)}/download`;
}

export function getStemsZipDownloadUrl(songId: number): string {
  return `${BASE}/api/songs/${songId}/stems/download`;
}

export function getMidiFileUrl(songId: number): string {
  return `${BASE}/api/songs/${songId}/midi/file`;
}

export function getTabFileUrl(songId: number): string {
  return `${BASE}/api/songs/${songId}/tabs/file`;
}

export function getTabDownloadUrl(songId: number): string {
  return `${BASE}/api/songs/${songId}/tabs/download`;
}

export async function pollUntilComplete(
  jobId: string,
  onProgress?: (status: JobStatus) => void,
  intervalMs = 1000,
): Promise<AnalysisResult> {
  while (true) {
    const status = await getJobStatus(jobId);
    onProgress?.(status);
    if (status.status === "complete") {
      return getResult(jobId);
    }
    if (status.status === "error") {
      throw new Error(status.error || "Analysis failed");
    }
    await new Promise((r) => setTimeout(r, intervalMs));
  }
}

export async function listSongs(): Promise<SongsListResponse> {
  const res = await fetch(`${BASE}/api/songs`);
  if (!res.ok) throw new Error("Failed to fetch songs");
  return res.json();
}

export async function getSong(songId: number): Promise<SongDetailResponse> {
  const res = await fetch(`${BASE}/api/songs/${songId}`);
  if (!res.ok) throw new Error("Failed to fetch song");
  return res.json();
}

export async function listSongStems(songId: number): Promise<SongStemsResponse> {
  const res = await fetch(`${BASE}/api/songs/${songId}/stems`);
  if (!res.ok) throw new Error("Failed to fetch stems");
  return res.json();
}

export async function getSongTabs(songId: number): Promise<SongTabsResponse> {
  const res = await fetch(`${BASE}/api/songs/${songId}/tabs`);
  if (!res.ok) throw new Error("Failed to fetch tabs metadata");
  return res.json();
}

export async function createSongNote(
  songId: number,
  payload: {
    type: "time" | "chord";
    text: string;
    timestamp_sec?: number;
    chord_index?: number;
    toast_duration_sec?: number;
  },
): Promise<SongNote> {
  const res = await fetch(`${BASE}/api/songs/${songId}/notes`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error("Failed to create note");
  return res.json();
}

export async function updateSongNote(
  noteId: number,
  payload: { text?: string; toast_duration_sec?: number },
): Promise<{ id: number; text: string; toast_duration_sec: number | null }> {
  const res = await fetch(`${BASE}/api/notes/${noteId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error("Failed to update note");
  return res.json();
}

export async function deleteSongNote(noteId: number): Promise<void> {
  const res = await fetch(`${BASE}/api/notes/${noteId}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error("Failed to delete note");
}

export async function savePlaybackPrefs(
  songId: number,
  prefs: PlaybackPrefs,
): Promise<PlaybackPrefs> {
  const res = await fetch(`${BASE}/api/songs/${songId}/playback-prefs`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(prefs),
  });
  if (!res.ok) throw new Error("Failed to save playback prefs");
  return res.json();
}

export async function resolveIdentity(fingerprintToken: string): Promise<IdentityResponse> {
  const res = await fetch(`${BASE}/api/identity/resolve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ fingerprint_token: fingerprintToken }),
  });
  if (!res.ok) throw new Error("Failed to resolve identity");
  return res.json();
}

export async function claimIdentity(payload: IdentityClaimPayload): Promise<IdentityResponse> {
  const res = await fetch(`${BASE}/api/identity/claim`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error("Failed to claim identity");
  return res.json();
}

export async function listBands(): Promise<BandsListResponse> {
  const res = await fetch(`${BASE}/api/bands`);
  if (!res.ok) throw new Error("Failed to fetch bands");
  return res.json();
}

export async function listBandProjects(bandId: number): Promise<ProjectsListResponse> {
  const res = await fetch(`${BASE}/api/bands/${bandId}/projects`);
  if (!res.ok) throw new Error("Failed to fetch projects");
  return res.json();
}

export async function listProjectSongs(projectId: number): Promise<ProjectSongsListResponse> {
  const res = await fetch(`${BASE}/api/projects/${projectId}/songs`);
  if (!res.ok) throw new Error("Failed to fetch project songs");
  return res.json();
}
