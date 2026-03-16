import { getAudioUrl, getStemAudioUrl } from "./api";

export interface SourceConfig {
  key: string;
  url: string;
  enabled: boolean;
}

interface ResolvePlaybackSourcesArgs {
  songId: number | null;
  stems: Array<{
    stemKey: string;
    relativePath: string;
    mimeType: string | null;
    duration: number | null;
  }>;
  enabledBySourceKey: Record<string, boolean>;
}

export function resolvePlaybackSources({
  songId,
  stems,
  enabledBySourceKey,
}: ResolvePlaybackSourcesArgs) {
  if (!songId) {
    return { sources: [] as SourceConfig[] };
  }

  const sources: SourceConfig[] = [
    {
      key: "__full_mix__",
      url: getAudioUrl(songId),
      enabled: enabledBySourceKey["__full_mix__"] ?? true,
    },
    ...stems.map((stem) => ({
      key: stem.stemKey,
      url: getStemAudioUrl(songId, stem.stemKey),
      enabled: enabledBySourceKey[stem.stemKey] ?? false,
    })),
  ];

  return { sources };
}