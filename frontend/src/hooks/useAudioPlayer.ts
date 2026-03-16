import { useRef, useState, useCallback, useEffect, useMemo } from "react";

export interface LoopPoints {
  start: number;
  end: number;
}

export interface SourceConfig {
  key: string;
  url: string;
  enabled: boolean;
}

export interface AudioLike {
  currentTime: number;
  duration: number;
  volume: number;
  playbackRate: number;
  play: () => Promise<void> | void;
  pause: () => void;
}

const FADE_DURATION_MS = 75;

function easeOutQuad(t: number): number {
  return 1 - (1 - t) * (1 - t);
}

export function applyVolumeToAudios(
  audios: AudioLike[],
  enabledFlags: boolean[],
  volume: number,
) {
  audios.forEach((audio, idx) => {
    const enabled = enabledFlags[idx] ?? true;
    audio.volume = enabled ? volume : 0;
  });
}

export function setPlaybackRateForAudios(audios: AudioLike[], rate: number) {
  audios.forEach((audio) => {
    audio.playbackRate = rate;
  });
}

export function seekAudios(audios: AudioLike[], time: number, duration: number) {
  const clamped = Math.max(0, Math.min(duration || 0, time));
  audios.forEach((audio) => {
    audio.currentTime = clamped;
  });
  return clamped;
}

export function pauseAudios(audios: AudioLike[]) {
  audios.forEach((audio) => audio.pause());
}

export async function playAudios(audios: AudioLike[]) {
  await Promise.all(audios.map((audio) => Promise.resolve(audio.play())));
}

export function useAudioPlayer(sources: SourceConfig[]) {
  const audioRefs = useRef<Map<string, HTMLAudioElement>>(new Map());
  const rafRef = useRef<number>(0);
  const loopRef = useRef<LoopPoints | null>(null);
  const fadeRafRefs = useRef<Map<string, number>>(new Map());
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [volume, setVolumeState] = useState(1);
  const [playbackRate, setPlaybackRateState] = useState(1);
  const [loop, setLoopState] = useState<LoopPoints | null>(null);
  const [loadErrors, setLoadErrors] = useState<Set<string>>(new Set());

  const sourceConfigSignature = useMemo(
    () => sources.map((s) => `${s.key}:${s.url}`).join("|"),
    [sources],
  );
  const enabledSignature = useMemo(
    () => sources.map((s) => `${s.key}:${s.enabled ? 1 : 0}`).join("|"),
    [sources],
  );

  const setLoop = useCallback((nextLoop: LoopPoints | null) => {
    loopRef.current = nextLoop;
    setLoopState(nextLoop);
  }, []);

  const fadeAudio = useCallback(
    (
      audio: HTMLAudioElement,
      key: string,
      targetEnabled: boolean,
      targetVolume: number,
    ) => {
      const existingRaf = fadeRafRefs.current.get(key);
      if (existingRaf) cancelAnimationFrame(existingRaf);

      const startVol = audio.volume;
      const endVol = targetEnabled ? targetVolume : 0;
      const startTime = performance.now();

      const tick = (now: number) => {
        const elapsed = now - startTime;
        const progress = Math.min(1, elapsed / FADE_DURATION_MS);
        const eased = easeOutQuad(progress);

        audio.volume = startVol + (endVol - startVol) * eased;

        if (progress < 1) {
          fadeRafRefs.current.set(key, requestAnimationFrame(tick));
        } else {
          fadeRafRefs.current.delete(key);
        }
      };

      fadeRafRefs.current.set(key, requestAnimationFrame(tick));
    },
    [],
  );

  useEffect(() => {
    if (sources.length === 0) {
      audioRefs.current.forEach((audio) => {
        audio.pause();
        audio.src = "";
      });
      audioRefs.current.clear();
      return;
    }

    sources.forEach((source) => {
      if (!audioRefs.current.has(source.key)) {
        const audio = new Audio(source.url);

        audio.addEventListener("error", () => {
          setLoadErrors((prev) => new Set([...prev, source.key]));
        });

        audioRefs.current.set(source.key, audio);
      }
    });

    const currentKeys = new Set(sources.map((s) => s.key));
    audioRefs.current.forEach((audio, key) => {
      if (!currentKeys.has(key)) {
        audio.pause();
        audio.src = "";
        audioRefs.current.delete(key);
        setLoadErrors((prev) => {
          const next = new Set(prev);
          next.delete(key);
          return next;
        });
      }
    });

    const primary = audioRefs.current.get(sources[0]?.key);
    if (primary && !primary.dataset.listenersSet) {
      primary.addEventListener("loadedmetadata", () => {
        setDuration(primary.duration || 0);
      });
      primary.addEventListener("ended", () => {
        setPlaying(false);
      });
      primary.dataset.listenersSet = "true";
    }

    queueMicrotask(() => {
      setCurrentTime(0);
    });

    return () => {
      cancelAnimationFrame(rafRef.current);
    };
  }, [sourceConfigSignature]);

  useEffect(() => {
    const prevEnabledRef = useRef<Map<string, boolean>>(new Map());

    sources.forEach((source) => {
      const audio = audioRefs.current.get(source.key);
      if (!audio) return;

      const prevEnabled = prevEnabledRef.current.get(source.key);
      const nowEnabled = source.enabled;

      if (prevEnabled !== undefined && prevEnabled !== nowEnabled) {
        fadeAudio(audio, source.key, nowEnabled, volume);
      } else if (prevEnabled === undefined) {
        audio.volume = nowEnabled ? volume : 0;
      }

      prevEnabledRef.current.set(source.key, nowEnabled);
    });
  }, [enabledSignature, volume, fadeAudio]);

  useEffect(() => {
    const audios = Array.from(audioRefs.current.values());
    setPlaybackRateForAudios(audios, playbackRate);
  }, [playbackRate]);

  useEffect(() => {
    if (!playing) {
      cancelAnimationFrame(rafRef.current);
      return;
    }

    const tick = () => {
      const audios = Array.from(audioRefs.current.values());
      if (audios.length === 0) return;

      const primary = audios[0];
      const nextLoop = loopRef.current;

      if (nextLoop && primary.currentTime >= nextLoop.end) {
        const loopedTime = seekAudios(audios, nextLoop.start, primary.duration || 0);
        setCurrentTime(loopedTime);
      } else {
        setCurrentTime(primary.currentTime);
      }

      rafRef.current = requestAnimationFrame(tick);
    };

    rafRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafRef.current);
  }, [playing, loop]);

  const play = useCallback(() => {
    const audios = Array.from(audioRefs.current.values());
    if (audios.length === 0) return;
    void playAudios(audios);
    setPlaying(true);
  }, []);

  const pause = useCallback(() => {
    const audios = Array.from(audioRefs.current.values());
    if (audios.length === 0) return;
    pauseAudios(audios);
    setPlaying(false);
  }, []);

  const togglePlay = useCallback(() => {
    if (playing) pause();
    else play();
  }, [playing, play, pause]);

  const seek = useCallback((time: number) => {
    const audios = Array.from(audioRefs.current.values());
    if (audios.length === 0) return;
    const primary = audios[0];
    const clamped = seekAudios(audios, time, primary.duration || 0);
    setCurrentTime(clamped);
  }, []);

  const seekRelative = useCallback((delta: number) => {
    const audios = Array.from(audioRefs.current.values());
    if (audios.length === 0) return;
    const primary = audios[0];
    const next = Math.max(0, Math.min(primary.duration || 0, primary.currentTime + delta));
    const clamped = seekAudios(audios, next, primary.duration || 0);
    setCurrentTime(clamped);
  }, []);

  const setVolume = useCallback((v: number) => {
    setVolumeState(v);
  }, []);

  const setPlaybackRate = useCallback((rate: number) => {
    setPlaybackRateState(rate);
  }, []);

  useEffect(() => {
    return () => {
      audioRefs.current.forEach((audio) => {
        audio.pause();
        audio.src = "";
      });
      fadeRafRefs.current.forEach((raf) => cancelAnimationFrame(raf));
    };
  }, []);

  return {
    currentTime,
    duration,
    playing,
    volume,
    playbackRate,
    loop,
    loadErrors,
    play,
    pause,
    togglePlay,
    seek,
    seekRelative,
    setVolume,
    setPlaybackRate,
    setLoop,
  };
}