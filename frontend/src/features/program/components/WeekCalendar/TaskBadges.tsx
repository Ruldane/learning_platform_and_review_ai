import { t } from "@/shared/i18n/t";
import type { TaskView } from "../viewTypes";

const BADGE = "rounded bg-muted px-1.5 py-0.5";
const NOTE = "rounded bg-secondary px-1.5 py-0.5 text-secondary-foreground";

/** Type, durée, « déjà acquis » et « Fait » d'une tâche, en étiquettes textuelles. */
export function TaskBadges({ task }: { task: TaskView }) {
  return (
    <ul className="flex flex-wrap gap-1">
      <li className={BADGE}>{t(`program.taskType.${task.type}`)}</li>
      <li className={BADGE}>{t("program.task.minutes", { minutes: task.minutes })}</li>
      {task.alreadyKnown && <li className={NOTE}>{t("program.task.alreadyKnown")}</li>}
      {task.done && <li className={NOTE}>{t("program.task.done")}</li>}
    </ul>
  );
}
