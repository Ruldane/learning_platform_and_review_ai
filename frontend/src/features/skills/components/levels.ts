import type { LevelView } from "./viewTypes";

/** The five states of a skill on the map, from least to most mastered (« absent »: no level). */
export const LEVEL_KEYS = ["absent", "declared", "in_progress", "validated", "proven"] as const;
export type LevelKey = (typeof LEVEL_KEYS)[number];

/**
 * Colour of each level. Each keeps white text at AA contrast (≥ 4.5:1) and stands out
 * on the page background (≥ 4.5:1): see `levels.test.ts`. The colour is never alone: the level
 * is written in each node and in the legend.
 */
export const LEVEL_COLORS: Record<LevelKey, string> = {
  absent: "#57606a",
  declared: "#8a5200",
  in_progress: "#1f5fa6",
  validated: "#0f6b5c",
  proven: "#6a3d9a",
};

export function levelKey(level: LevelView): LevelKey {
  return level ?? "absent";
}
