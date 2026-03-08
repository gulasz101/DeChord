import { useEffect, useRef } from "react";
import bravuraWoffUrl from "../assets/alphatab/Bravura.woff?url";
import bravuraWoff2Url from "../assets/alphatab/Bravura.woff2?url";
import bravuraOtfUrl from "../assets/alphatab/Bravura.otf?url";

interface TabViewerPanelProps {
  tabSourceUrl: string | null;
  currentTime: number;
  isPlaying: boolean;
}

function createSettings(tabSourceUrl: string, scrollElement: string | HTMLElement) {
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
  const alphaTabRef = useRef<any>(null);
  const renderReadyRef = useRef(false);
  const currentTimeRef = useRef(currentTime);
  const isPlayingRef = useRef(isPlaying);

  useEffect(() => {
    currentTimeRef.current = currentTime;
    isPlayingRef.current = isPlaying;
  }, [currentTime, isPlaying]);

  useEffect(() => {
    const api = alphaTabRef.current;
    if (!api || !renderReadyRef.current) return;
    try {
      api.timePosition = currentTime * 1000;
      if (isPlaying) api.scrollToCursor?.();
    } catch { /* ignore */ }
  }, [currentTime, isPlaying]);

  useEffect(() => {
    let disposed = false;
    async function init() {
      if (!tabSourceUrl || !containerRef.current) return;
      try {
        const mod: any = await import("@coderline/alphatab");
        if (disposed || !containerRef.current) return;
        const AlphaTabApi = mod.AlphaTabApi;
        if (!AlphaTabApi) return;
        const api = new AlphaTabApi(containerRef.current, createSettings(tabSourceUrl, scrollHostRef.current ?? "html,body"));
        alphaTabRef.current = api;
        api.renderFinished.on(() => {
          if (disposed) return;
          renderReadyRef.current = true;
          api.timePosition = currentTimeRef.current * 1000;
          if (isPlayingRef.current) api.scrollToCursor?.();
        });
      } catch { alphaTabRef.current = null; }
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
      <div className="border px-4 py-3 text-sm" style={{ borderColor: "#e0ddd6", background: "#ffffff", color: "#6b6b6b", borderRadius: "2px" }}>
        Tabs not available for this song yet.
      </div>
    );
  }

  return (
    <div className="border p-3" style={{ borderColor: "#e0ddd6", background: "#ffffff", borderRadius: "2px" }}>
      <h3 className="mb-2 text-xs font-semibold uppercase tracking-[0.15em]" style={{ color: "#6b6b6b" }}>Tab Viewer</h3>
      <div ref={scrollHostRef} className="relative h-64 overflow-x-auto overflow-y-hidden bg-white p-3 text-black" style={{ border: "1px solid #e0ddd6", borderRadius: "2px" }}>
        <div ref={containerRef} className="min-h-24" />
        <div className="pointer-events-none absolute inset-x-0 bottom-0 h-5 bg-white" />
      </div>
    </div>
  );
}
