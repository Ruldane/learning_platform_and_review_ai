import type { MemoryKindView } from "./viewTypes";

/**
 * One fixed colour per memory item type (list, detail, search results, and the
 * map on the Map screen). Each reaches a contrast of at least 4.5:1 on the off-white background
 * (#FAFAF7), checked by `kindColors.test.ts`; colour is never the only signal: the name of the
 * type is always written next to it.
 */
export const KIND_COLORS: Record<MemoryKindView, string> = {
  document: "#3d5a99",
  skill: "#1b7e3b",
  lesson: "#8a5a00",
  source: "#00798a",
  posting: "#b4461f",
  decision: "#8a2ea8",
};

/** The six types, in the order shown in the filters and selectors. */
export const MEMORY_KINDS = Object.keys(KIND_COLORS) as MemoryKindView[];
