import { parseDay } from "@/shared/lib/format";
import type { JournalEntryView, JournalWeekView } from "../viewTypes";

const DAY_MS = 86_400_000;

/** Le lundi (`AAAA-MM-JJ`) de la semaine qui porte ce jour. */
export function weekStartOf(day: string): string {
  const date = parseDay(day);
  const sinceMonday = (date.getUTCDay() + 6) % 7;
  return new Date(date.getTime() - sinceMonday * DAY_MS).toISOString().slice(0, 10);
}

/**
 * Regroupe les entrées par semaine, la plus récente d'abord. Dans une semaine, le bilan
 * hebdomadaire passe en tête ; les autres gardent l'ordre reçu (du plus récent au plus ancien).
 * Une semaine répartie sur deux pages se retrouve en un seul groupe.
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
