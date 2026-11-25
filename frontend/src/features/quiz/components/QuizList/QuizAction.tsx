import type { RunSource } from "@/shared/lib/runSource";
import { useLaunchSource } from "@/shared/session-ui";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { QuizSummaryView } from "../viewTypes";

interface QuizActionProps {
  item: QuizSummaryView;
  /** A preparation is running for this module: its button is off. */
  pending: boolean;
  onPrepare: (moduleId: string, source?: RunSource) => void;
  onOpen: (quizId: string) => void;
}

/**
 * A row's button: prepare, retry a failed preparation, skip or redo the quiz.
 * Until the retry is due (`retryOn`) there is no button: the row shows the date.
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
