import { describe, expect, it } from "vitest";
import { readingFraction } from "./readingFraction";

describe("readingFraction", () => {
  it("is 0 before the article reaches the top of the window", () => {
    expect(readingFraction({ top: 200, height: 3000 }, 800)).toBe(0);
  });

  it("is half way once half of the scrollable length has gone by", () => {
    expect(readingFraction({ top: -1100, height: 3000 }, 800)).toBe(0.5);
  });

  it("is 1 when the end of the article is in view", () => {
    expect(readingFraction({ top: -2200, height: 3000 }, 800)).toBe(1);
    expect(readingFraction({ top: -5000, height: 3000 }, 800)).toBe(1);
  });

  it("is 1 for an article that fits in the window", () => {
    expect(readingFraction({ top: 0, height: 500 }, 800)).toBe(1);
  });
});
