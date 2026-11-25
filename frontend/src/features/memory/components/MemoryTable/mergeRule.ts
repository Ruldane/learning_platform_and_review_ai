import type { MemoryItemRow } from "../viewTypes";

/** Merge allowed: at least two items, all of the same type, and never documents. */
export function canMerge(rows: MemoryItemRow[]): boolean {
  if (rows.length < 2) return false;
  const kind = rows[0]?.kind;
  return kind !== "document" && rows.every((item) => item.kind === kind);
}
