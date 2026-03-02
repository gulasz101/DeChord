import { useCallback, useState, useRef } from "react";
import type { JobStage, ProcessMode } from "../lib/types";

interface DropZoneProps {
  onFile: (file: File, mode: ProcessMode) => void;
  loading?: boolean;
  progressText?: string;
  progressPct?: number;
  stageProgressPct?: number;
  stage?: JobStage;
}

const ACCEPTED = [".mp3", ".wav", ".m4a", ".aac", ".mp4"];

export function DropZone({
  onFile,
  loading,
  progressText,
  progressPct,
  stageProgressPct,
  stage,
}: DropZoneProps) {
  const [dragOver, setDragOver] = useState(false);
  const [mode, setMode] = useState<ProcessMode>("analysis_only");
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const file = e.dataTransfer.files[0];
      if (file) onFile(file, mode);
    },
    [onFile, mode],
  );

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) onFile(file, mode);
    },
    [onFile, mode],
  );

  if (loading) {
    const overallPct = Math.round(progressPct ?? 0);
    const currentStagePct = Math.round(stageProgressPct ?? 0);
    return (
      <div className="flex w-full max-w-md flex-col items-center justify-center gap-4 rounded-xl border border-slate-700 bg-slate-900/70 p-4">
        <div className="w-8 h-8 border-2 border-gray-400 border-t-white rounded-full animate-spin" />
        <p className="text-gray-300 text-sm">{progressText || "Processing..."}</p>
        <div className="w-full">
          <div className="mb-1 flex items-center justify-between text-xs text-slate-400">
            <span>Overall</span>
            <span>{overallPct}%</span>
          </div>
          <div className="h-2 rounded bg-slate-800">
            <div
              className="h-2 rounded bg-blue-500 transition-all"
              style={{ width: `${Math.max(0, Math.min(overallPct, 100))}%` }}
            />
          </div>
        </div>
        <div className="w-full">
          <div className="mb-1 flex items-center justify-between text-xs text-slate-400">
            <span>{stage || "stage"}</span>
            <span>{currentStagePct}%</span>
          </div>
          <div className="h-2 rounded bg-slate-800">
            <div
              className="h-2 rounded bg-emerald-500 transition-all"
              style={{ width: `${Math.max(0, Math.min(currentStagePct, 100))}%` }}
            />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setDragOver(true);
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={handleDrop}
      onClick={() => inputRef.current?.click()}
      className={`flex flex-col items-center justify-center h-64 border-2 border-dashed rounded-lg cursor-pointer transition-colors ${
        dragOver
          ? "border-blue-400 bg-blue-400/10"
          : "border-gray-600 hover:border-gray-400"
      }`}
    >
      <p className="text-gray-400 mb-2">Drop audio file here or click to browse</p>
      <p className="text-gray-600 text-sm">MP3, WAV, M4A, AAC</p>
      <div className="mt-3 flex items-center gap-2 text-sm text-gray-300">
        <label htmlFor="process-mode" className="text-gray-400">Mode</label>
        <select
          id="process-mode"
          name="process-mode"
          value={mode}
          onClick={(e) => e.stopPropagation()}
          onChange={(e) => setMode(e.target.value as ProcessMode)}
          className="rounded border border-gray-600 bg-slate-900 px-2 py-1 text-gray-200"
        >
          <option value="analysis_only">Analyze chords only</option>
          <option value="analysis_and_stems">Analyze + split stems</option>
        </select>
      </div>
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED.join(",")}
        onChange={handleChange}
        className="hidden"
      />
    </div>
  );
}
