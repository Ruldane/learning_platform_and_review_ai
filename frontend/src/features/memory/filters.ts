import type { ItemFilterValue } from "./components/viewTypes";

/** No filter: all active items. */
export const NO_FILTERS: ItemFilterValue = { kind: "", tag: "", author: "", since: "", until: "" };

/** Decisions waiting for agreement (« À confirmer » box). */
export const PENDING_FILTERS: ItemFilterValue = { ...NO_FILTERS, kind: "decision" };

export function isPristine(filters: ItemFilterValue): boolean {
  return Object.values(filters).every((value) => value === "");
}

/** Authors always offered: the user and the Archivist, who writes to memory (SPEC 4.5). */
const KNOWN_AUTHORS = ["user", "archivist"];

/** Author list of the filter: the known authors, those seen in the list, and the current filter. */
export function authorChoices(seen: string[], current: string): string[] {
  return [...new Set([...KNOWN_AUTHORS, ...seen, ...(current === "" ? [] : [current])])];
}
