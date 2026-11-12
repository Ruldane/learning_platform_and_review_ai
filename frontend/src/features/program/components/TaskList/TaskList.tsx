import { t } from "@/shared/i18n/t";
import type { NewTaskInput, WeekView } from "../viewTypes";
import { AddTaskForm } from "./AddTaskForm";
import { WeekSection } from "./WeekSection";

interface TaskListProps {
  weeks: WeekView[];
  /** Faux : lecture seule, ni case active, ni suppression, ni formulaire d'ajout. */
  editable: boolean;
  onToggleDone: (taskId: string, done: boolean) => void;
  onDelete: (taskId: string) => void;
  onAdd: (input: NewTaskInput) => void | Promise<unknown>;
  /** Refus du serveur à l'ajout, affiché sous le formulaire. */
  addError?: string | null;
}

/** Liste complète des tâches, par semaine puis par module, avec le formulaire d'ajout. */
export function TaskList({
  weeks,
  editable,
  onToggleDone,
  onDelete,
  onAdd,
  addError,
}: TaskListProps) {
  if (weeks.length === 0) {
    return <p className="text-sm text-muted-foreground">{t("program.list.empty")}</p>;
  }
  return (
    <div className="flex flex-col gap-6">
      <h2 className="sr-only">{t("program.list.label")}</h2>
      {weeks.map((week) => (
        <WeekSection
          key={week.rank}
          week={week}
          editable={editable}
          onToggleDone={onToggleDone}
          onDelete={onDelete}
        />
      ))}
      {editable && <AddTaskForm weeks={weeks} onAdd={onAdd} error={addError} />}
    </div>
  );
}
