import { describe, expect, it } from "vitest";
import { LEVEL_COLORS, LEVEL_KEYS } from "./levels";

function luminance(hex: string): number {
  const [r, g, b] = [1, 3, 5].map((start) => {
    const channel = parseInt(hex.slice(start, start + 2), 16) / 255;
    return channel <= 0.03928 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r! + 0.7152 * g! + 0.0722 * b!;
}

/** Rapport de contraste WCAG entre deux couleurs `#rrggbb`. */
function contrastRatio(a: string, b: string): number {
  const [light, dark] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (light! + 0.05) / (dark! + 0.05);
}

const WHITE = "#ffffff";
const BACKGROUND = "#fafaf7";

describe("LEVEL_COLORS", () => {
  it("has a color for each level and for absent skills", () => {
    expect(Object.keys(LEVEL_COLORS).sort()).toEqual(
      ["absent", "declare", "en_cours", "prouve", "valide"].sort(),
    );
  });

  it("keeps white text at AA contrast on every level color", () => {
    for (const key of LEVEL_KEYS) {
      expect(contrastRatio(LEVEL_COLORS[key], WHITE), key).toBeGreaterThanOrEqual(4.5);
    }
  });

  it("keeps every level color at AA contrast on the page background", () => {
    for (const key of LEVEL_KEYS) {
      expect(contrastRatio(LEVEL_COLORS[key], BACKGROUND), key).toBeGreaterThanOrEqual(4.5);
    }
  });

  it("gives each level its own color", () => {
    expect(new Set(Object.values(LEVEL_COLORS)).size).toBe(LEVEL_KEYS.length);
  });
});

describe("contrastRatio", () => {
  it("is 21 between black and white and 1 for the same color", () => {
    expect(contrastRatio("#000000", "#ffffff")).toBeCloseTo(21, 5);
    expect(contrastRatio("#336699", "#336699")).toBeCloseTo(1, 5);
  });
});
