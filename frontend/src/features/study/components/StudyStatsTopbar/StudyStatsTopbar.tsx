import { t } from "@/shared/i18n/t";
import { StudyStatsBadge } from "../StudyStatsBadge";

interface StudyStatsTopbarProps {
  /** The figures; `null` until they are read or when the read failed. */
  stats: { streakDays: number; weekMinutes: number } | null;
  failed: boolean;
}

/**
 * The day streak and the week's hours, in the top bar. Silent while
 * loading; a missed read is said in one discreet line (the bar rereads on its own).
 */
export function StudyStatsTopbar({ stats, failed }: StudyStatsTopbarProps) {
  if (stats) return <StudyStatsBadge {...stats} />;
  if (failed) {
    return <p className="text-sm text-muted-foreground">{t("study.stats.unavailable")}</p>;
  }
  return null;
}
