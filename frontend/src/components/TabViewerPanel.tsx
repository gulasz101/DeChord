import { useEffect, useRef } from "react";
import { createTabViewerSettings } from "./tabViewer";

interface TabViewerPanelProps {
  tabSourceUrl: string | null;
  currentTime: number;
  isPlaying: boolean;
  onSyncTime?: (currentTime: number) => void;
}

interface AlphaTabApiLike {
  timePosition: number;
  scrollToCursor?: () => void;
  destroy?: () => void;
  renderFinished: { on: (cb: () => void) => void };
}

interface AlphaTabModuleLike {
  AlphaTabApi?: new (container: HTMLElement, settings: ReturnType<typeof createTabViewerSettings>) => AlphaTabApiLike;
}

export function TabViewerPanel({ tabSourceUrl, currentTime, isPlaying, onSyncTime }: TabViewerPanelProps) {
  const scrollHostRef = useRef<HTMLDivElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const alphaTabRef = useRef<AlphaTabApiLike | null>(null);
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
        const alphaTabModule = await import("@coderline/alphatab") as AlphaTabModuleLike;
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
