import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useReducedMotion } from "./useReducedMotion";

type Listener = () => void;

function stubMatchMedia(initial: boolean) {
  let matches = initial;
  const listeners = new Set<Listener>();
  vi.stubGlobal("matchMedia", (query: string) => ({
    get matches() {
      return matches && query === "(prefers-reduced-motion: reduce)";
    },
    addEventListener: (_type: string, listener: Listener) => listeners.add(listener),
    removeEventListener: (_type: string, listener: Listener) => listeners.delete(listener),
  }));
  return (value: boolean) => {
    matches = value;
    listeners.forEach((listener) => listener());
  };
}

afterEach(() => vi.unstubAllGlobals());

describe("useReducedMotion", () => {
  it("is false without matchMedia", () => {
    vi.stubGlobal("matchMedia", undefined);
    expect(renderHook(() => useReducedMotion()).result.current).toBe(false);
  });

  it("follows prefers-reduced-motion", () => {
    const set = stubMatchMedia(true);
    const { result } = renderHook(() => useReducedMotion());
    expect(result.current).toBe(true);
    act(() => set(false));
    expect(result.current).toBe(false);
  });
});
