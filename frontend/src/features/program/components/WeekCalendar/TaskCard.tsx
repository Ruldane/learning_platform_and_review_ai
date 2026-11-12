import { useDraggable } from "@dnd-kit/core";
import { GripVertical } from "lucide-react";
import { t } from "@/shared/i18n/t";
import { cn } from "@/shared/lib/utils";
import type { TaskView } from "../viewTypes";
import { MoveMenu } from "./MoveMenu";
import { TaskBadges } from "./TaskBadges";

interface TaskCardProps {
  task: TaskView;
  editable: boolean;
  /** Jours où la tâche peut aller (`AAAA-MM-JJ`). */
  moveTargets: string[];
  onMove: (date: string) => void;
}

/** Carte d'une tâche dans le calendrier : poignée de glisser, détails et menu « Déplacer vers… ». */
export function TaskCard({ task, editable, moveTargets, onMove }: TaskCardProps) {
  const { attributes, listeners, setNodeRef, setActivatorNodeRef, transform, isDragging } =
    useDraggable({
      id: task.id,
      disabled: !editable,
      attributes: { roleDescription: t("program.calendar.dragRole") },
    });
  const style = transform
    ? { transform: `translate3d(${transform.x}px, ${transform.y}px, 0)` }
    : undefined;
  return (
    <li
      ref={setNodeRef}
      data-task-id={task.id}
      style={style}
      className={cn(
        "relative flex flex-col gap-1 rounded-lg border bg-background p-2 text-xs",
        task.done && "bg-muted text-muted-foreground",
        isDragging && "z-30 shadow-lg ring-2 ring-ring",
      )}
    >
      <div className="flex items-start gap-1">
        {editable && (
          <button
            ref={setActivatorNodeRef}
            type="button"
            {...attributes}
            {...listeners}
            aria-label={t("program.calendar.dragHandle", { title: task.title })}
            className="mt-0.5 shrink-0 cursor-grab rounded text-muted-foreground outline-none focus-visible:ring-3 focus-visible:ring-ring active:cursor-grabbing"
          >
            <GripVertical aria-hidden="true" className="size-3.5" />
          </button>
        )}
        <p className={cn("min-w-0 flex-1 font-medium break-words", task.done && "line-through")}>
          {task.title}
        </p>
        {editable && <MoveMenu taskTitle={task.title} dates={moveTargets} onSelect={onMove} />}
      </div>
      <p className="break-words text-muted-foreground">{task.moduleTitle}</p>
      <TaskBadges task={task} />
    </li>
  );
}
