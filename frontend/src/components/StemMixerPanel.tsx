import type { StemInfo } from "../lib/types";

export type PlaybackMode = "full_mix" | "stems";

interface StemMixerPanelProps {
  playbackMode: PlaybackMode;
  onModeChange: (mode: PlaybackMode) => void;
  stems: StemInfo[];
  enabledByStem: Record<string, boolean>;
  onToggle: (stemKey: string, enabled: boolean) => void;
}

export function StemMixerPanel({
  playbackMode,
  onModeChange,
  stems,
  enabledByStem,
  onToggle,
}: StemMixerPanelProps) {
  if (stems.length === 0) return null;

  return (
    <section className="rounded-xl border border-slate-800 bg-slate-900/50 p-3 sm:w-72">
      <h3 className="mb-3 text-xs font-semibold uppercase tracking-wide text-slate-400">Stem Mixer</h3>
      <div className="mb-3 space-y-2">
        <label className="flex items-center gap-2 rounded border border-slate-700 bg-slate-900 px-2 py-1 text-sm text-slate-200">
          <input
            type="radio"
            name="playback-mode"
            checked={playbackMode === "full_mix"}
            onChange={() => onModeChange("full_mix")}
          />
          <span>Full Mix</span>
        </label>
        <label className="flex items-center gap-2 rounded border border-slate-700 bg-slate-900 px-2 py-1 text-sm text-slate-200">
          <input
            type="radio"
            name="playback-mode"
            checked={playbackMode === "stems"}
            onChange={() => onModeChange("stems")}
          />
          <span>Stems</span>
        </label>
      </div>
      <div className="space-y-2">
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
