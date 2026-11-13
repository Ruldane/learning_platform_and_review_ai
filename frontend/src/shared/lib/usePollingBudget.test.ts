import { act, renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { usePollingBudget } from "./usePollingBudget";

describe("usePollingBudget", () => {
  it("runs out after the allowed number of reads and starts again on request", () => {
    const { result } = renderHook(() => usePollingBudget(3));
    expect(result.current.exhausted).toBe(false);
    act(() => {
      result.current.spend();
      result.current.spend();
    });
    expect(result.current.used).toBe(2);
    expect(result.current.exhausted).toBe(false);
    act(() => result.current.spend());
    expect(result.current.exhausted).toBe(true);
    act(() => result.current.restart());
    expect(result.current.used).toBe(0);
    expect(result.current.exhausted).toBe(false);
  });
});
