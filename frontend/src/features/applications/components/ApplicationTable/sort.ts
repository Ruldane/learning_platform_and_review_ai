import { STATUS_ORDER } from "../viewTypes";
import type { ApplicationView } from "../viewTypes";

export type SortKey =
  "company" | "title" | "status" | "appliedOn" | "nextActionOn" | "dueReminders";
export type SortDirection = "ascending" | "descending";
export interface SortState {
  key: SortKey;
  direction: SortDirection;
}

type Value = string | number | null;

function valueOf(application: ApplicationView, key: SortKey): Value {
  if (key === "status") return STATUS_ORDER.indexOf(application.status);
  return application[key];
}

function compare(a: string | number, b: string | number): number {
  if (typeof a === "number" && typeof b === "number") return a - b;
  return String(a).localeCompare(String(b), "fr", { sensitivity: "base" });
}

/**
 * Records sorted by `sort` (the received order when unsorted). The sort is stable; a missing value
 * (date not set) always goes to the end of the list, in both directions.
 */
export function sortApplications(
  applications: ApplicationView[],
  sort: SortState | null,
): ApplicationView[] {
  if (!sort) return applications;
  const sign = sort.direction === "ascending" ? 1 : -1;
  return [...applications].sort((a, b) => {
    const left = valueOf(a, sort.key);
    const right = valueOf(b, sort.key);
    if (left === null && right === null) return 0;
    if (left === null) return 1;
    if (right === null) return -1;
    return sign * compare(left, right);
  });
}

/** A first click sorts ascending, a second reverses it; on another column, it starts ascending
 * again. */
export function nextSort(current: SortState | null, key: SortKey): SortState {
  if (current?.key === key) {
    return { key, direction: current.direction === "ascending" ? "descending" : "ascending" };
  }
  return { key, direction: "ascending" };
}
