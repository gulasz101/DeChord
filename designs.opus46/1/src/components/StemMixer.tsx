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
          <div key={key} className="rounded-xl border p-3" style={{ borderColor: isActive ? "rgba(180, 83, 9, 0.25)" : "rgba(196, 168, 130, 0.08)", background: isActive ? "rgba(26, 18, 9, 0.6)" : "rgba(26, 18, 9, 0.3)" }}>
            {/* Header row: toggle + label */}
            <div className="flex items-center gap-2.5">
              <button onClick={() => onToggleStem(key)}
                className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg text-xs font-bold transition-all"
                style={{
                  background: isActive ? "rgba(180, 83, 9, 0.3)" : "rgba(61, 43, 31, 0.3)",
                  color: isActive ? "#d97706" : "#6b5d4e",
                  border: `1px solid ${isActive ? "rgba(180, 83, 9, 0.4)" : "rgba(196, 168, 130, 0.1)"}`,
                }}>
                {isActive ? "✓" : "—"}
              </button>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium truncate" style={{ color: isActive ? "#faf5eb" : "#6b5d4e" }}>{selectedStem.label}</div>
                <div className="flex items-center gap-1.5 text-[10px]" style={{ color: "#6b5d4e" }}>
                  <span className="rounded px-1 py-0.5" style={{ background: selectedStem.sourceType === "System" ? "rgba(107, 114, 52, 0.15)" : "rgba(180, 83, 9, 0.15)", color: selectedStem.sourceType === "System" ? "#a3b236" : "#d97706" }}>
                    {selectedStem.sourceType}
                  </span>
                  <span>by {selectedStem.uploaderName}</span>
                </div>
              </div>
            </div>

            {/* Description */}
            <p className="mt-1.5 text-[11px] leading-snug pl-[38px]" style={{ color: "#8b7d6b" }}>{selectedStem.description}</p>

            {/* Version switcher — shown when multiple versions exist */}
            {versions.length > 1 && (
              <div className="mt-2 pl-[38px]">
                <label className="mb-1 block text-[10px] font-medium uppercase tracking-wider" style={{ color: "#8b7d6b" }}>Version</label>
                <div className="space-y-1">
                  {versions.map((v) => (
                    <button key={v.id} onClick={() => onSelectVersion(key, v.id)}
                      className="flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 text-left text-[11px] transition-colors"
                      style={{
                        background: v.id === selectedId ? "rgba(180, 83, 9, 0.2)" : "transparent",
                        color: v.id === selectedId ? "#d97706" : "#8b7d6b",
                        border: v.id === selectedId ? "1px solid rgba(180, 83, 9, 0.3)" : "1px solid transparent",
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
                <button className="text-[10px] font-medium transition-colors hover:text-amber-300" style={{ color: "#c4a882" }}>
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
