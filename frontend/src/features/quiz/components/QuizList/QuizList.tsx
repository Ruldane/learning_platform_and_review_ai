import { t } from "@/shared/i18n/t";
import { EmptyState } from "@/shared/ui/states/EmptyState";
import type { QuizSummaryView } from "../viewTypes";
import { QuizItem } from "./QuizItem";

interface QuizListProps {
  items: QuizSummaryView[];
  onPrepare: (moduleId: string) => void;
  onOpen: (quizId: string) => void;
  /** Le module dont le quiz se prépare : son bouton ne se déclenche pas deux fois. */
  pendingModuleId?: string | null;
}

/** Les modules du programme, par semaine, avec leur meilleur score et l'action du quiz. */
export function QuizList({ items, onPrepare, onOpen, pendingModuleId = null }: QuizListProps) {
  if (items.length === 0) {
    return (
      <EmptyState title={t("quiz.list.emptyTitle")} description={t("quiz.list.emptyDescription")} />
    );
  }
  const ordered = [...items].sort((a, b) => a.weekRank - b.weekRank);
  return (
    <ul className="flex flex-col gap-3">
      {ordered.map((item) => (
        <QuizItem
          key={item.moduleId}
          item={item}
          pending={item.moduleId === pendingModuleId}
          onPrepare={onPrepare}
          onOpen={onOpen}
        />
      ))}
    </ul>
  );
}
