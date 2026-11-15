import { useDroppable } from "@dnd-kit/core";
import { t } from "@/shared/i18n/t";
import { cn } from "@/shared/lib/utils";
import type { ApplicationView, StatusView } from "../viewTypes";
import { KanbanCard } from "./KanbanCard";

interface KanbanColumnProps {
  status: StatusView;
  applications: ApplicationView[];
  onMove: (id: string, status: StatusView) => void;
  onOpen?: (id: string) => void;
}

/** Une colonne du tableau de suivi : un statut, son compte et ses cartes. */
export function KanbanColumn({ status, applications, onMove, onOpen }: KanbanColumnProps) {
  const { setNodeRef, isOver } = useDroppable({ id: status });
  const label = t(`applications.status.${status}`);
  const count = applications.length;
  return (
    <div
      ref={setNodeRef}
      role="group"
      data-status={status}
      aria-label={t("applications.board.columnLabel", { status: label, count })}
      className={cn(
        "flex min-w-0 flex-col gap-2 rounded-xl border bg-card p-1.5",
        isOver && "bg-muted ring-2 ring-ring",
      )}
    >
      <h3 className="flex items-baseline justify-between gap-2 px-1 text-sm font-semibold">
        <span>{label}</span>
        <span className="text-xs font-normal text-muted-foreground tabular-nums">{count}</span>
      </h3>
      {count === 0 ? (
        <p className="px-1 text-xs text-muted-foreground">{t("applications.board.empty")}</p>
      ) : (
        <ul className="flex flex-col gap-1.5">
          {applications.map((application) => (
            <KanbanCard
              key={application.id}
              application={application}
              onMove={(next) => onMove(application.id, next)}
              onOpen={onOpen}
            />
          ))}
        </ul>
      )}
    </div>
  );
}
