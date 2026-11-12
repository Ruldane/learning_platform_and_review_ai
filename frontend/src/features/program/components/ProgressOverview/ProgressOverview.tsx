import { t } from "@/shared/i18n/t";
import { formatMinutes } from "@/shared/lib/format";
import type { ProgressView, WeekView } from "../viewTypes";
import { ProgressBar } from "./ProgressBar";
import { WeekProgress } from "./WeekProgress";
import { percentOf } from "./percentOf";

interface ProgressOverviewProps {
  progress: ProgressView;
  weeks: WeekView[];
}

/** Avancement global (tâches et heures faites sur prévues) et une barre par semaine. */
export function ProgressOverview({ progress, weeks }: ProgressOverviewProps) {
  if (progress.tasksPlanned === 0) {
    return <p className="text-sm text-muted-foreground">{t("program.progress.empty")}</p>;
  }
  const percent = percentOf(progress.minutesDone, progress.minutesPlanned);
  return (
    <section aria-label={t("program.progress.label")} className="flex flex-col gap-4">
      <dl className="grid grid-cols-2 gap-3">
        <div className="rounded-lg border bg-card p-3">
          <dt className="text-sm text-muted-foreground">{t("program.progress.tasks")}</dt>
          <dd className="text-xl font-semibold tabular-nums">
            {t("program.progress.tasksValue", {
              done: progress.tasksDone,
              planned: progress.tasksPlanned,
            })}
          </dd>
        </div>
        <div className="rounded-lg border bg-card p-3">
          <dt className="text-sm text-muted-foreground">{t("program.progress.hours")}</dt>
          <dd className="text-xl font-semibold tabular-nums">
            {t("program.progress.hoursValue", {
              done: formatMinutes(progress.minutesDone),
              planned: formatMinutes(progress.minutesPlanned),
            })}
          </dd>
        </div>
      </dl>
      <div className="flex flex-col gap-1">
        <div className="flex items-baseline justify-between text-sm">
          <span>{t("program.progress.overall")}</span>
          <span className="tabular-nums">{t("program.progress.percent", { percent })}</span>
        </div>
        <ProgressBar label={t("program.progress.overall")} percent={percent} />
      </div>
      <div className="flex flex-col gap-2">
        <h3 className="text-sm font-semibold">{t("program.progress.byWeek")}</h3>
        <ul className="flex flex-col gap-3">
          {weeks.map((week) => (
            <WeekProgress key={week.rank} week={week} />
          ))}
        </ul>
      </div>
    </section>
  );
}
