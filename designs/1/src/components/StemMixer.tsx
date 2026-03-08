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
    <div className="rounded-xl border p-4" style={{ borderColor: "rgba(196, 168, 130, 0.12)", background: "rgba(26, 18, 9, 0.7)" }}>
      <h3 className="mb-3 text-xs font-medium uppercase tracking-widest" style={{ color: "#8b7d6b" }}>Stem Mixer</h3>
      <div className="space-y-3">
        {Array.from(groups.entries()).map(([key, versions]) => {
          const isActive = activeStemKeys.has(key);
          const selectedId = selectedVersions[key] ?? versions[0]?.id;
          const selectedStem = versions.find((v) => v.id === selectedId) ?? versions[0];

          return (
            <div key={key} className="flex items-center gap-3">
              {/* Toggle */}
              <button onClick={() => onToggleStem(key)}
                className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg text-xs font-bold transition-all"
                style={{
                  background: isActive ? "rgba(180, 83, 9, 0.3)" : "rgba(61, 43, 31, 0.3)",
                  color: isActive ? "#d97706" : "#6b5d4e",
                  border: `1px solid ${isActive ? "rgba(180, 83, 9, 0.4)" : "rgba(196, 168, 130, 0.1)"}`,
                }}>
                {isActive ? "✓" : "—"}
              </button>

              {/* Label */}
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium" style={{ color: isActive ? "#faf5eb" : "#6b5d4e" }}>{selectedStem.label}</span>
                  <span className="text-[10px]" style={{ color: "#6b5d4e" }}>by {selectedStem.uploaderName}</span>
                </div>
              </div>

              {/* Version switcher */}
              {versions.length > 1 && (
                <select value={selectedId} onChange={(e) => onSelectVersion(key, e.target.value)}
                  className="rounded border px-2 py-1 text-[10px]" style={{ background: "rgba(26, 18, 9, 0.6)", borderColor: "rgba(196, 168, 130, 0.15)", color: "#c4a882" }}>
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
