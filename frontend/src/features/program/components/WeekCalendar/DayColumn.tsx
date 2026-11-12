import { useDroppable } from "@dnd-kit/core";
import { TriangleAlert } from "lucide-react";
import { t } from "@/shared/i18n/t";
import { cn } from "@/shared/lib/utils";
import { shortDay } from "@/shared/lib/format";
import { dayLoad, dayOfMonth, weekdayLabel } from "../format";
import type { DayView } from "../viewTypes";
import { TaskCard } from "./TaskCard";

interface DayColumnProps {
  day: DayView;
  editable: boolean;
  /** Tous les jours de la semaine (`AAAA-MM-JJ`) : une tâche peut aller sur chacun d'eux. */
  dates: string[];
  /** Déplacement choisi dans le menu « Déplacer vers… » d'une carte. */
  onMoveTask: (taskId: string, date: string) => void;
}

/** Un jour du calendrier : charge face à la capacité (dépassement dit en toutes lettres) et tâches. */
export function DayColumn({ day, editable, dates, onMoveTask }: DayColumnProps) {
  const { setNodeRef, isOver } = useDroppable({ id: day.date, disabled: !editable });
  const load = dayLoad(day.tasks);
  const over = load > day.capacityMinutes;
  const values = { load, cap: day.capacityMinutes };
  return (
    <div
      ref={setNodeRef}
      role="group"
      aria-label={shortDay(day.date)}
      className={cn(
        "flex min-w-0 flex-col gap-2 rounded-xl border bg-card p-1.5",
        over && "border-destructive",
        isOver && "bg-muted ring-2 ring-ring",
      )}
    >
      <div className="flex flex-col gap-0.5 px-1">
        <p className="text-sm font-semibold">
          <span className="capitalize">{weekdayLabel(day.date)}</span> {dayOfMonth(day.date)}
        </p>
        {over ? (
          <p className="flex items-start gap-1 text-xs font-medium text-destructive">
            <TriangleAlert aria-hidden="true" className="mt-0.5 size-3 shrink-0" />
            {t("program.calendar.dayOver", values)}
          </p>
        ) : (
          <p className="text-xs text-muted-foreground tabular-nums">
            {t("program.calendar.dayLoad", values)}
          </p>
        )}
      </div>
      {day.tasks.length === 0 ? (
        <p className="px-1 text-xs text-muted-foreground">{t("program.calendar.dayEmpty")}</p>
      ) : (
        <ul className="flex flex-col gap-1.5">
          {day.tasks.map((task) => (
            <TaskCard
              key={task.id}
              task={task}
              editable={editable}
              moveTargets={dates.filter((date) => date !== day.date)}
              onMove={(date) => onMoveTask(task.id, date)}
            />
          ))}
        </ul>
      )}
    </div>
  );
}
