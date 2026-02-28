import { useRef, useState, useCallback, useEffect } from "react";

export interface LoopPoints {
  start: number; // seconds
  end: number;   // seconds
}

export function useAudioPlayer(src: string | null) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const rafRef = useRef<number>(0);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [volume, setVolumeState] = useState(1);
  const [loop, setLoop] = useState<LoopPoints | null>(null);

  // Create audio element when src changes
  useEffect(() => {
    if (!src) return;
    const audio = new Audio(src);
    audioRef.current = audio;

    audio.addEventListener("loadedmetadata", () => {
      setDuration(audio.duration);
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

  // Animation frame loop for time tracking
  useEffect(() => {
    if (!playing) {
      cancelAnimationFrame(rafRef.current);
      return;
    }

    const tick = () => {
      const audio = audioRef.current;
      if (!audio) return;
      setCurrentTime(audio.currentTime);

      // Handle loop
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
    audio.play();
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
    audio.currentTime = time;
    setCurrentTime(time);
  }, []);

  const seekRelative = useCallback(
    (delta: number) => {
      const audio = audioRef.current;
      if (!audio) return;
      const newTime = Math.max(0, Math.min(audio.duration, audio.currentTime + delta));
      audio.currentTime = newTime;
      setCurrentTime(newTime);
    },
    [],
  );

  const setVolume = useCallback((v: number) => {
    const audio = audioRef.current;
    if (audio) audio.volume = v;
    setVolumeState(v);
  }, []);

  return {
    currentTime,
    duration,
    playing,
    volume,
    loop,
    play,
    pause,
    togglePlay,
    seek,
    seekRelative,
    setVolume,
    setLoop,
  };
}
