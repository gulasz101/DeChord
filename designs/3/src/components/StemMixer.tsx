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
          <div key={key} className="border p-3" style={{ borderColor: isActive ? "rgba(230, 57, 70, 0.25)" : "#e0ddd6", background: isActive ? "#ffffff" : "#f8f6f1", borderRadius: "2px" }}>
            {/* Header row: toggle + label */}
            <div className="flex items-center gap-2.5">
              <button onClick={() => onToggleStem(key)}
                className="flex h-7 w-7 shrink-0 items-center justify-center text-xs font-bold transition-all"
                style={{
                  background: isActive ? "#1a1a1a" : "#f0ede6",
                  color: isActive ? "#ffffff" : "#6b6b6b",
                  border: `1px solid ${isActive ? "#1a1a1a" : "#e0ddd6"}`,
                  borderRadius: "2px",
                }}>
                {isActive ? "\u2713" : "\u2014"}
              </button>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium truncate" style={{ color: isActive ? "#1a1a1a" : "#6b6b6b" }}>{selectedStem.label}</div>
                <div className="flex items-center gap-1.5 text-[10px]" style={{ color: "#6b6b6b" }}>
                  <span className="border px-1 py-0.5" style={{ background: selectedStem.sourceType === "System" ? "rgba(45, 106, 48, 0.08)" : "rgba(230, 57, 70, 0.08)", color: selectedStem.sourceType === "System" ? "#2d6a30" : "#e63946", borderColor: selectedStem.sourceType === "System" ? "rgba(45, 106, 48, 0.2)" : "rgba(230, 57, 70, 0.2)", borderRadius: "2px" }}>
                    {selectedStem.sourceType}
                  </span>
                  <span>by {selectedStem.uploaderName}</span>
                </div>
              </div>
            </div>

            {/* Description */}
            <p className="mt-1.5 text-[11px] leading-snug pl-[38px]" style={{ color: "#6b6b6b" }}>{selectedStem.description}</p>

            {/* Version switcher — shown when multiple versions exist */}
            {versions.length > 1 && (
              <div className="mt-2 pl-[38px]">
                <label className="mb-1 block text-[10px] font-medium uppercase tracking-[0.15em]" style={{ color: "#6b6b6b" }}>Version</label>
                <div className="space-y-1">
                  {versions.map((v) => (
                    <button key={v.id} onClick={() => onSelectVersion(key, v.id)}
                      className="flex w-full items-center gap-2 px-2.5 py-1.5 text-left text-[11px] transition-colors"
                      style={{
                        background: v.id === selectedId ? "rgba(230, 57, 70, 0.06)" : "transparent",
                        color: v.id === selectedId ? "#e63946" : "#6b6b6b",
                        border: v.id === selectedId ? "1px solid rgba(230, 57, 70, 0.25)" : "1px solid transparent",
                        borderRadius: "2px",
                      }}>
                      <span className="font-semibold">v{v.version}</span>
                      <span className="flex-1 truncate">{v.uploaderName}</span>
                      <span className="text-[9px] opacity-60">{v.sourceType}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Download button */}
            {isActive && (
              <div className="mt-2 pl-[38px]">
                <button className="text-[10px] font-medium transition-colors hover:text-[#e63946]" style={{ color: "#1a1a1a" }}>
                  ↓ Download
                </button>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
