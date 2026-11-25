import { useLaunchSource } from "@/shared/session-ui";
import { useMutation } from "@tanstack/react-query";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { InlineError } from "@/shared/ui/states/InlineError";
import { startQuiz } from "../../api";

interface QuizFailedProps {
  moduleId: string;
  /** The reason given by the back end, when it gives one. */
  reason: string | null;
  /** The preparation is retried: re-read the quiz. */
  onRelaunched: () => void;
}

/** Quiz preparation failed: « Relancer la préparation » (the back end retries the same quiz). */
export function QuizFailed({ moduleId, reason, onRelaunched }: QuizFailedProps) {
  const launch = useLaunchSource();
  const relaunch = useMutation({
    mutationFn: () => startQuiz(moduleId, launch.source),
    onSuccess: onRelaunched,
  });
  return (
    <section className="flex flex-col items-start gap-3 rounded-xl border border-destructive/40 bg-card p-4">
      <h2 className="text-lg font-medium">{t("quiz.page.failedTitle")}</h2>
      {reason ? <p className="text-sm text-muted-foreground">{reason}</p> : null}
      {relaunch.error ? <InlineError message={errorMessage(relaunch.error)} /> : null}
      {launch.menu}
      <Button disabled={relaunch.isPending} onClick={() => relaunch.mutate()}>
        {t("quiz.page.failedRetry")}
      </Button>
    </section>
  );
}
