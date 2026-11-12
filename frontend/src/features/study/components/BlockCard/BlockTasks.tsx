import { t } from "@/shared/i18n/t";
import { formatMinutes } from "@/shared/lib/format";
import type { BlockView } from "../viewTypes";

/** Les tâches du bloc (type, titre, durée) et leur total. */
export function BlockTasks({ tasks }: { tasks: BlockView["tasks"] }) {
  const total = tasks.reduce((sum, task) => sum + task.minutes, 0);
  return (
    <>
      <ul aria-label={t("study.block.tasks")} className="flex flex-col gap-1.5 text-sm">
        {tasks.map((task) => (
          <li key={task.id} className="flex flex-wrap items-baseline gap-x-2">
            <span className="rounded bg-muted px-1.5 py-0.5 text-xs">
              {t(`program.taskType.${task.type}`)}
            </span>
            <span className="min-w-0 flex-1">{task.title}</span>
            <span className="tabular-nums text-muted-foreground">
              {formatMinutes(task.minutes)}
            </span>
          </li>
        ))}
      </ul>
      <p className="text-sm font-medium tabular-nums">
        {t("study.block.total", { time: formatMinutes(total) })}
      </p>
    </>
  );
}
