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
          <div key={key} className="rounded-2xl border p-3" style={{ borderColor: isActive ? "rgba(124, 58, 237, 0.25)" : "rgba(192, 192, 192, 0.06)", background: isActive ? "rgba(17, 22, 56, 0.7)" : "rgba(17, 22, 56, 0.4)", backdropFilter: "blur(8px)" }}>
            {/* Header row: toggle + label */}
            <div className="flex items-center gap-2.5">
              <button onClick={() => onToggleStem(key)}
                className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg text-xs font-bold transition-all"
                style={{
                  background: isActive ? "rgba(124, 58, 237, 0.2)" : "rgba(30, 30, 58, 0.4)",
                  color: isActive ? "#a78bfa" : "#5a5a6e",
                  border: `1px solid ${isActive ? "rgba(124, 58, 237, 0.35)" : "rgba(192, 192, 192, 0.08)"}`,
                }}>
                {isActive ? "✓" : "—"}
              </button>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium truncate" style={{ color: isActive ? "#e2e2f0" : "#5a5a6e" }}>{selectedStem.label}</div>
                <div className="flex items-center gap-1.5 text-[10px]" style={{ color: "#5a5a6e" }}>
                  <span className="rounded px-1 py-0.5" style={{ background: selectedStem.sourceType === "System" ? "rgba(20, 184, 166, 0.15)" : "rgba(124, 58, 237, 0.15)", color: selectedStem.sourceType === "System" ? "#14b8a6" : "#a78bfa" }}>
                    {selectedStem.sourceType}
                  </span>
                  <span>by {selectedStem.uploaderName}</span>
                </div>
              </div>
            </div>

            {/* Description */}
            <p className="mt-1.5 text-[11px] leading-snug pl-[38px]" style={{ color: "#7a7a90" }}>{selectedStem.description}</p>

            {/* Version switcher — shown when multiple versions exist */}
            {versions.length > 1 && (
              <div className="mt-2 pl-[38px]">
                <label className="mb-1 block text-[10px] font-medium uppercase tracking-widest" style={{ fontFamily: "Orbitron, sans-serif", color: "#7a7a90", fontSize: "0.5rem" }}>Version</label>
                <div className="space-y-1">
                  {versions.map((v) => (
                    <button key={v.id} onClick={() => onSelectVersion(key, v.id)}
                      className="flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 text-left text-[11px] transition-colors"
                      style={{
                        background: v.id === selectedId ? "rgba(124, 58, 237, 0.2)" : "transparent",
                        color: v.id === selectedId ? "#a78bfa" : "#7a7a90",
                        border: v.id === selectedId ? "1px solid rgba(124, 58, 237, 0.3)" : "1px solid transparent",
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
                <button className="text-[10px] font-medium transition-colors hover:text-purple-300" style={{ color: "#c0c0c0" }}>
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
