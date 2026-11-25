import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { InlineError } from "@/shared/ui/states/InlineError";

interface GradingFailedProps {
  /** The answers are kept: they can be resent. `false` after a page reload. */
  canResend: boolean;
  /** Message for a refused resend. */
  error: string | null;
  /** A resend is in flight: the button is off. */
  sending: boolean;
  onResend: () => void;
  onBack: () => void;
}

/** Grading failed: resend the same answers, or go back to the quiz. */
export function GradingFailed(props: GradingFailedProps) {
  const { canResend, error, sending, onResend, onBack } = props;
  return (
    <section className="flex flex-col items-start gap-3 rounded-xl border border-destructive/40 bg-card p-4">
      <h2 className="text-lg font-medium">{t("quiz.page.gradingFailedTitle")}</h2>
      {canResend ? (
        <p className="text-sm text-muted-foreground">{t("quiz.page.gradingFailedHelp")}</p>
      ) : null}
      {error ? <InlineError message={error} /> : null}
      <div className="flex flex-wrap gap-2">
        {canResend ? (
          <Button disabled={sending} onClick={onResend}>
            {t("quiz.page.resend")}
          </Button>
        ) : null}
        <Button variant="outline" onClick={onBack}>
          {t("quiz.page.backToQuiz")}
        </Button>
      </div>
    </section>
  );
}
