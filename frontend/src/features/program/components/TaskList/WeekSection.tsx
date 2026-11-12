import { t } from "@/shared/i18n/t";
import type { TaskView, WeekView } from "../viewTypes";
import { TaskRow } from "./TaskRow";

interface WeekSectionProps {
  week: WeekView;
  editable: boolean;
  onToggleDone: (taskId: string, done: boolean) => void;
  onDelete: (taskId: string) => void;
}

function byModule(week: WeekView): [string, TaskView[]][] {
  const groups = new Map<string, TaskView[]>();
  for (const task of week.days.flatMap((day) => day.tasks)) {
    groups.set(task.moduleTitle, [...(groups.get(task.moduleTitle) ?? []), task]);
  }
  return [...groups];
}

/** Les tâches d'une semaine, regroupées par module. */
export function WeekSection({ week, editable, onToggleDone, onDelete }: WeekSectionProps) {
  return (
    <section className="flex flex-col gap-3">
      <h3 className="text-base font-semibold">
        {t("program.list.weekTitle", { rank: week.rank, theme: week.theme })}
      </h3>
      {byModule(week).map(([moduleTitle, tasks]) => (
        <div key={moduleTitle} className="flex flex-col gap-2">
          <h4 className="text-sm font-medium text-muted-foreground">{moduleTitle}</h4>
          <ul className="flex flex-col gap-2">
            {tasks.map((task) => (
              <TaskRow
                key={task.id}
                task={task}
                editable={editable}
                onToggleDone={onToggleDone}
                onDelete={onDelete}
              />
            ))}
          </ul>
        </div>
      ))}
    </section>
  );
}
