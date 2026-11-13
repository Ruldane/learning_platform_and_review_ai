import { useEffect, useRef } from "react";
import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import { Button, buttonVariants } from "@/shared/ui/button";
import { QuizResult } from "../../components/QuizResult";
import type { AttemptResultView } from "../../components/viewTypes";

interface AttemptResultProps {
  result: AttemptResultView;
  /** Le quiz est relu : « Refaire le quiz » attend l'ordre du prochain essai. */
  refreshing: boolean;
  onBack: () => void;
}

/**
 * La note d'un essai, puis « Refaire le quiz » et « Voir tous les quiz ». Après un échec,
 * « Refaire » n'apparaît qu'une fois la date du nouvel essai venue (F9 : le back refuserait).
 * Le résultat arrive à la place du formulaire : le focus y va pour que la note soit lue.
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
        <Link to="/etudier/quiz" className={buttonVariants({ variant: "outline" })}>
          {t("quiz.page.allQuizzes")}
        </Link>
      </div>
    </div>
  );
}
