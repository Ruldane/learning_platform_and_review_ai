import { expect } from "vitest";

/** Les niveaux des titres de la page, dans l'ordre du document. */
export const headingLevels = (root: ParentNode = document): number[] =>
  Array.from(root.querySelectorAll("h1, h2, h3, h4, h5, h6")).map((node) =>
    Number(node.tagName.slice(1)),
  );

/**
 * Le plan de la page est cohérent : un seul `h1`, en premier, puis jamais de saut de niveau vers le
 * bas (un `h3` ne suit pas un `h1`).
 */
export function expectCoherentOutline(root: ParentNode = document): void {
  const levels = headingLevels(root);
  expect(levels.filter((level) => level === 1)).toHaveLength(1);
  expect(levels[0]).toBe(1);
  levels.forEach((level, index) => {
    if (index > 0) expect(level - (levels[index - 1] ?? 0)).toBeLessThanOrEqual(1);
  });
}
