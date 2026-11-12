import { describe, expect, it } from "vitest";
import { extractHeadings, slugify } from "./toc";

describe("toc", () => {
  it("slugifies accents, spaces and symbols", () => {
    expect(slugify("L'essentiel en 5 lignes")).toBe("l-essentiel-en-5-lignes");
    expect(slugify("Erreurs fréquentes !")).toBe("erreurs-frequentes");
    expect(slugify("???")).toBe("section");
  });

  it("keeps h2 and h3, with their line, and suffixes duplicates", () => {
    const headings = extractHeadings("# Titre\n\n## A\n\ntexte\n\n### B\n\n#### C\n\n## A\n");
    expect(headings.map((h) => [h.text, h.level, h.line, h.id])).toEqual([
      ["A", 2, 3, "a"],
      ["B", 3, 7, "b"],
      ["A", 2, 11, "a-2"],
    ]);
  });

  it("ignores headings inside fenced code and strips inline marks", () => {
    const headings = extractHeadings("```md\n## Faux\n```\n\n## Vrai **titre** `code` ##\n");
    expect(headings.map((h) => h.text)).toEqual(["Vrai titre code"]);
  });
});
