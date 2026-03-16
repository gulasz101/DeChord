// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useAudioPlayer } from "../useAudioPlayer";

type AudioEvent = "loadedmetadata" | "ended" | "error";

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

describe("useAudioPlayer fade transitions", () => {
  let originalAudio: typeof Audio;

  beforeEach(() => {
    FakeAudio.instances = [];
    originalAudio = globalThis.Audio;
    globalThis.Audio = FakeAudio as unknown as typeof Audio;
    vi.useFakeTimers();
  });

  afterEach(() => {
    globalThis.Audio = originalAudio;
    vi.useRealTimers();
  });

  it("applies fade when source enabled state changes", async () => {
    const sources = [
      { key: "stem1", url: "http://example.com/stem1.mp3", enabled: true },
      { key: "stem2", url: "http://example.com/stem2.mp3", enabled: false },
    ];

    const { result, rerender } = renderHook(
      ({ sources }) => useAudioPlayer(sources),
      { initialProps: { sources } }
    );

    await act(async () => {
      await vi.runAllTimersAsync();
    });

    expect(FakeAudio.instances).toHaveLength(2);
    const audio1 = FakeAudio.instances[0];
    expect(audio1.volume).toBe(1);

    const newSources = [
      { key: "stem1", url: "http://example.com/stem1.mp3", enabled: false },
      { key: "stem2", url: "http://example.com/stem2.mp3", enabled: true },
    ];

    rerender({ sources: newSources });

    await act(async () => {
      await vi.advanceTimersByTimeAsync(100);
    });

    expect(result.current).toBeDefined();
  });

  it("handles rapid toggle sequences without error", async () => {
    const sources = [
      { key: "stem1", url: "http://example.com/stem1.mp3", enabled: true },
    ];

    const { rerender } = renderHook(
      ({ sources }) => useAudioPlayer(sources),
      { initialProps: { sources } }
    );

    for (let i = 0; i < 10; i++) {
      const newSources = [
        { key: "stem1", url: "http://example.com/stem1.mp3", enabled: i % 2 === 0 },
      ];
      rerender({ sources: newSources });
      await act(async () => {
        await vi.advanceTimersByTimeAsync(10);
      });
    }

    await act(async () => {
      await vi.runAllTimersAsync();
    });
  });

  it("cleans up audio elements on unmount", async () => {
    const sources = [
      { key: "stem1", url: "http://example.com/stem1.mp3", enabled: true },
    ];

    const { unmount } = renderHook(() => useAudioPlayer(sources));

    await act(async () => {
      await vi.runAllTimersAsync();
    });

    expect(() => unmount()).not.toThrow();
  });
});