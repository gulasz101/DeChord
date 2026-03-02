import { getAudioUrl, getStemAudioUrl } from "./api";
import type { StemInfo } from "./types";

interface ResolvePlaybackSourcesArgs {
  songId: number | null;
  stems: StemInfo[];
  enabledByStem: Record<string, boolean>;
}

export function resolvePlaybackSources({
  songId,
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
  const stemSources = stems.map((stem) => ({
    key: stem.stem_key,
    url: getStemAudioUrl(songId, stem.stem_key),
    enabled: enabledByStem[stem.stem_key] ?? true,
  }));

  return {
    audioSrc,
    stemSources,
    usingStems: stemSources.length > 0,
  };
}
