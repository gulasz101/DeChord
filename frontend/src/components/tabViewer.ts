import bravuraWoffUrl from "../assets/alphatab/Bravura.woff?url";
import bravuraWoff2Url from "../assets/alphatab/Bravura.woff2?url";
import bravuraOtfUrl from "../assets/alphatab/Bravura.otf?url";

const BAR_WINDOW_SIZE = 4;

export function createTabViewerSettings(tabSourceUrl: string, scrollElement: string | HTMLElement) {
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
