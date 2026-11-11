import type { MemoryKindView } from "./viewTypes";

/**
 * Une couleur fixe par type d'élément de mémoire (liste, détail, résultats de recherche, et la
 * carte de l'écran Carte). Chacune atteint un contraste d'au moins 4,5:1 sur le fond blanc cassé
 * (#FAFAF7), vérifié par `kindColors.test.ts` ; la couleur n'est jamais le seul signal : le nom du
 * type est toujours écrit à côté.
 */
export const KIND_COLORS: Record<MemoryKindView, string> = {
  document: "#3d5a99",
  acquis: "#1b7e3b",
  lecon: "#8a5a00",
  source: "#00798a",
  offre: "#b4461f",
  decision: "#8a2ea8",
};

/** Les six types, dans l'ordre d'affichage des filtres et des sélecteurs. */
export const MEMORY_KINDS = Object.keys(KIND_COLORS) as MemoryKindView[];
