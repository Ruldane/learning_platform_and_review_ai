import { expect } from "vitest";

/** The heading levels of the page, in document order. */
export const headingLevels = (root: ParentNode = document): number[] =>
  Array.from(root.querySelectorAll("h1, h2, h3, h4, h5, h6")).map((node) =>
    Number(node.tagName.slice(1)),
  );

/**
 * The page outline is consistent: a single `h1`, first, then never a level skip downwards
 * (an `h3` does not follow an `h1`).
 */
export function expectCoherentOutline(root: ParentNode = document): void {
  const levels = headingLevels(root);
  expect(levels.filter((level) => level === 1)).toHaveLength(1);
  expect(levels[0]).toBe(1);
  levels.forEach((level, index) => {
    if (index > 0) expect(level - (levels[index - 1] ?? 0)).toBeLessThanOrEqual(1);
  });
}
