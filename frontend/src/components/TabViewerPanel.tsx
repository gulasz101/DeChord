import { useEffect, useRef } from "react";

interface TabViewerPanelProps {
  tabSourceUrl: string | null;
  currentTime: number;
  isPlaying: boolean;
  onSyncTime?: (currentTime: number) => void;
}

const BAR_WINDOW_SIZE = 4;

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
  const barStartTicksRef = useRef<number[]>([]);
  const totalBarsRef = useRef(0);
  const activeWindowRef = useRef<{ startBar: number; barCount: number } | null>(null);

  const updateVisibleWindow = (api: any, currentBarIndex: number) => {
    const window = getDisplayWindowForBar(currentBarIndex, totalBarsRef.current);
    if (
      activeWindowRef.current &&
      activeWindowRef.current.startBar === window.startBar &&
      activeWindowRef.current.barCount === window.barCount
    ) {
      return;
    }

    api.settings.display.startBar = window.startBar;
    api.settings.display.barCount = window.barCount;
    api.updateSettings?.();
    api.render?.();
    activeWindowRef.current = window;
  };

  useEffect(() => {
    onSyncTime?.(currentTime);
    const api = alphaTabRef.current;
    if (!api || !renderReadyRef.current) return;
    try {
      api.timePosition = currentTime * 1000;
      if (isPlaying) {
        api.scrollToCursor?.();
      }
      const currentTick = typeof api.tickPosition === "number" ? api.tickPosition : 0;
      const currentBarIndex = findCurrentBarIndex(barStartTicksRef.current, currentTick);
      updateVisibleWindow(api, currentBarIndex);
    } catch {
      // Keep the app usable even if alphaTab state sync fails transiently.
    }
  }, [currentTime, isPlaying, onSyncTime]);

  useEffect(() => {
    let disposed = false;
    const unsubs: Array<() => void> = [];
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
            barsPerRow: BAR_WINDOW_SIZE,
            scale: 1.4,
            stretchForce: 0.9,
            startBar: 1,
            barCount: BAR_WINDOW_SIZE,
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
        unsubs.push(
          api.renderFinished.on(() => {
            if (disposed) return;
            renderReadyRef.current = true;
            const scoreMasterBars = api.score?.masterBars ?? [];
            totalBarsRef.current = scoreMasterBars.length;
            barStartTicksRef.current = scoreMasterBars.map((masterBar: any) => masterBar.start ?? 0);
            const currentTick = typeof api.tickPosition === "number" ? api.tickPosition : 0;
            const currentBarIndex = findCurrentBarIndex(barStartTicksRef.current, currentTick);
            updateVisibleWindow(api, currentBarIndex);
            api.timePosition = currentTime * 1000;
            api.scrollToCursor?.();
          }),
        );

        unsubs.push(
          api.playerPositionChanged.on((args: any) => {
            if (disposed || !renderReadyRef.current) return;
            const currentBarIndex = findCurrentBarIndex(barStartTicksRef.current, args.currentTick ?? 0);
            updateVisibleWindow(api, currentBarIndex);
          }),
        );

        unsubs.push(
          api.playedBeatChanged.on((beat: any) => {
            if (disposed || !renderReadyRef.current) return;
            const barIndex = beat?.voice?.bar?.masterBar?.index;
            if (typeof barIndex === "number") {
              updateVisibleWindow(api, barIndex);
            }
          }),
        );
      } catch {
        alphaTabRef.current = null;
      }
    }
    void init();

    return () => {
      disposed = true;
      for (const unsub of unsubs) {
        unsub();
      }
      renderReadyRef.current = false;
      barStartTicksRef.current = [];
      totalBarsRef.current = 0;
      activeWindowRef.current = null;
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
        className="max-h-96 overflow-y-auto rounded bg-white p-3 text-black"
      >
        <div ref={containerRef} data-testid="tab-viewer-canvas" className="min-h-24" />
      </div>
    </section>
  );
}
