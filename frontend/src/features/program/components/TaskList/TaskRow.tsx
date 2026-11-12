import { Trash2 } from "lucide-react";
import { t } from "@/shared/i18n/t";
import { cn } from "@/shared/lib/utils";
import { Button } from "@/shared/ui/button";
import { shortDay } from "../format";
import type { TaskView } from "../viewTypes";

interface TaskRowProps {
  task: TaskView;
  editable: boolean;
  onToggleDone: (taskId: string, done: boolean) => void;
  onDelete: (taskId: string) => void;
}

/** Une tâche de la liste : case « faite », détails, critère de fin et suppression. */
export function TaskRow({ task, editable, onToggleDone, onDelete }: TaskRowProps) {
  return (
    <li className="flex items-start gap-3 rounded-lg border bg-background p-3">
      <input
        type="checkbox"
        checked={task.done}
        disabled={!editable}
        onChange={() => onToggleDone(task.id, !task.done)}
        aria-label={t("program.list.toggle", { title: task.title })}
        className="mt-1 size-4 shrink-0 accent-primary"
      />
      <div className="flex min-w-0 flex-1 flex-col gap-1">
        <p className={cn("font-medium", task.done && "text-muted-foreground line-through")}>
          {task.title}
        </p>
        <p className="text-sm text-muted-foreground">
          {t(`program.taskType.${task.type}`)} ·{" "}
          {t("program.task.minutes", { minutes: task.minutes })} · {shortDay(task.plannedDate)}
          {task.alreadyKnown && ` · ${t("program.task.alreadyKnown")}`}
        </p>
        <p className="text-sm">{t("program.list.criterion", { criterion: task.doneCriterion })}</p>
      </div>
      {editable && (
        <Button
          type="button"
          variant="ghost"
          size="icon-sm"
          aria-label={t("program.list.remove", { title: task.title })}
          onClick={() => onDelete(task.id)}
        >
          <Trash2 aria-hidden="true" />
        </Button>
      )}
    </li>
  );
}
