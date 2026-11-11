import { describe, expect, it } from "vitest";
import { KIND_COLORS, MEMORY_KINDS } from "./kindColors";

function luminance(hex: string): number {
  const [r, g, b] = [1, 3, 5].map((i) => {
    const v = parseInt(hex.slice(i, i + 2), 16) / 255;
    return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
  }) as [number, number, number];
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function contrast(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x) as [number, number];
  return (hi + 0.05) / (lo + 0.05);
}

describe("KIND_COLORS", () => {
  it("every kind has a distinct color", () => {
    expect(new Set(Object.values(KIND_COLORS)).size).toBe(6);
  });

  it("lists the six kinds in a stable order", () => {
    expect(MEMORY_KINDS).toEqual(["document", "acquis", "lecon", "source", "offre", "decision"]);
  });

  it("every color reaches AA contrast on the off-white background", () => {
    for (const color of Object.values(KIND_COLORS)) {
      expect(color).toMatch(/^#[0-9a-f]{6}$/);
      expect(contrast(color, "#fafaf7")).toBeGreaterThanOrEqual(4.5);
    }
  });
});
