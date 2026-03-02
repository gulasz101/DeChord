import type { JobStatus } from "./types";

export function deriveStemWarning(status: Pick<JobStatus, "stems_status" | "stems_error">): string | null {
  if (status.stems_status !== "failed") return null;
  if (status.stems_error && status.stems_error.trim().length > 0) {
    return `Stem splitting failed: ${status.stems_error}`;
  }
  return "Stem splitting failed.";
}
