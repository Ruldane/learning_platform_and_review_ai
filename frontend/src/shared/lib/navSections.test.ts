import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { NAV_SECTIONS } from "./navSections";

// Les tests tournent depuis `frontend/` (voir `vitest.config`).
const css = readFileSync(resolve(process.cwd(), "src/index.css"), "utf8");

describe("NAV_SECTIONS", () => {
  it("donne à chaque section un jeton de couleur distinct, déclaré dans le thème", () => {
    const colors = NAV_SECTIONS.map((section) => section.color);
    expect(new Set(colors).size).toBe(NAV_SECTIONS.length);
    for (const color of colors) {
      const token = /^var\((--section-[a-z]+)\)$/.exec(color)?.[1];
      expect(token, color).toBeDefined();
      expect(css).toContain(`${token}: #`);
    }
  });
});
