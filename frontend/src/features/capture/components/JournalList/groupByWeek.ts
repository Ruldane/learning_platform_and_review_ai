import { parseDay } from "@/shared/lib/format";
import type { JournalEntryView, JournalWeekView } from "../viewTypes";

const DAY_MS = 86_400_000;

/** The Monday (`AAAA-MM-JJ`) of the week that holds this day. */
export function weekStartOf(day: string): string {
  const date = parseDay(day);
  const sinceMonday = (date.getUTCDay() + 6) % 7;
  return new Date(date.getTime() - sinceMonday * DAY_MS).toISOString().slice(0, 10);
}

/**
 * Groups entries by week, most recent first. Within a week, the weekly review
 * goes first; the others keep the received order (newest to oldest).
 * A week split across two pages ends up in a single group.
 */
export function groupByWeek(entries: JournalEntryView[]): JournalWeekView[] {
  const weeks = new Map<string, JournalEntryView[]>();
  for (const entry of entries) {
    const key = weekStartOf(entry.occurredOn);
    weeks.set(key, [...(weeks.get(key) ?? []), entry]);
  }
  return [...weeks.entries()]
    .sort(([a], [b]) => b.localeCompare(a))
    .map(([weekStart, items]) => ({
      weekStart,
      entries: [
        ...items.filter((entry) => entry.kind === "weekly_review"),
        ...items.filter((entry) => entry.kind !== "weekly_review"),
      ],
    }));
}
