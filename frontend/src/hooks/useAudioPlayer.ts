import { useRef, useState, useCallback, useEffect } from "react";

export interface LoopPoints {
  start: number;
  end: number;
}

export function useAudioPlayer(src: string | null) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const rafRef = useRef<number>(0);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [volume, setVolumeState] = useState(1);
  const [playbackRate, setPlaybackRateState] = useState(1);
  const [loop, setLoop] = useState<LoopPoints | null>(null);

  useEffect(() => {
    if (!src) return;
    const audio = new Audio(src);
    audio.volume = volume;
    audio.playbackRate = playbackRate;
    audioRef.current = audio;
    setCurrentTime(0);

    audio.addEventListener("loadedmetadata", () => {
      setDuration(audio.duration || 0);
    });
    audio.addEventListener("ended", () => {
      setPlaying(false);
    });

    return () => {
      audio.pause();
      audio.src = "";
      audioRef.current = null;
      cancelAnimationFrame(rafRef.current);
    };
  }, [src]);

  useEffect(() => {
    const audio = audioRef.current;
    if (audio) audio.volume = volume;
  }, [volume]);

  useEffect(() => {
    const audio = audioRef.current;
    if (audio) audio.playbackRate = playbackRate;
  }, [playbackRate]);

  useEffect(() => {
    if (!playing) {
      cancelAnimationFrame(rafRef.current);
      return;
    }

    const tick = () => {
      const audio = audioRef.current;
      if (!audio) return;
      setCurrentTime(audio.currentTime);

      if (loop && audio.currentTime >= loop.end) {
        audio.currentTime = loop.start;
      }

      rafRef.current = requestAnimationFrame(tick);
    };

    rafRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafRef.current);
  }, [playing, loop]);

  const play = useCallback(() => {
    const audio = audioRef.current;
    if (!audio) return;
    void audio.play();
    setPlaying(true);
  }, []);

  const pause = useCallback(() => {
    const audio = audioRef.current;
    if (!audio) return;
    audio.pause();
    setPlaying(false);
  }, []);

  const togglePlay = useCallback(() => {
    if (playing) pause();
    else play();
  }, [playing, play, pause]);

  const seek = useCallback((time: number) => {
    const audio = audioRef.current;
    if (!audio) return;
    const clamped = Math.max(0, Math.min(audio.duration || 0, time));
    audio.currentTime = clamped;
    setCurrentTime(clamped);
  }, []);

  const seekRelative = useCallback((delta: number) => {
    const audio = audioRef.current;
    if (!audio) return;
    const newTime = Math.max(0, Math.min(audio.duration || 0, audio.currentTime + delta));
    audio.currentTime = newTime;
    setCurrentTime(newTime);
  }, []);

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
