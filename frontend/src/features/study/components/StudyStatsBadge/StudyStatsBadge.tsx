import { Clock, Flame } from "lucide-react";
import { t } from "@/shared/i18n/t";
import { formatMinutes } from "@/shared/lib/format";

interface StudyStatsBadgeProps {
  streakDays: number;
  weekMinutes: number;
}

function streakText(days: number): string {
  if (days <= 0) return t("study.stats.streakNone");
  return t(days === 1 ? "study.stats.streakOne" : "study.stats.streakMany", { count: days });
}

/**
 * Day streak and hours of the week, as text and library icons (never an
 * emoji: it renders differently from one system to another and reads badly to screen readers).
 */
export function StudyStatsBadge({ streakDays, weekMinutes }: StudyStatsBadgeProps) {
  return (
    <ul aria-label={t("study.stats.label")} className="flex items-center gap-3 text-sm">
      <li className="flex items-center gap-1.5">
        <Flame aria-hidden="true" className="size-4 text-primary" />
        <span>{streakText(streakDays)}</span>
      </li>
      <li className="flex items-center gap-1.5">
        <Clock aria-hidden="true" className="size-4 text-primary" />
        <span className="tabular-nums">
          {t("study.stats.week", { time: formatMinutes(weekMinutes) })}
        </span>
      </li>
    </ul>
  );
}
