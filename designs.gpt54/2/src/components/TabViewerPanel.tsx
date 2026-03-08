import { useEffect, useRef } from "react";
import bravuraWoffUrl from "../assets/alphatab/Bravura.woff?url";
import bravuraWoff2Url from "../assets/alphatab/Bravura.woff2?url";
import bravuraOtfUrl from "../assets/alphatab/Bravura.otf?url";

interface TabViewerPanelProps {
  tabSourceUrl: string | null;
  currentTime: number;
  isPlaying: boolean;
}

function createTabViewerSettings(tabSourceUrl: string, scrollElement: string | HTMLElement) {
  return {
    file: tabSourceUrl,
    core: {
      smuflFontSources: new Map([
        ["Woff2", bravuraWoff2Url],
        ["Woff", bravuraWoffUrl],
        ["OpenType", bravuraOtfUrl],
      ]),
    },
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
      enableAnimatedBeatCursor: true,
      enableElementHighlighting: true,
      enableUserInteraction: false,
      scrollMode: "Continuous",
      scrollElement,
      nativeBrowserSmoothScroll: true,
    },
  };
}

export function TabViewerPanel({ tabSourceUrl, currentTime, isPlaying }: TabViewerPanelProps) {
  const scrollHostRef = useRef<HTMLDivElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const apiRef = useRef<any>(null);
  const renderReadyRef = useRef(false);
  const currentTimeRef = useRef(currentTime);
  const isPlayingRef = useRef(isPlaying);

  useEffect(() => {
    currentTimeRef.current = currentTime;
    isPlayingRef.current = isPlaying;
    const api = apiRef.current;
    if (!api || !renderReadyRef.current) {
      return;
    }
    try {
      api.timePosition = currentTime * 1000;
      if (isPlaying) {
        api.scrollToCursor?.();
      }
    } catch {
      // Best-effort sync only for mocked preview flow.
    }
  }, [currentTime, isPlaying]);

  useEffect(() => {
    let disposed = false;
    async function init() {
      if (!tabSourceUrl || !containerRef.current) {
        return;
      }
      try {
        const alphaTabModule: any = await import("@coderline/alphatab");
        if (disposed || !containerRef.current) {
          return;
        }
        const AlphaTabApi = alphaTabModule.AlphaTabApi;
        if (!AlphaTabApi) {
          return;
        }
        const api = new AlphaTabApi(
          containerRef.current,
          createTabViewerSettings(tabSourceUrl, scrollHostRef.current ?? "html,body"),
        );
        apiRef.current = api;
        api.renderFinished.on(() => {
          if (disposed) {
            return;
          }
          renderReadyRef.current = true;
          api.timePosition = currentTimeRef.current * 1000;
          if (isPlayingRef.current) {
            api.scrollToCursor?.();
          }
        });
      } catch {
        apiRef.current = null;
      }
    }
    void init();

    return () => {
      disposed = true;
      renderReadyRef.current = false;
      apiRef.current?.destroy?.();
      apiRef.current = null;
    };
  }, [tabSourceUrl]);

  if (!tabSourceUrl) {
    return (
      <section className="rounded-[var(--radius-lg)] border border-[var(--line)] bg-[var(--panel)] px-3 py-3 text-sm text-[var(--text-soft)] shadow-[var(--shadow-soft)]">
        Tabs are not available for this song yet.
      </section>
    );
  }

  return (
    <section className="rounded-[var(--radius-lg)] border border-[var(--line)] bg-[var(--panel)] p-3 shadow-[var(--shadow-soft)]">
      <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-[var(--text-soft)]">Tab Viewer</h2>
      <div
        className="relative h-64 overflow-x-auto overflow-y-hidden rounded-[var(--radius-md)] bg-white p-3 text-black"
        data-testid="tab-viewer-scrollhost"
        ref={scrollHostRef}
      >
        <div className="min-h-24" data-testid="tab-viewer-canvas" ref={containerRef} />
        <div className="pointer-events-none absolute inset-x-0 bottom-0 h-5 bg-white" />
      </div>
    </section>
  );
}
