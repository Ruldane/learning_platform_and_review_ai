import type { ItemFilterValue } from "./components/viewTypes";

/** Aucun filtre : tous les éléments actifs. */
export const NO_FILTERS: ItemFilterValue = { kind: "", tag: "", author: "", since: "", until: "" };

/** Les décisions en attente d'accord (boîte « À confirmer »). */
export const PENDING_FILTERS: ItemFilterValue = { ...NO_FILTERS, kind: "decision" };

export function isPristine(filters: ItemFilterValue): boolean {
  return Object.values(filters).every((value) => value === "");
}

/** Auteurs toujours proposés : l'utilisateur et l'Archiviste, qui écrit dans la mémoire (SPEC 4.5). */
const KNOWN_AUTHORS = ["user", "archivist"];

/** Liste des auteurs du filtre : les auteurs connus, ceux vus dans la liste, et le filtre en cours. */
export function authorChoices(seen: string[], current: string): string[] {
  return [...new Set([...KNOWN_AUTHORS, ...seen, ...(current === "" ? [] : [current])])];
}
