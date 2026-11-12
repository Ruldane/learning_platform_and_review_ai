import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { QUIET_MS, useSettled } from "./useSettled";

function stubFonts(ready: Promise<unknown>) {
  Object.defineProperty(document, "fonts", { value: { ready }, configurable: true });
}

describe("useSettled", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    stubFonts(Promise.resolve());
  });
  afterEach(() => {
    vi.useRealTimers();
    Reflect.deleteProperty(document, "fonts");
  });

  it("stays read-only while fonts load", async () => {
    let fontsLoaded: () => void = () => {};
    stubFonts(new Promise<void>((resolve) => (fontsLoaded = resolve)));
    const { result } = renderHook(() => useSettled(true, 0));
    await act(() => vi.advanceTimersByTimeAsync(300));
    expect(result.current).toBe(false);
    await act(() => vi.advanceTimersByTimeAsync(700));
    await act(async () => fontsLoaded());
    await act(() => vi.advanceTimersByTimeAsync(QUIET_MS - 1));
    expect(result.current).toBe(false);
    await act(() => vi.advanceTimersByTimeAsync(1));
    expect(result.current).toBe(true);
  });

  it("waits for the scene to be fully shown", async () => {
    const { result, rerender } = renderHook(({ done }) => useSettled(done, 0), {
      initialProps: { done: false },
    });
    await act(() => vi.advanceTimersByTimeAsync(1000));
    expect(result.current).toBe(false);
    rerender({ done: true });
    await act(() => vi.advanceTimersByTimeAsync(QUIET_MS));
    expect(result.current).toBe(true);
  });

  it("restarts the quiet window on each change", async () => {
    const { result, rerender } = renderHook(({ tick }) => useSettled(true, tick), {
      initialProps: { tick: 0 },
    });
    await act(async () => {}); // laisse `document.fonts.ready` se résoudre
    await act(() => vi.advanceTimersByTimeAsync(200));
    rerender({ tick: 1 });
    await act(() => vi.advanceTimersByTimeAsync(QUIET_MS - 1));
    expect(result.current).toBe(false);
    await act(() => vi.advanceTimersByTimeAsync(1));
    expect(result.current).toBe(true);
  });

  it("stays editable once settled, whatever comes next", async () => {
    const { result, rerender } = renderHook(({ tick }) => useSettled(true, tick), {
      initialProps: { tick: 0 },
    });
    await act(async () => {}); // laisse `document.fonts.ready` se résoudre
    await act(() => vi.advanceTimersByTimeAsync(QUIET_MS));
    expect(result.current).toBe(true);
    rerender({ tick: 1 });
    expect(result.current).toBe(true);
  });

  it("does not wait for fonts where the browser has no font loading API", async () => {
    Reflect.deleteProperty(document, "fonts");
    const { result } = renderHook(() => useSettled(true, 0));
    await act(() => vi.advanceTimersByTimeAsync(QUIET_MS));
    expect(result.current).toBe(true);
  });
});
