import { useCallback, useState, useRef } from "react";

interface DropZoneProps {
  onFile: (file: File) => void;
  loading?: boolean;
  progress?: string;
}

const ACCEPTED = [".mp3", ".wav", ".m4a", ".aac", ".mp4"];

export function DropZone({ onFile, loading, progress }: DropZoneProps) {
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const file = e.dataTransfer.files[0];
      if (file) onFile(file);
    },
    [onFile],
  );

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) onFile(file);
    },
    [onFile],
  );

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-4">
        <div className="w-8 h-8 border-2 border-gray-400 border-t-white rounded-full animate-spin" />
        <p className="text-gray-400 text-sm">{progress || "Analyzing..."}</p>
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
