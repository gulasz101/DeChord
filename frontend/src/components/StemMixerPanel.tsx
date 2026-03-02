import type { StemInfo } from "../lib/types";

interface StemMixerPanelProps {
  stems: StemInfo[];
  enabledByStem: Record<string, boolean>;
  onToggle: (stemKey: string, enabled: boolean) => void;
}

export function StemMixerPanel({ stems, enabledByStem, onToggle }: StemMixerPanelProps) {
  if (stems.length === 0) return null;

  return (
    <section className="rounded-xl border border-slate-800 bg-slate-900/50 p-3">
      <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">Stem Mixer</h3>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        {stems.map((stem) => {
          const enabled = enabledByStem[stem.stem_key] ?? true;
          return (
            <label
              key={stem.stem_key}
              className="flex items-center gap-2 rounded border border-slate-700 bg-slate-900 px-2 py-1 text-sm text-slate-200"
            >
              <input
                type="checkbox"
                checked={enabled}
                onChange={(e) => onToggle(stem.stem_key, e.target.checked)}
              />
              <span>{stem.stem_key}</span>
            </label>
          );
        })}
      </div>
    </section>
  );
}
