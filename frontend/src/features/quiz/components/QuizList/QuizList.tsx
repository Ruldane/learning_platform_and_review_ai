import type { RunSource } from "@/shared/lib/runSource";
import { t } from "@/shared/i18n/t";
import { EmptyState } from "@/shared/ui/states/EmptyState";
import type { QuizSummaryView } from "../viewTypes";
import { QuizItem } from "./QuizItem";

interface QuizListProps {
  items: QuizSummaryView[];
  onPrepare: (moduleId: string, source?: RunSource) => void;
  onOpen: (quizId: string) => void;
  /** The module whose quiz is being prepared: its button does not fire twice. */
  pendingModuleId?: string | null;
}

/** The program's modules, by week, with their best score and the quiz action. */
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
