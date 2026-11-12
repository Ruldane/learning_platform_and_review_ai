import {
  DndContext,
  KeyboardSensor,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import type { DragEndEvent } from "@dnd-kit/core";
import { useMemo } from "react";
import { t } from "@/shared/i18n/t";
import type { WeekView } from "../viewTypes";
import { DayColumn } from "./DayColumn";
import { makeAnnouncements } from "./announcements";
import { columnKeyboardCoordinates } from "./keyboardCoordinates";

interface WeekCalendarProps {
  week: WeekView;
  /** Faux : lecture seule, ni poignée ni menu de déplacement. */
  editable: boolean;
  onMoveTask: (taskId: string, date: string) => void;
}

/**
 * Calendrier d'une semaine, un jour par colonne. Une tâche se déplace à la souris, au clavier
 * (espace, flèches) ou par le menu « Déplacer vers… » de sa carte. Un jour au-delà de sa capacité
 * est signalé, jamais refusé : seule la semaine est bornée (D88).
 */
export function WeekCalendar({ week, editable, onMoveTask }: WeekCalendarProps) {
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
    useSensor(KeyboardSensor, { coordinateGetter: columnKeyboardCoordinates }),
  );
  const announcements = useMemo(() => makeAnnouncements(week), [week]);
  const dates = week.days.map((day) => day.date);

  function onDragEnd({ active, over }: DragEndEvent) {
    if (!editable || !over) return;
    const taskId = String(active.id);
    const date = String(over.id);
    const task = week.days.flatMap((day) => day.tasks).find((item) => item.id === taskId);
    if (task && task.plannedDate !== date) onMoveTask(taskId, date);
  }

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCenter}
      onDragEnd={onDragEnd}
      accessibility={{
        announcements,
        screenReaderInstructions: { draggable: t("program.calendar.dragInstructions") },
      }}
    >
      <div
        role="group"
        aria-label={t("program.calendar.label", { rank: week.rank })}
        className="grid grid-cols-7 items-start gap-1.5"
      >
        {week.days.map((day) => (
          <DayColumn
            key={day.date}
            day={day}
            editable={editable}
            dates={dates}
            onMoveTask={onMoveTask}
          />
        ))}
      </div>
    </DndContext>
  );
}
