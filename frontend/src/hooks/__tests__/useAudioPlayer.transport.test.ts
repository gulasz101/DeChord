import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useAudioPlayer } from "../useAudioPlayer";

type AudioEvent = "loadedmetadata" | "ended";

class FakeAudio {
  static instances: FakeAudio[] = [];

  currentTime = 0;
  duration = 120;
  volume = 1;
  playbackRate = 1;
  src: string;
  play = vi.fn().mockResolvedValue(undefined);
  pause = vi.fn();

  private listeners = new Map<AudioEvent, Array<() => void>>();

  constructor(src: string) {
    this.src = src;
    FakeAudio.instances.push(this);
  }

  addEventListener(event: AudioEvent, listener: () => void) {
    const listeners = this.listeners.get(event) ?? [];
    listeners.push(listener);
    this.listeners.set(event, listeners);
  }

  dispatch(event: AudioEvent) {
    for (const listener of this.listeners.get(event) ?? []) {
      listener();
    }
  }
}

describe("useAudioPlayer transport contract", () => {
  let originalAudio: typeof Audio;

  beforeEach(() => {
    FakeAudio.instances = [];
    originalAudio = globalThis.Audio;

    globalThis.Audio = FakeAudio as unknown as typeof Audio;
  });

  afterEach(() => {
    globalThis.Audio = originalAudio;
  });

  it("exposes one public transport contract for play, seek, rate, volume, loop, and ended cleanup", async () => {
    const hook = renderHook(() => useAudioPlayer("/api/audio/30"));

    await act(async () => {
      await Promise.resolve();
    });

    expect(FakeAudio.instances).toHaveLength(1);

    const primaryAudio = FakeAudio.instances[0];

    await waitFor(() => {
      expect(hook.result.current.currentTime).toBe(0);
    });

    act(() => {
      primaryAudio.dispatch("loadedmetadata");
    });

    act(() => {
      hook.result.current.seek(12);
    });

    expect(primaryAudio.currentTime).toBe(12);
    expect(hook.result.current.currentTime).toBe(12);

    act(() => {
      hook.result.current.seekRelative(-2);
      hook.result.current.setPlaybackRate(0.8);
      hook.result.current.setVolume(0.6);
      hook.result.current.setLoop({ start: 4, end: 8 });
      hook.result.current.togglePlay();
    });

    await waitFor(() => {
      expect(primaryAudio.currentTime).toBe(10);
      expect(primaryAudio.playbackRate).toBe(0.8);
      expect(primaryAudio.volume).toBe(0.6);
      expect(primaryAudio.play).toHaveBeenCalledTimes(1);
      expect(hook.result.current.currentTime).toBe(10);
      expect(hook.result.current.playing).toBe(true);
      expect(hook.result.current.playbackRate).toBe(0.8);
      expect(hook.result.current.volume).toBe(0.6);
      expect(hook.result.current.loop).toEqual({ start: 4, end: 8 });
    });

    act(() => {
      hook.result.current.togglePlay();
    });

    expect(primaryAudio.pause).toHaveBeenCalledTimes(1);
    expect(hook.result.current.playing).toBe(false);

    act(() => {
      hook.result.current.togglePlay();
    });

    expect(primaryAudio.play).toHaveBeenCalledTimes(2);

    act(() => {
      primaryAudio.dispatch("ended");
    });

    await waitFor(() => {
      expect(hook.result.current.playing).toBe(false);
    });

    hook.unmount();
  });
});
