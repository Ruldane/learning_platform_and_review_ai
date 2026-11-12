import { t } from "@/shared/i18n/t";
import { formatMinutes } from "@/shared/lib/format";
import type { WeekView } from "../viewTypes";
import { ProgressBar } from "./ProgressBar";
import { percentOf } from "./percentOf";

interface WeekProgressProps {
  week: WeekView;
}

/** Une barre par semaine : minutes des tâches faites sur minutes prévues. */
export function WeekProgress({ week }: WeekProgressProps) {
  const tasks = week.days.flatMap((day) => day.tasks);
  const planned = tasks.reduce((sum, task) => sum + task.minutes, 0);
  const done = tasks.filter((task) => task.done).reduce((sum, task) => sum + task.minutes, 0);
  const label = t("program.progress.weekBar", { rank: week.rank, theme: week.theme });
  return (
    <li className="flex flex-col gap-1">
      <div className="flex items-baseline justify-between gap-3 text-sm">
        <span>{label}</span>
        <span className="text-muted-foreground tabular-nums">
          {t("program.progress.weekValue", {
            done: formatMinutes(done),
            planned: formatMinutes(planned),
          })}
        </span>
      </div>
      <ProgressBar label={label} percent={percentOf(done, planned)} />
    </li>
  );
}
