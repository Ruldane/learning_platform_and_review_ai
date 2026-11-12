import { describe, expect, it } from "vitest";
import { revealDelays, revealUnits, REVEAL_STEP_MS } from "./reveal";

describe("revealDelays", () => {
  it("spaces elements by 200 ms and clamps to 150-300", () => {
    expect(REVEAL_STEP_MS).toBe(200);
    expect(revealDelays(3, { reducedMotion: false })).toEqual([0, 200, 400]);
    expect(revealDelays(2, { stepMs: 500, reducedMotion: false })).toEqual([0, 300]);
    expect(revealDelays(2, { stepMs: 20, reducedMotion: false })).toEqual([0, 150]);
  });

  it("shows everything at once with reduced motion", () => {
    expect(revealDelays(3, { reducedMotion: true })).toEqual([0, 0, 0]);
  });

  it("returns nothing for an empty scene", () => {
    expect(revealDelays(0, { reducedMotion: false })).toEqual([]);
  });
});

describe("revealUnits", () => {
  it("keeps converter order and shows a bound label with its container", () => {
    const elements = [
      { id: "a", type: "rectangle" },
      { id: "a-label", type: "text", containerId: "a" },
      { id: "b", type: "rectangle" },
      { id: "e", type: "arrow" },
    ];
    expect(revealUnits(elements).map((unit) => unit.map((el) => el.id))).toEqual([
      ["a", "a-label"],
      ["b"],
      ["e"],
    ]);
  });

  it("treats a label whose container is unknown as its own unit", () => {
    const units = revealUnits([{ id: "t", type: "text", containerId: "ghost" }]);
    expect(units).toHaveLength(1);
  });
});
