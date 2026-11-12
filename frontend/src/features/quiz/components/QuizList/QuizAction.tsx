import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { QuizSummaryView } from "../viewTypes";

interface QuizActionProps {
  item: QuizSummaryView;
  /** Une préparation est en route pour ce module : son bouton est coupé. */
  pending: boolean;
  onPrepare: (moduleId: string) => void;
  onOpen: (quizId: string) => void;
}

/** Le bouton d'une ligne : préparer, réessayer une préparation ratée, passer ou refaire le quiz. */
export function QuizAction({ item, pending, onPrepare, onOpen }: QuizActionProps) {
  const label = (action: string) => t("quiz.list.action", { action, module: item.moduleTitle });
  if (item.status === "generating") return null;
  if (item.status === "ready" && item.quizId !== null) {
    const quizId = item.quizId;
    const text = t(item.bestScore === null ? "quiz.list.take" : "quiz.list.again");
    return (
      <Button variant="outline" aria-label={label(text)} onClick={() => onOpen(quizId)}>
        {text}
      </Button>
    );
  }
  const text = t(item.status === "failed" ? "quiz.list.retryPrepare" : "quiz.list.prepare");
  return (
    <Button
      variant="outline"
      disabled={pending}
      aria-label={label(text)}
      onClick={() => onPrepare(item.moduleId)}
    >
      {text}
    </Button>
  );
}
