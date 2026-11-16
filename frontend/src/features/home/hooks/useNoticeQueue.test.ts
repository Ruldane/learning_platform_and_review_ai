import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useNoticeQueue } from "./useNoticeQueue";

const notice = (id: string) => ({ id, title: `Titre ${id}`, detail: null });
const ids = (notices: { id: string }[]) => notices.map((n) => n.id);

describe("useNoticeQueue", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it("closes a notice by itself after its delay", () => {
    const { result } = renderHook(() => useNoticeQueue(8000));
    act(() => result.current.push([notice("a")]));
    act(() => void vi.advanceTimersByTime(7999));
    expect(ids(result.current.notices)).toEqual(["a"]);
    act(() => void vi.advanceTimersByTime(1));
    expect(result.current.notices).toEqual([]);
  });

  it("starts the delay of a waiting notice only when it becomes one of the three visible", () => {
    const { result } = renderHook(() => useNoticeQueue(8000));
    act(() => result.current.push(["a", "b", "c", "d", "e"].map(notice)));
    act(() => void vi.advanceTimersByTime(5000));
    act(() => result.current.dismiss("a"));
    // « d » devient visible à 5 s : il vit 8 s de plus, pas 3.
    act(() => void vi.advanceTimersByTime(3000));
    expect(ids(result.current.notices)).toEqual(["d", "e"]);
    act(() => void vi.advanceTimersByTime(4999));
    expect(ids(result.current.notices)).toEqual(["d", "e"]);
    act(() => void vi.advanceTimersByTime(1));
    expect(ids(result.current.notices)).toEqual(["e"]);
    act(() => void vi.advanceTimersByTime(8000));
    expect(result.current.notices).toEqual([]);
  });

  it("clears its timers on unmount", () => {
    const { result, unmount } = renderHook(() => useNoticeQueue(8000));
    act(() => result.current.push([notice("a")]));
    unmount();
    expect(vi.getTimerCount()).toBe(0);
  });
});
