import { useEffect, useRef } from "react";

interface TabViewerPanelProps {
  tabSourceUrl: string | null;
  currentTime: number;
  onSyncTime?: (currentTime: number) => void;
}

export function TabViewerPanel({ tabSourceUrl, currentTime, onSyncTime }: TabViewerPanelProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const alphaTabRef = useRef<any>(null);

  useEffect(() => {
    onSyncTime?.(currentTime);
    alphaTabRef.current?.player?.seek?.(currentTime * 1000);
  }, [currentTime, onSyncTime]);

  useEffect(() => {
    let disposed = false;
    async function init() {
      if (!tabSourceUrl || !containerRef.current) return;
      try {
        const alphaTabModule: any = await import("@coderline/alphatab");
        if (disposed || !containerRef.current) return;
        const AlphaTabApi = alphaTabModule.AlphaTabApi;
        if (!AlphaTabApi) return;
        alphaTabRef.current = new AlphaTabApi(containerRef.current, {
          file: tabSourceUrl,
        });
      } catch {
        alphaTabRef.current = null;
      }
    }
    void init();

    return () => {
      disposed = true;
      alphaTabRef.current?.destroy?.();
      alphaTabRef.current = null;
    };
  }, [tabSourceUrl]);

  if (!tabSourceUrl) {
    return (
      <section className="rounded-xl border border-slate-800 bg-slate-900/60 px-3 py-2 text-sm text-slate-300">
        Tabs are not available for this song yet.
      </section>
    );
  }

  return (
    <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-3">
      <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-300">Tab Viewer</h2>
      <div ref={containerRef} data-testid="tab-viewer-canvas" className="min-h-24 rounded bg-slate-950/60" />
    </section>
  );
}
