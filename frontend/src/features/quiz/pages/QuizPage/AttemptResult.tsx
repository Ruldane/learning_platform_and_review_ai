import { useEffect, useRef } from "react";
import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import { Button, buttonVariants } from "@/shared/ui/button";
import { QuizResult } from "../../components/QuizResult";
import type { AttemptResultView } from "../../components/viewTypes";

interface AttemptResultProps {
  result: AttemptResultView;
  /** The quiz is re-read: « Refaire le quiz » waits for the next attempt's order. */
  refreshing: boolean;
  onBack: () => void;
}

/**
 * An attempt's grade, then « Refaire le quiz » and « Voir tous les quiz ». After a failure,
 * « Refaire » only appears once the new attempt's date has come (F9: the back end would refuse).
 * The result takes the place of the form: focus moves there so the grade gets read.
 */
export function AttemptResult({ result, refreshing, onBack }: AttemptResultProps) {
  const root = useRef<HTMLDivElement>(null);
  useEffect(() => root.current?.focus(), []);
  const waitRetry = !result.passed && result.followup?.retryOn != null;
  return (
    <div ref={root} tabIndex={-1} className="flex flex-col gap-4 outline-none">
      <QuizResult result={result} />
      <div className="flex flex-wrap gap-2">
        {waitRetry ? null : (
          <Button disabled={refreshing} onClick={onBack}>
            {t("quiz.page.again")}
          </Button>
        )}
        <Link to="/study/quiz" className={buttonVariants({ variant: "outline" })}>
          {t("quiz.page.allQuizzes")}
        </Link>
      </div>
    </div>
  );
}
