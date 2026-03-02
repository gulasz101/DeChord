import { useRef, useState, useCallback, useEffect } from "react";

export interface LoopPoints {
  start: number;
  end: number;
}

export interface StemSource {
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

export function useAudioPlayer(src: string | null, stemSources: StemSource[] = []) {
  const audioRefs = useRef<HTMLAudioElement[]>([]);
  const rafRef = useRef<number>(0);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [volume, setVolumeState] = useState(1);
  const [playbackRate, setPlaybackRateState] = useState(1);
  const [loop, setLoop] = useState<LoopPoints | null>(null);

  const sources = stemSources.length > 0
    ? stemSources.map((s) => ({ url: s.url, enabled: s.enabled }))
    : src
      ? [{ url: src, enabled: true }]
      : [];

  useEffect(() => {
    if (sources.length === 0) return;
    const audios = sources.map((source) => {
      const audio = new Audio(source.url);
      audio.playbackRate = playbackRate;
      return audio;
    });
    applyVolumeToAudios(audios, sources.map((s) => s.enabled), volume);
    audioRefs.current = audios;
    setCurrentTime(0);

    const primary = audios.find((_a, idx) => sources[idx].enabled) ?? audios[0];
    primary.addEventListener("loadedmetadata", () => {
      setDuration(primary.duration || 0);
    });
    primary.addEventListener("ended", () => {
      setPlaying(false);
    });

    return () => {
      audios.forEach((audio) => {
        audio.pause();
        audio.src = "";
      });
      audioRefs.current = [];
      cancelAnimationFrame(rafRef.current);
    };
  }, [sources.map((s) => `${s.url}:${s.enabled ? 1 : 0}`).join("|")]);

  useEffect(() => {
    applyVolumeToAudios(
      audioRefs.current,
      sources.map((s) => s.enabled),
      volume,
    );
  }, [volume, sources.map((s) => (s.enabled ? "1" : "0")).join("")]);

  useEffect(() => {
    setPlaybackRateForAudios(audioRefs.current, playbackRate);
  }, [playbackRate]);

  useEffect(() => {
    if (!playing) {
      cancelAnimationFrame(rafRef.current);
      return;
    }

    const tick = () => {
      const audios = audioRefs.current;
      if (audios.length === 0) return;
      const primary = audios.find((_a, idx) => sources[idx]?.enabled) ?? audios[0];
      setCurrentTime(primary.currentTime);

      if (loop && primary.currentTime >= loop.end) {
        seekAudios(audios, loop.start, primary.duration || 0);
      }

      rafRef.current = requestAnimationFrame(tick);
    };

    rafRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafRef.current);
  }, [playing, loop, sources.map((s) => (s.enabled ? "1" : "0")).join("")]);

  const play = useCallback(() => {
    const audios = audioRefs.current;
    if (audios.length === 0) return;
    void playAudios(audios);
    setPlaying(true);
  }, []);

  const pause = useCallback(() => {
    const audios = audioRefs.current;
    if (audios.length === 0) return;
    pauseAudios(audios);
    setPlaying(false);
  }, []);

  const togglePlay = useCallback(() => {
    if (playing) pause();
    else play();
  }, [playing, play, pause]);

  const seek = useCallback((time: number) => {
    const audios = audioRefs.current;
    if (audios.length === 0) return;
    const primary = audios.find((_a, idx) => sources[idx]?.enabled) ?? audios[0];
    const clamped = seekAudios(audios, time, primary.duration || 0);
    setCurrentTime(clamped);
  }, [sources.map((s) => (s.enabled ? "1" : "0")).join("")]);

  const seekRelative = useCallback((delta: number) => {
    const audios = audioRefs.current;
    if (audios.length === 0) return;
    const primary = audios.find((_a, idx) => sources[idx]?.enabled) ?? audios[0];
    const next = Math.max(0, Math.min(primary.duration || 0, primary.currentTime + delta));
    const clamped = seekAudios(audios, next, primary.duration || 0);
    setCurrentTime(clamped);
  }, [sources.map((s) => (s.enabled ? "1" : "0")).join("")]);

  const setVolume = useCallback((v: number) => {
    setVolumeState(v);
  }, []);

  const setPlaybackRate = useCallback((rate: number) => {
    setPlaybackRateState(rate);
  }, []);

  return {
    currentTime,
    duration,
    playing,
    volume,
    playbackRate,
    loop,
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
