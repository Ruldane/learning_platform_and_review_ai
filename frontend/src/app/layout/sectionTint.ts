import type { CSSProperties } from "react";

/**
 * Tint of an active section: 14% background of its color and a solid underline under the entry.
 * The color goes through the `--section-color` variable (see `sectionVars`), set on the element.
 */
export const ACTIVE_TINT =
  "border-[var(--section-color)] bg-[color-mix(in_srgb,var(--section-color)_14%,transparent)]";

/** The reserved underline when the entry is not active: nothing moves on page change. */
export const IDLE_TINT = "border-transparent";

/** The CSS variable `--section-color` of a section, to pass to `style`. */
export function sectionVars(color: string): CSSProperties {
  return { "--section-color": color } as CSSProperties;
}
