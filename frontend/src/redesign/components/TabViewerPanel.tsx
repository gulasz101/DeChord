import { useEffect, useRef } from "react";
import bravuraWoffUrl from "../assets/alphatab/Bravura.woff?url";
import bravuraWoff2Url from "../assets/alphatab/Bravura.woff2?url";
import bravuraOtfUrl from "../assets/alphatab/Bravura.otf?url";

interface TabViewerPanelProps {
  tabSourceUrl: string | null;
  currentTime: number;
  isPlaying: boolean;
}

interface AlphaTabApiLike {
  timePosition: number;
  scrollToCursor?: () => void;
  destroy?: () => void;
  renderFinished: { on: (cb: () => void) => void };
}

interface AlphaTabModuleLike {
  AlphaTabApi?: new (container: HTMLElement, settings: ReturnType<typeof createSettings>) => AlphaTabApiLike;
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
  const alphaTabRef = useRef<AlphaTabApiLike | null>(null);
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
        const mod = await import("@coderline/alphatab") as AlphaTabModuleLike;
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
      <div className="border px-4 py-3 text-sm" style={{ borderRadius: "4px", borderColor: "rgba(192, 192, 192, 0.06)", background: "rgba(17, 22, 56, 0.5)", color: "#7a7a90" }}>
        Tabs not available for this song yet.
      </div>
    );
  }

  return (
    <div className="border p-3" style={{ borderRadius: "4px", borderColor: "rgba(192, 192, 192, 0.06)", background: "rgba(17, 22, 56, 0.7)", backdropFilter: "blur(12px)" }}>
      <h3 className="mb-2 text-xs font-medium" style={{ fontFamily: "Playfair Display, serif", color: "#7a7a90" }}>Tab Viewer</h3>
      <div ref={scrollHostRef} className="relative h-64 overflow-x-auto overflow-y-hidden rounded-lg bg-white p-3 text-black">
        <div ref={containerRef} className="min-h-24" />
        <div className="pointer-events-none absolute inset-x-0 bottom-0 h-5 bg-white" />
      </div>
    </div>
  );
}
