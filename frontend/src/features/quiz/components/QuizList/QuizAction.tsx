import type { RunSource } from "@/shared/lib/runSource";
import { useLaunchSource } from "@/shared/session-ui";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { QuizSummaryView } from "../viewTypes";

interface QuizActionProps {
  item: QuizSummaryView;
  /** Une préparation est en route pour ce module : son bouton est coupé. */
  pending: boolean;
  onPrepare: (moduleId: string, source?: RunSource) => void;
  onOpen: (quizId: string) => void;
}

/**
 * Le bouton d'une ligne : préparer, réessayer une préparation ratée, passer ou refaire le quiz.
 * Tant que le nouvel essai n'est pas venu (`retryOn`), pas de bouton : la ligne dit la date.
 */
export function QuizAction({ item, pending, onPrepare, onOpen }: QuizActionProps) {
  const launch = useLaunchSource();
  const label = (action: string) => t("quiz.list.action", { action, module: item.moduleTitle });
  if (item.status === "generating") return null;
  if (item.status === "ready" && item.retryOn !== null) return null;
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
    <div className="flex flex-wrap items-end gap-2">
      {launch.menu}
      <Button
        variant="outline"
        disabled={pending}
        aria-label={label(text)}
        onClick={() =>
          launch.source === undefined
            ? onPrepare(item.moduleId)
            : onPrepare(item.moduleId, launch.source)
        }
      >
        {text}
      </Button>
    </div>
  );
}
