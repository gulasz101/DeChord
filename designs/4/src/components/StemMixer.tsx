import type { StemInfo } from "../lib/types";

interface StemMixerProps {
  stems: StemInfo[];
  activeStemKeys: Set<string>;
  selectedVersions: Record<string, string>;
  onToggleStem: (stemKey: string) => void;
  onSelectVersion: (stemKey: string, stemId: string) => void;
}

export function StemMixer({ stems, activeStemKeys, selectedVersions, onToggleStem, onSelectVersion }: StemMixerProps) {
  const activeStems = stems.filter((s) => !s.isArchived);
  const groups = new Map<string, StemInfo[]>();
  for (const s of activeStems) {
    const arr = groups.get(s.stemKey) ?? [];
    arr.push(s);
    groups.set(s.stemKey, arr);
  }

  return (
    <div className="space-y-3">
      {Array.from(groups.entries()).map(([key, versions]) => {
        const isActive = activeStemKeys.has(key);
        const selectedId = selectedVersions[key] ?? versions[0]?.id;
        const selectedStem = versions.find((v) => v.id === selectedId) ?? versions[0];

        return (
          <div key={key} className="p-3" style={{ border: `2px solid ${isActive ? "#000" : "#ccc"}`, background: isActive ? "#fff" : "#f5f5f5" }}>
            {/* Header row: toggle + label */}
            <div className="flex items-center gap-2.5">
              <button onClick={() => onToggleStem(key)}
                className="flex h-7 w-7 shrink-0 items-center justify-center text-xs font-bold transition-all"
                style={{
                  background: isActive ? "#FFE500" : "#f5f5f5",
                  color: "#000",
                  border: "2px solid #000",
                }}>
                {isActive ? "\u2713" : "\u2014"}
              </button>
              <div className="min-w-0 flex-1">
                <div className="truncate text-sm font-bold uppercase" style={{ color: isActive ? "#000" : "#888" }}>{selectedStem.label}</div>
                <div className="flex items-center gap-1.5 text-[10px] font-bold uppercase" style={{ color: "#888" }}>
                  <span className="px-1 py-0.5" style={{ background: selectedStem.sourceType === "System" ? "#f5f5f5" : "#FFE500", border: "1px solid #000", color: "#000" }}>
                    {selectedStem.sourceType}
                  </span>
                  <span>by {selectedStem.uploaderName}</span>
                </div>
              </div>
            </div>

            {/* Description */}
            <p className="mt-1.5 pl-[38px] text-[11px] leading-snug" style={{ color: "#555" }}>{selectedStem.description}</p>

            {/* Version switcher -- shown when multiple versions exist */}
            {versions.length > 1 && (
              <div className="mt-2 pl-[38px]">
                <label className="mb-1 block text-[10px] font-bold uppercase tracking-widest" style={{ color: "#888" }}>Version</label>
                <div className="space-y-1">
                  {versions.map((v) => (
                    <button key={v.id} onClick={() => onSelectVersion(key, v.id)}
                      className="flex w-full items-center gap-2 px-2.5 py-1.5 text-left text-[11px] font-bold transition-colors hover:bg-yellow-200"
                      style={{
                        background: v.id === selectedId ? "#FFE500" : "transparent",
                        color: "#000",
                        border: v.id === selectedId ? "2px solid #000" : "2px solid transparent",
                      }}>
                      <span className="font-bold">v{v.version}</span>
                      <span className="flex-1 truncate">{v.uploaderName}</span>
                      <span className="text-[9px] uppercase" style={{ color: "#888" }}>{v.sourceType}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Download button */}
            {isActive && (
              <div className="mt-2 pl-[38px]">
                <button className="text-[10px] font-bold uppercase tracking-wider transition-colors hover:text-red-600" style={{ color: "#000", textDecoration: "underline" }}>
                  Download
                </button>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
