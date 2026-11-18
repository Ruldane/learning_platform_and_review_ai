import { CircleCheck } from "lucide-react";
import { t } from "@/shared/i18n/t";
import type { LessonSummaryOut } from "../../types";

/** Avancement d’une leçon dans le programme : « Terminée », « n / m tâches faites » ou rien. */
export function LessonTaskProgress({ lesson }: { lesson: LessonSummaryOut }) {
  if (lesson.completed) {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 px-2 py-0.5 font-medium text-primary">
        <CircleCheck aria-hidden="true" className="size-4" />
        {t("lessons.list.completed")}
      </span>
    );
  }
  if (!lesson.done_tasks || !lesson.total_tasks) return null;
  return (
    <span className="text-muted-foreground">
      {t("lessons.list.tasksDone", { done: lesson.done_tasks, total: lesson.total_tasks })}
    </span>
  );
}
