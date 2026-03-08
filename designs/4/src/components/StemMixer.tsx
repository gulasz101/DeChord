import type { StemInfo } from "../lib/types";

interface StemMixerProps {
  stems: StemInfo[];
  activeStemKeys: Set<string>;
  selectedVersions: Record<string, string>; // stemKey -> stemId
  onToggleStem: (stemKey: string) => void;
  onSelectVersion: (stemKey: string, stemId: string) => void;
}

export function StemMixer({ stems, activeStemKeys, selectedVersions, onToggleStem, onSelectVersion }: StemMixerProps) {
  const activeStems = stems.filter((s) => !s.isArchived);
  // Group by stemKey
  const groups = new Map<string, StemInfo[]>();
  for (const s of activeStems) {
    const arr = groups.get(s.stemKey) ?? [];
    arr.push(s);
    groups.set(s.stemKey, arr);
  }

  return (
    <div className="p-4" style={{ border: "3px solid #000", background: "#fff" }}>
      <h3 className="mb-3 text-xs font-bold uppercase tracking-widest" style={{ color: "#000" }}>Stem Mixer</h3>
      <div style={{ border: "2px solid #000" }}>
        {Array.from(groups.entries()).map(([key, versions]) => {
          const isActive = activeStemKeys.has(key);
          const selectedId = selectedVersions[key] ?? versions[0]?.id;
          const selectedStem = versions.find((v) => v.id === selectedId) ?? versions[0];

          return (
            <div key={key} className="flex items-center gap-3 p-3" style={{ borderBottom: "2px solid #000" }}>
              {/* Toggle */}
              <button onClick={() => onToggleStem(key)}
                className="flex h-7 w-7 shrink-0 items-center justify-center text-xs font-bold transition-all"
                style={{
                  background: isActive ? "#FFE500" : "#f5f5f5",
                  color: "#000",
                  border: "2px solid #000",
                }}>
                {isActive ? "✓" : "—"}
              </button>

              {/* Label */}
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-bold uppercase" style={{ color: isActive ? "#000" : "#888" }}>{selectedStem.label}</span>
                  <span className="text-[10px] uppercase" style={{ color: "#888" }}>by {selectedStem.uploaderName}</span>
                </div>
              </div>

              {/* Version switcher */}
              {versions.length > 1 && (
                <select value={selectedId} onChange={(e) => onSelectVersion(key, e.target.value)}
                  className="px-2 py-1 text-[10px] font-bold" style={{ background: "#fff", border: "2px solid #000", color: "#000" }}>
                  {versions.map((v) => (
                    <option key={v.id} value={v.id}>v{v.version} — {v.uploaderName}</option>
                  ))}
                </select>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
