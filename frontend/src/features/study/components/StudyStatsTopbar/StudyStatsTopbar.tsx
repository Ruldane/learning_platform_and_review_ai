import { t } from "@/shared/i18n/t";
import { StudyStatsBadge } from "../StudyStatsBadge";

interface StudyStatsTopbarProps {
  /** Les chiffres ; `null` tant qu'ils ne sont pas lus ou quand la lecture a échoué. */
  stats: { streakDays: number; weekMinutes: number } | null;
  failed: boolean;
}

/**
 * La série de jours et les heures de la semaine, dans la barre du haut. Silencieuse pendant le
 * chargement ; une lecture manquée se dit en une ligne discrète (la barre relit toute seule).
 */
export function StudyStatsTopbar({ stats, failed }: StudyStatsTopbarProps) {
  if (stats) return <StudyStatsBadge {...stats} />;
  if (failed) {
    return <p className="text-sm text-muted-foreground">{t("study.stats.unavailable")}</p>;
  }
  return null;
}
