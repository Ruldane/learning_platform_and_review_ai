import { StudyStatsTopbar } from "./components/StudyStatsTopbar";
import { useStudySummary } from "./hooks/useStudySummary";

/** Relecture de la série et des heures : toutes les 60 s. */
const REFRESH_MS = 60_000;

/** Emplacement `topbar` de la feature : lit le résumé de l'étude et le passe à `StudyStatsTopbar`. */
export function StudyTopbarSlot() {
  const summary = useStudySummary(REFRESH_MS);
  const stats = summary.data
    ? { streakDays: summary.data.streak_days, weekMinutes: summary.data.week_minutes }
    : null;
  return <StudyStatsTopbar stats={stats} failed={summary.isError && !summary.data} />;
}
