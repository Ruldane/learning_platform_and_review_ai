import { renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { IDLE_MS, useIdleTeach } from "./useIdleTeach";

type Props = { enabled: boolean; line: number | null; activity: number };

function setup(initial: Props) {
  const onIdle = vi.fn();
  const view = renderHook((props: Props) => useIdleTeach({ ...props, onIdle }), {
    initialProps: initial,
  });
  return { onIdle, ...view };
}

describe("useIdleTeach", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it("idle timer is off by default: nothing fires, however long we wait", () => {
    const { onIdle } = setup({ enabled: false, line: 3, activity: 0 });
    vi.advanceTimersByTime(IDLE_MS * 5);
    expect(onIdle).not.toHaveBeenCalled();
    expect(vi.getTimerCount()).toBe(0);
  });

  it("fires once after 30 s on the same line when enabled", () => {
    const { onIdle } = setup({ enabled: true, line: 3, activity: 0 });
    vi.advanceTimersByTime(IDLE_MS - 1);
    expect(onIdle).not.toHaveBeenCalled();
    vi.advanceTimersByTime(1);
    expect(onIdle).toHaveBeenCalledTimes(1);
    vi.advanceTimersByTime(IDLE_MS * 3);
    expect(onIdle).toHaveBeenCalledTimes(1);
  });

  it("moving to another line or typing starts the 30 s again", () => {
    const { onIdle, rerender } = setup({ enabled: true, line: 3, activity: 0 });
    vi.advanceTimersByTime(IDLE_MS - 1000);
    rerender({ enabled: true, line: 4, activity: 0 });
    vi.advanceTimersByTime(IDLE_MS - 1000);
    rerender({ enabled: true, line: 4, activity: 1 });
    vi.advanceTimersByTime(IDLE_MS - 1000);
    expect(onIdle).not.toHaveBeenCalled();
    vi.advanceTimersByTime(1000);
    expect(onIdle).toHaveBeenCalledTimes(1);
  });

  it("waits for the first cursor move, and stops when the option is cleared", () => {
    const { onIdle, rerender } = setup({ enabled: true, line: null, activity: 0 });
    vi.advanceTimersByTime(IDLE_MS * 2);
    expect(onIdle).not.toHaveBeenCalled();
    rerender({ enabled: true, line: 2, activity: 0 });
    vi.advanceTimersByTime(IDLE_MS - 1);
    rerender({ enabled: false, line: 2, activity: 0 });
    vi.advanceTimersByTime(IDLE_MS);
    expect(onIdle).not.toHaveBeenCalled();
  });
});
