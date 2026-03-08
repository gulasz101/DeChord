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
    <div className="border p-4" style={{ borderColor: "rgba(0, 255, 65, 0.12)", background: "rgba(10, 10, 10, 0.9)" }}>
      <h3 className="mb-3 font-mono text-xs font-medium uppercase tracking-widest" style={{ color: "#00e5ff" }}>// stem mixer</h3>
      <div className="space-y-3">
        {Array.from(groups.entries()).map(([key, versions]) => {
          const isActive = activeStemKeys.has(key);
          const selectedId = selectedVersions[key] ?? versions[0]?.id;
          const selectedStem = versions.find((v) => v.id === selectedId) ?? versions[0];

          return (
            <div key={key} className="flex items-center gap-3">
              {/* Toggle */}
              <button onClick={() => onToggleStem(key)}
                className="flex h-7 w-7 shrink-0 items-center justify-center border font-mono text-xs font-bold transition-all"
                style={{
                  background: isActive ? "rgba(0, 255, 65, 0.15)" : "rgba(26, 26, 26, 0.5)",
                  color: isActive ? "#00ff41" : "#3a3a3a",
                  borderColor: isActive ? "#00ff41" : "rgba(58, 58, 58, 0.3)",
                }}>
                {isActive ? "+" : "-"}
              </button>

              {/* Label */}
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-sm font-medium" style={{ color: isActive ? "#00ff41" : "#3a3a3a" }}>{selectedStem.label}</span>
                  <span className="font-mono text-[10px]" style={{ color: "#3a3a3a" }}>by {selectedStem.uploaderName}</span>
                </div>
              </div>

              {/* Version switcher */}
              {versions.length > 1 && (
                <select value={selectedId} onChange={(e) => onSelectVersion(key, e.target.value)}
                  className="border px-2 py-1 font-mono text-[10px]" style={{ background: "#111111", borderColor: "rgba(0, 255, 65, 0.15)", color: "#00e5ff" }}>
                  {versions.map((v) => (
                    <option key={v.id} value={v.id}>v{v.version} -- {v.uploaderName}</option>
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
