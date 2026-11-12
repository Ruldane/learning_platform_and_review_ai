import type { LevelView } from "./viewTypes";

/** Les cinq états d'une compétence sur la carte, du moins au plus maîtrisé (« absent » : aucun niveau). */
export const LEVEL_KEYS = ["absent", "declare", "en_cours", "valide", "prouve"] as const;
export type LevelKey = (typeof LEVEL_KEYS)[number];

/**
 * Couleur de chaque niveau. Chacune garde un texte blanc au contraste AA (≥ 4,5:1) et ressort
 * sur le fond de page (≥ 4,5:1) : voir `levels.test.ts`. La couleur n'est jamais seule : le niveau
 * est écrit dans chaque nœud et dans la légende.
 */
export const LEVEL_COLORS: Record<LevelKey, string> = {
  absent: "#57606a",
  declare: "#8a5200",
  en_cours: "#1f5fa6",
  valide: "#0f6b5c",
  prouve: "#6a3d9a",
};

export function levelKey(level: LevelView): LevelKey {
  return level ?? "absent";
}
