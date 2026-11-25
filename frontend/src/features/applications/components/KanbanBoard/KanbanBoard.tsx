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
import { STATUS_ORDER } from "../viewTypes";
import type { ApplicationView, StatusView } from "../viewTypes";
import { KanbanColumn } from "./KanbanColumn";
import { makeAnnouncements } from "./announcements";
import { columnKeyboardCoordinates } from "./keyboardCoordinates";
import { useBoardMoves } from "./useBoardMoves";

interface KanbanBoardProps {
  applications: ApplicationView[];
  /** Called for a move by drag and drop or by the « Déplacer vers… » menu. */
  onMove: (id: string, status: StatusView) => void;
  onOpen?: (id: string) => void;
}

/**
 * The tracking board: one column per status, in status order. A card moves by
 * mouse, keyboard (space, arrows) or the « Déplacer vers… » menu; the move by the
 * menu is announced in a live region, drag and drop by dnd-kit. Eight columns do not
 * fit in 1 024 px: the horizontal scroll is the table's (never the page's).
 */
export function KanbanBoard({ applications, onMove, onOpen }: KanbanBoardProps) {
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
    useSensor(KeyboardSensor, { coordinateGetter: columnKeyboardCoordinates }),
  );
  const announcements = useMemo(() => makeAnnouncements(applications), [applications]);
  const { announcement, boardRef, move } = useBoardMoves(applications, onMove);

  function onDragEnd({ active, over, activatorEvent }: DragEndEvent) {
    const source = activatorEvent instanceof KeyboardEvent ? "keyboard" : "pointer";
    if (over) move(String(active.id), String(over.id) as StatusView, source);
  }

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCenter}
      onDragEnd={onDragEnd}
      accessibility={{
        announcements,
        screenReaderInstructions: { draggable: t("applications.board.dragInstructions") },
      }}
    >
      <div
        ref={boardRef}
        role="group"
        aria-label={t("applications.board.label")}
        className="grid w-full max-w-full min-w-0 grid-cols-[repeat(8,minmax(11rem,1fr))] items-start gap-1.5 overflow-x-auto overscroll-x-contain pb-2"
      >
        {STATUS_ORDER.map((status) => (
          <KanbanColumn
            key={status}
            status={status}
            applications={applications.filter((item) => item.status === status)}
            onMove={(id, next) => move(id, next, "menu")}
            onOpen={onOpen}
          />
        ))}
      </div>
      <p role="status" aria-live="polite" className="sr-only">
        {announcement}
      </p>
    </DndContext>
  );
}
