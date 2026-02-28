interface HeaderProps {
  songKey?: string;
  tempo?: number;
  fileName?: string;
}

export function Header({ songKey, tempo, fileName }: HeaderProps) {
  return (
    <header className="flex items-center justify-between px-4 py-2 bg-gray-900 border-b border-gray-800">
      <div className="flex items-center gap-3">
        <h1 className="text-lg font-bold text-white">DeChord</h1>
        {fileName && (
          <span className="text-sm text-gray-400 truncate max-w-64">
            {fileName}
          </span>
        )}
      </div>
      <div className="flex items-center gap-3">
        {songKey && (
          <span className="text-sm text-gray-300">
            {songKey}
            {tempo ? ` | ${tempo} BPM` : ""}
          </span>
        )}
      </div>
    </header>
  );
}
