import { useEffect, useRef } from "react";

interface TabViewerPanelProps {
  tabSourceUrl: string | null;
  currentTime: number;
  isPlaying: boolean;
  onSyncTime?: (currentTime: number) => void;
}

const BAR_WINDOW_SIZE = 4;

export function createTabViewerSettings(tabSourceUrl: string, scrollElement: string | HTMLElement) {
  return {
    file: tabSourceUrl,
    display: {
      layoutMode: "Horizontal",
      staveProfile: "Tab",
      barsPerRow: -1,
      scale: 1.35,
      stretchForce: 0.9,
      startBar: 1,
      barCount: -1,
    },
    player: {
      playerMode: "EnabledExternalMedia",
      enableCursor: true,
      enableUserInteraction: false,
      scrollMode: "Continuous",
      scrollElement,
      nativeBrowserSmoothScroll: true,
    },
  };
}

export function findCurrentBarIndex(barStartTicks: number[], currentTick: number): number {
  if (barStartTicks.length === 0) return 0;
  let lo = 0;
  let hi = barStartTicks.length - 1;
  let best = 0;

  while (lo <= hi) {
    const mid = Math.floor((lo + hi) / 2);
    if (barStartTicks[mid] <= currentTick) {
      best = mid;
      lo = mid + 1;
    } else {
      hi = mid - 1;
    }
  }

  return best;
}

export function getDisplayWindowForBar(currentBarIndex: number, totalBars: number): { startBar: number; barCount: number } {
  if (totalBars <= 0) {
    return { startBar: 1, barCount: BAR_WINDOW_SIZE };
  }

  const clampedCurrent = Math.min(Math.max(currentBarIndex, 0), totalBars - 1);
  const startBar = clampedCurrent + 1;
  const barCount = Math.min(BAR_WINDOW_SIZE, totalBars - clampedCurrent);
  return { startBar, barCount };
}

export function TabViewerPanel({ tabSourceUrl, currentTime, isPlaying, onSyncTime }: TabViewerPanelProps) {
  const scrollHostRef = useRef<HTMLDivElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const alphaTabRef = useRef<any>(null);
  const renderReadyRef = useRef(false);
  const currentTimeRef = useRef(currentTime);
  const isPlayingRef = useRef(isPlaying);

  useEffect(() => {
    currentTimeRef.current = currentTime;
    isPlayingRef.current = isPlaying;
  }, [currentTime, isPlaying]);

  useEffect(() => {
    onSyncTime?.(currentTime);
    const api = alphaTabRef.current;
    if (!api || !renderReadyRef.current) return;
    try {
      api.timePosition = currentTime * 1000;
      if (isPlaying) {
        api.scrollToCursor?.();
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
        const api = new AlphaTabApi(
          containerRef.current,
          createTabViewerSettings(tabSourceUrl, scrollHostRef.current ?? "html,body"),
        );
        alphaTabRef.current = api;
        api.renderFinished.on(() => {
          if (disposed) return;
          renderReadyRef.current = true;
          api.timePosition = currentTimeRef.current * 1000;
          if (isPlayingRef.current) {
            api.scrollToCursor?.();
          }
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
      <div
        ref={scrollHostRef}
        data-testid="tab-viewer-scrollhost"
        className="relative h-64 overflow-x-auto overflow-y-hidden rounded bg-white p-3 text-black"
      >
        <div ref={containerRef} data-testid="tab-viewer-canvas" className="min-h-24" />
        <div className="pointer-events-none absolute inset-x-0 bottom-0 h-5 bg-white" />
      </div>
    </section>
  );
}
