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
import { useFocusAfterMove } from "./useFocusAfterMove";

interface WeekCalendarProps {
  week: WeekView;
  /** False: read-only, no handle or move menu. */
  editable: boolean;
  onMoveTask: (taskId: string, date: string) => void;
}

/**
 * One-week calendar, one day per column. A task is moved with the mouse, the keyboard
 * (space, arrows) or via its card's « Déplacer vers… » menu. A day over its capacity
 * is flagged, never refused: only the week is bounded (D88).
 */
export function WeekCalendar({ week, editable, onMoveTask }: WeekCalendarProps) {
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
    useSensor(KeyboardSensor, { coordinateGetter: columnKeyboardCoordinates }),
  );
  const announcements = useMemo(() => makeAnnouncements(week), [week]);
  const dates = week.days.map((day) => day.date);
  const { gridRef, moved } = useFocusAfterMove(week);

  function onMenuMove(taskId: string, date: string) {
    moved(taskId);
    onMoveTask(taskId, date);
  }

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
        ref={gridRef}
        role="group"
        aria-label={t("program.calendar.label", { rank: week.rank })}
        tabIndex={0}
        className="grid grid-cols-[repeat(7,minmax(8.5rem,1fr))] items-start gap-1.5 overflow-x-auto pb-2 focus-visible:outline-2 focus-visible:outline-ring"
      >
        {week.days.map((day) => (
          <DayColumn
            key={day.date}
            day={day}
            editable={editable}
            dates={dates}
            onMoveTask={onMenuMove}
          />
        ))}
      </div>
    </DndContext>
  );
}
