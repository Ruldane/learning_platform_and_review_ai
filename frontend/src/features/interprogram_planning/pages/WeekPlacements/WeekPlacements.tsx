import { t } from "@/shared/i18n/t";
import type { Week } from "../../api";
import { formatDay } from "../../dates";

export function WeekPlacements({ tasks }: { tasks: Week["placements"] }) {
  if (!tasks.length) return null;
  return (
    <div>
      <h4 className="font-semibold">{t("interprogramPlanning.tasks")}</h4>
      <ul className="list-inside list-disc">
        {tasks.map((task) => (
          <li key={task.task_id}>
            {t("interprogramPlanning.scheduledTask", {
              task: task.title,
              date: formatDay(task.planned_date),
              minutes: task.minutes,
            })}
            {task.from_date !== task.planned_date && (
              <p className="pl-4 text-sm">
                {t("interprogramPlanning.movedFrom", { date: formatDay(task.from_date) })}
              </p>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
