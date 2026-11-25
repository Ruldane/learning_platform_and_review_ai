import { StudyStatsTopbar } from "./components/StudyStatsTopbar";
import { useStudySummary } from "./hooks/useStudySummary";

/** Re-reading of the streak and hours: every 60 s. */
const REFRESH_MS = 60_000;

/** The `topbar` slot: reads the study summary and passes it to `StudyStatsTopbar`. */
export function StudyTopbarSlot() {
  const summary = useStudySummary(REFRESH_MS);
  const stats = summary.data
    ? { streakDays: summary.data.streak_days, weekMinutes: summary.data.week_minutes }
    : null;
  return <StudyStatsTopbar stats={stats} failed={summary.isError && !summary.data} />;
}
