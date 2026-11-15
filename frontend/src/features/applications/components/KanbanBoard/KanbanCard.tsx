import { useDraggable } from "@dnd-kit/core";
import { GripVertical } from "lucide-react";
import { t } from "@/shared/i18n/t";
import { cn } from "@/shared/lib/utils";
import { ApplicationCard } from "../ApplicationCard";
import type { ApplicationView, StatusView } from "../viewTypes";
import { StatusMoveMenu } from "./StatusMoveMenu";

interface KanbanCardProps {
  application: ApplicationView;
  onMove: (status: StatusView) => void;
  onOpen?: (id: string) => void;
}

/** Une carte du tableau de suivi : poignée de glisser, fiche et menu « Déplacer vers… ». */
export function KanbanCard({ application, onMove, onOpen }: KanbanCardProps) {
  const { attributes, listeners, setNodeRef, setActivatorNodeRef, transform, isDragging } =
    useDraggable({
      id: application.id,
      attributes: { roleDescription: t("applications.board.dragRole") },
    });
  const style = transform
    ? { transform: `translate3d(${transform.x}px, ${transform.y}px, 0)` }
    : undefined;
  return (
    <li
      ref={setNodeRef}
      data-application-id={application.id}
      style={style}
      className={cn(
        "relative flex items-start gap-1 rounded-lg border bg-background p-2",
        isDragging && "z-30 shadow-lg ring-2 ring-ring",
      )}
    >
      <button
        ref={setActivatorNodeRef}
        type="button"
        {...attributes}
        {...listeners}
        aria-label={t("applications.board.dragHandle", {
          title: application.title,
          company: application.company,
        })}
        data-drag-handle=""
        className="mt-0.5 shrink-0 cursor-grab touch-none rounded text-muted-foreground outline-none focus-visible:ring-3 focus-visible:ring-ring active:cursor-grabbing"
      >
        <GripVertical aria-hidden="true" className="size-3.5" />
      </button>
      <div className="min-w-0 flex-1">
        <ApplicationCard application={application} onOpen={onOpen} />
      </div>
      <StatusMoveMenu
        title={application.title}
        company={application.company}
        current={application.status}
        onSelect={onMove}
      />
    </li>
  );
}
