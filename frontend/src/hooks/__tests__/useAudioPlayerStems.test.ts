import { describe, expect, it, vi } from "vitest";
import {
  applyVolumeToAudios,
  pauseAudios,
  playAudios,
  seekAudios,
  setPlaybackRateForAudios,
  type AudioLike,
} from "../useAudioPlayer";

function mkAudio(duration = 120): AudioLike {
  return {
    currentTime: 0,
    duration,
    volume: 1,
    playbackRate: 1,
    play: vi.fn().mockResolvedValue(undefined),
    pause: vi.fn(),
  };
}

describe("useAudioPlayer stem sync helpers", () => {
  it("syncs volume based on stem enabled flags", () => {
    const a1 = mkAudio();
    const a2 = mkAudio();

    applyVolumeToAudios([a1, a2], [true, false], 0.6);

    expect(a1.volume).toBe(0.6);
    expect(a2.volume).toBe(0);
  });

  it("syncs playback rate across all audios", () => {
    const a1 = mkAudio();
    const a2 = mkAudio();

    setPlaybackRateForAudios([a1, a2], 0.8);

    expect(a1.playbackRate).toBe(0.8);
    expect(a2.playbackRate).toBe(0.8);
  });

  it("syncs seek across all audios with clamping", () => {
    const a1 = mkAudio(100);
    const a2 = mkAudio(100);

    const clamped = seekAudios([a1, a2], 140, 100);

    expect(clamped).toBe(100);
    expect(a1.currentTime).toBe(100);
    expect(a2.currentTime).toBe(100);
  });

  it("syncs play and pause across all audios", async () => {
    const a1 = mkAudio();
    const a2 = mkAudio();

    await playAudios([a1, a2]);
    pauseAudios([a1, a2]);

    expect(a1.play).toHaveBeenCalledTimes(1);
    expect(a2.play).toHaveBeenCalledTimes(1);
    expect(a1.pause).toHaveBeenCalledTimes(1);
    expect(a2.pause).toHaveBeenCalledTimes(1);
  });
});
