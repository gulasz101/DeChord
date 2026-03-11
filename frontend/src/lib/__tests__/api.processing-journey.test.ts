import { describe, expect, it, vi } from "vitest";
import { getJobStatus, getResult } from "../api";
import type { CompletedAnalysisResult, JobStatus } from "../types";

const expectedStatus: JobStatus = {
  status: "processing",
  stage: "splitting_stems",
  progress_pct: 45,
  stage_history: ["queued", "analyzing_chords", "splitting_stems"],
  message: "Splitting stems...",
};

const expectedResult: CompletedAnalysisResult = {
  song_id: 77,
  key: "Em",
  tempo: 120,
  duration: 42,
  chords: [],
};

describe("processing journey api", () => {
  it("returns stage-rich status payloads", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => expectedStatus,
    }) as unknown as typeof fetch;

    await expect(getJobStatus("job-123")).resolves.toEqual(expectedStatus);
  });

  it("returns the completed job result payload", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => expectedResult,
    }) as unknown as typeof fetch;

    const result: CompletedAnalysisResult = await getResult("job-123");

    expect(result).toEqual(expectedResult);
  });
});
