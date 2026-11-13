import { useMutation } from "@tanstack/react-query";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { InlineError } from "@/shared/ui/states/InlineError";
import { startQuiz } from "../../api";

interface QuizFailedProps {
  moduleId: string;
  /** La raison donnée par le back, quand il en donne une. */
  reason: string | null;
  /** La préparation est relancée : relire le quiz. */
  onRelaunched: () => void;
}

/** La préparation du quiz a échoué : « Relancer la préparation » (le back relance le même quiz). */
export function QuizFailed({ moduleId, reason, onRelaunched }: QuizFailedProps) {
  const relaunch = useMutation({
    mutationFn: () => startQuiz(moduleId),
    onSuccess: onRelaunched,
  });
  return (
    <section className="flex flex-col items-start gap-3 rounded-xl border border-destructive/40 bg-card p-4">
      <h2 className="text-lg font-medium">{t("quiz.page.failedTitle")}</h2>
      {reason ? <p className="text-sm text-muted-foreground">{reason}</p> : null}
      {relaunch.error ? <InlineError message={errorMessage(relaunch.error)} /> : null}
      <Button disabled={relaunch.isPending} onClick={() => relaunch.mutate()}>
        {t("quiz.page.failedRetry")}
      </Button>
    </section>
  );
}
