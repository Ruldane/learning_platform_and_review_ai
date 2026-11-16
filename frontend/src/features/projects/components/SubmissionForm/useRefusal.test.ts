import { act, renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { useRefusal } from "./useRefusal";

const REFUSAL = { repoUrl: "Refusé." };

describe("useRefusal", () => {
  it("hides a refusal once its field is cleared, and a new refusal starts again", () => {
    const { result, rerender } = renderHook(({ refusal }) => useRefusal(refusal), {
      initialProps: { refusal: REFUSAL as { repoUrl?: string } | null },
    });
    expect(result.current.refused("repoUrl")).toBe("Refusé.");
    act(() => result.current.clear("repoUrl"));
    expect(result.current.refused("repoUrl")).toBeUndefined();
    rerender({ refusal: { repoUrl: "Encore refusé." } });
    expect(result.current.refused("repoUrl")).toBe("Encore refusé.");
  });

  it("does not grow or re-render when a field already cleared is cleared again", () => {
    let renders = 0;
    const { result } = renderHook(() => {
      renders += 1;
      return useRefusal(REFUSAL);
    });
    act(() => result.current.clear("repoUrl", "missing"));
    const after = renders;
    for (let i = 0; i < 20; i += 1) act(() => result.current.clear("repoUrl", "missing"));
    // React peut rendre une fois de plus avant de voir que l'état n'a pas changé, jamais à chaque appel.
    expect(renders - after).toBeLessThanOrEqual(1);
  });
});
