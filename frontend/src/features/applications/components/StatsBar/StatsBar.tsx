import { t } from "@/shared/i18n/t";
import { formatNumber, formatPercent } from "../format";
import { Indicator } from "./Indicator";
import { STATUS_ORDER } from "../viewTypes";
import type { StatsView } from "../viewTypes";

interface StatsBarProps {
  stats: StatsView;
}

function delay(days: number | null): string {
  if (days === null) return t("applications.stats.none");
  const key = days === 1 ? "one" : "many";
  return t(`applications.stats.delayValue.${key}`, { count: formatNumber(days) });
}

/** Counts by status, response rate and time, and follow-ups due. */
export function StatsBar({ stats }: StatsBarProps) {
  const { byStatus, responseRate, meanResponseDays, dueReminders } = stats;
  return (
    <section
      aria-label={t("applications.stats.label")}
      className="flex flex-col gap-3 rounded-xl border bg-card p-4"
    >
      <ul aria-label={t("applications.stats.byStatus")} className="flex flex-wrap gap-2">
        {STATUS_ORDER.map((status) => (
          <li
            key={status}
            className="flex items-baseline gap-1.5 rounded-lg border bg-background px-2 py-1 text-sm"
          >
            <span>{t(`applications.status.${status}`)}</span>
            <span className="font-semibold tabular-nums">{byStatus[status]}</span>
          </li>
        ))}
      </ul>
      <dl className="flex flex-wrap gap-x-8 gap-y-2">
        <Indicator
          label={t("applications.stats.responseRate")}
          value={responseRate === null ? t("applications.stats.none") : formatPercent(responseRate)}
        />
        <Indicator label={t("applications.stats.meanDelay")} value={delay(meanResponseDays)} />
        <Indicator label={t("applications.stats.due")} value={String(dueReminders)} />
      </dl>
    </section>
  );
}
