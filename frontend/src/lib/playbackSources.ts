import { getAudioUrl, getStemAudioUrl } from "./api";
import type { StemInfo } from "./types";

interface ResolvePlaybackSourcesArgs {
  songId: number | null;
  playbackMode: "full_mix" | "stems";
  stems: StemInfo[];
  enabledByStem: Record<string, boolean>;
}

export function resolvePlaybackSources({
  songId,
  playbackMode,
  stems,
  enabledByStem,
}: ResolvePlaybackSourcesArgs) {
  if (!songId) {
    return {
      audioSrc: null as string | null,
      stemSources: [] as Array<{ key: string; url: string; enabled: boolean }>,
      usingStems: false,
    };
  }

  const audioSrc = getAudioUrl(songId);
  if (playbackMode !== "stems") {
    return {
      audioSrc,
      stemSources: [] as Array<{ key: string; url: string; enabled: boolean }>,
      usingStems: false,
    };
  }

  const stemSources = stems
    .filter((stem) => enabledByStem[stem.stem_key] ?? true)
    .map((stem) => ({
      key: stem.stem_key,
      url: getStemAudioUrl(songId, stem.stem_key),
      enabled: true,
    }));

  return {
    audioSrc,
    stemSources,
    usingStems: stemSources.length > 0,
  };
}
