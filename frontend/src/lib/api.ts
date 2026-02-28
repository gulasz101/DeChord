import type { JobStatus, AnalysisResult } from "./types";

const BASE = "";

export async function uploadAudio(file: File): Promise<string> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${BASE}/api/analyze`, { method: "POST", body: form });
  if (!res.ok) throw new Error("Upload failed");
  const data = await res.json();
  return data.job_id;
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

export function getAudioUrl(jobId: string): string {
  return `${BASE}/api/audio/${jobId}`;
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
