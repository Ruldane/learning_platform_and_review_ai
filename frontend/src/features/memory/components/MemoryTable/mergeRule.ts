import type { MemoryItemRow } from "../viewTypes";

/** Fusion permise : au moins deux éléments, tous du même type, et jamais des documents. */
export function canMerge(rows: MemoryItemRow[]): boolean {
  if (rows.length < 2) return false;
  const kind = rows[0]?.kind;
  return kind !== "document" && rows.every((item) => item.kind === kind);
}
