import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { InlineError } from "@/shared/ui/states/InlineError";

interface GradingFailedProps {
  /** Les réponses sont gardées : on peut les renvoyer. `false` après un rechargement de la page. */
  canResend: boolean;
  /** Message d'un renvoi refusé. */
  error: string | null;
  /** Un renvoi est en route : le bouton est coupé. */
  sending: boolean;
  onResend: () => void;
  onBack: () => void;
}

/** La correction a échoué : renvoyer les mêmes réponses, ou revenir au quiz. */
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
