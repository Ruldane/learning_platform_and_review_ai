import { renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { REFIT_DELAY_MS, useRefitOnShow } from "./useRefitOnShow";

type Callback = (entries: { contentRect: { width: number; height: number } }[]) => void;

describe("useRefitOnShow", () => {
  let callback: Callback = () => undefined;
  const disconnect = vi.fn();

  beforeEach(() => {
    vi.useFakeTimers();
    vi.stubGlobal(
      "ResizeObserver",
      class {
        constructor(cb: Callback) {
          callback = cb;
        }
        observe() {}
        disconnect = disconnect;
      },
    );
  });
  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });
  const settle = () => vi.advanceTimersByTime(REFIT_DELAY_MS);

  const size = (width: number, height: number) => callback([{ contentRect: { width, height } }]);

  function setup() {
    const refit = vi.fn();
    const frame = { current: document.createElement("div") };
    const view = renderHook(() => useRefitOnShow(frame, refit));
    return { refit, view };
  }

  it("refits when the area comes back from a zero size", () => {
    const { refit } = setup();
    size(500, 500);
    expect(refit).not.toHaveBeenCalled();
    size(0, 0);
    size(520, 540);
    expect(refit).not.toHaveBeenCalled();
    settle();
    expect(refit).toHaveBeenCalledTimes(1);
  });

  it("keeps the view the user chose on a plain resize", () => {
    const { refit } = setup();
    size(500, 500);
    size(600, 500);
    size(400, 450);
    settle();
    expect(refit).not.toHaveBeenCalled();
  });

  it("does not refit twice for one return", () => {
    const { refit } = setup();
    size(0, 500);
    size(300, 500);
    size(310, 500);
    settle();
    expect(refit).toHaveBeenCalledTimes(1);
  });

  it("stops observing, and drops a pending refit, when unmounted", () => {
    const { view, refit } = setup();
    size(0, 0);
    size(300, 300);
    view.unmount();
    settle();
    expect(disconnect).toHaveBeenCalled();
    expect(refit).not.toHaveBeenCalled();
  });

  it("does nothing without ResizeObserver", () => {
    vi.unstubAllGlobals();
    vi.stubGlobal("ResizeObserver", undefined);
    expect(() => setup()).not.toThrow();
  });
});
