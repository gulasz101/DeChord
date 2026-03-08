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
    <div className="border p-4" style={{ borderColor: "#e0ddd6", background: "#ffffff", borderRadius: "2px" }}>
      <h3 className="mb-3 text-xs font-semibold uppercase tracking-[0.15em]" style={{ color: "#6b6b6b" }}>Stem Mixer</h3>
      <div className="space-y-3">
        {Array.from(groups.entries()).map(([key, versions]) => {
          const isActive = activeStemKeys.has(key);
          const selectedId = selectedVersions[key] ?? versions[0]?.id;
          const selectedStem = versions.find((v) => v.id === selectedId) ?? versions[0];

          return (
            <div key={key} className="flex items-center gap-3">
              {/* Toggle */}
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

              {/* Label */}
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium" style={{ color: isActive ? "#1a1a1a" : "#6b6b6b" }}>{selectedStem.label}</span>
                  <span className="text-[10px]" style={{ color: "#6b6b6b" }}>by {selectedStem.uploaderName}</span>
                </div>
              </div>

              {/* Version switcher */}
              {versions.length > 1 && (
                <select value={selectedId} onChange={(e) => onSelectVersion(key, e.target.value)}
                  className="border-b bg-transparent px-1 py-1 text-[10px]" style={{ borderColor: "#d4d0c8", color: "#1a1a1a" }}>
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
