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
          <div key={key} className="border p-3" style={{ borderColor: isActive ? "rgba(0, 255, 65, 0.2)" : "rgba(58, 58, 58, 0.15)", background: isActive ? "rgba(0, 255, 65, 0.03)" : "rgba(17, 17, 17, 0.5)" }}>
            {/* Header row: toggle + label */}
            <div className="flex items-center gap-2.5">
              <button onClick={() => onToggleStem(key)}
                className="flex h-7 w-7 shrink-0 items-center justify-center border font-mono text-xs font-bold transition-all"
                style={{
                  background: isActive ? "rgba(0, 255, 65, 0.15)" : "rgba(26, 26, 26, 0.5)",
                  color: isActive ? "#00ff41" : "#3a3a3a",
                  borderColor: isActive ? "#00ff41" : "rgba(58, 58, 58, 0.3)",
                }}>
                {isActive ? "+" : "-"}
              </button>
              <div className="flex-1 min-w-0">
                <div className="font-mono text-sm font-medium truncate" style={{ color: isActive ? "#00ff41" : "#3a3a3a" }}>{selectedStem.label}</div>
                <div className="flex items-center gap-1.5 font-mono text-[10px]" style={{ color: "#3a3a3a" }}>
                  <span className="px-1 py-0.5" style={{ background: selectedStem.sourceType === "System" ? "rgba(0, 229, 255, 0.1)" : "rgba(255, 0, 255, 0.1)", color: selectedStem.sourceType === "System" ? "#00e5ff" : "#ff00ff" }}>
                    {selectedStem.sourceType}
                  </span>
                  <span>by {selectedStem.uploaderName}</span>
                </div>
              </div>
            </div>

            {/* Description */}
            <p className="mt-1.5 font-mono text-[11px] leading-snug pl-[38px]" style={{ color: "#555" }}>{selectedStem.description}</p>

            {/* Version switcher — shown when multiple versions exist */}
            {versions.length > 1 && (
              <div className="mt-2 pl-[38px]">
                <label className="mb-1 block font-mono text-[10px] font-medium uppercase tracking-widest" style={{ color: "#555" }}>version</label>
                <div className="space-y-1">
                  {versions.map((v) => (
                    <button key={v.id} onClick={() => onSelectVersion(key, v.id)}
                      className="flex w-full items-center gap-2 px-2.5 py-1.5 text-left font-mono text-[11px] transition-colors"
                      style={{
                        background: v.id === selectedId ? "rgba(0, 255, 65, 0.1)" : "transparent",
                        color: v.id === selectedId ? "#00ff41" : "#555",
                        border: v.id === selectedId ? "1px solid rgba(0, 255, 65, 0.25)" : "1px solid transparent",
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
                <button className="font-mono text-[10px] font-medium transition-colors hover:text-cyan-300" style={{ color: "#00e5ff" }}>
                  &gt; download
                </button>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
