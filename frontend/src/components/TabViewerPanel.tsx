import { useEffect, useRef } from "react";

interface TabViewerPanelProps {
  tabSourceUrl: string | null;
  currentTime: number;
  isPlaying: boolean;
  onSyncTime?: (currentTime: number) => void;
}

export function TabViewerPanel({ tabSourceUrl, currentTime, isPlaying, onSyncTime }: TabViewerPanelProps) {
  const scrollHostRef = useRef<HTMLDivElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const alphaTabRef = useRef<any>(null);
  const renderReadyRef = useRef(false);

  useEffect(() => {
    onSyncTime?.(currentTime);
    const api = alphaTabRef.current;
    if (!api || !renderReadyRef.current) return;
    try {
      api.timePosition = currentTime * 1000;
      api.scrollToCursor?.();
      if (isPlaying) {
        api.play?.();
      } else {
        api.pause?.();
      }
    } catch {
      // Keep the app usable even if alphaTab state sync fails transiently.
    }
  }, [currentTime, isPlaying, onSyncTime]);

  useEffect(() => {
    let disposed = false;
    async function init() {
      if (!tabSourceUrl || !containerRef.current) return;
      try {
        const alphaTabModule: any = await import("@coderline/alphatab");
        if (disposed || !containerRef.current) return;
        const AlphaTabApi = alphaTabModule.AlphaTabApi;
        if (!AlphaTabApi) return;
        const api = new AlphaTabApi(containerRef.current, {
          file: tabSourceUrl,
          display: {
            layoutMode: "Page",
            barsPerRow: 2,
            scale: 1.4,
            stretchForce: 0.9,
          },
          player: {
            playerMode: "EnabledExternalMedia",
            enableCursor: true,
            enableUserInteraction: false,
            scrollMode: "Continuous",
            scrollElement: scrollHostRef.current ?? "html,body",
            nativeBrowserSmoothScroll: true,
          },
        });
        alphaTabRef.current = api;
        api.renderFinished.on(() => {
          if (disposed) return;
          renderReadyRef.current = true;
          api.timePosition = currentTime * 1000;
          api.scrollToCursor?.();
        });
      } catch {
        alphaTabRef.current = null;
      }
    }
    void init();

    return () => {
      disposed = true;
      renderReadyRef.current = false;
      alphaTabRef.current?.destroy?.();
      alphaTabRef.current = null;
    };
  }, [tabSourceUrl, currentTime]);

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
      <div
        ref={scrollHostRef}
        data-testid="tab-viewer-scrollhost"
        className="max-h-96 overflow-y-auto rounded bg-white p-3 text-black"
      >
        <div ref={containerRef} data-testid="tab-viewer-canvas" className="min-h-24" />
      </div>
    </section>
  );
}
