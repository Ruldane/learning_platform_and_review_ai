import { t } from "@/shared/i18n/t";
import { FreeTextAnswer } from "@/shared/session-ui";
import { Button } from "@/shared/ui/button";

/** La limite d'une réponse (`max_length` de la question `interview_answer`). */
const MAX_ANSWER = 4000;

interface AnswerFieldsProps {
  disabled: boolean;
  stopLabel: string | null;
  onAnswer: (text: string) => void;
  onStop: () => void;
}

/** Le champ de réponse écrite, la limite de longueur et « Terminer l'entretien » (si le serveur l'offre). */
export function AnswerFields({ disabled, stopLabel, onAnswer, onStop }: AnswerFieldsProps) {
  return (
    <>
      <FreeTextAnswer
        multiline
        maxLength={MAX_ANSWER}
        label={t("applications.interviewRun.answerLabel")}
        disabled={disabled}
        onSubmit={onAnswer}
      />
      <p className="mt-2 text-sm text-muted-foreground">{t("applications.interviewRun.hint")}</p>
      {stopLabel === null ? null : (
        <div className="mt-3 flex flex-col items-start gap-1 border-t pt-3">
          <Button type="button" variant="outline" disabled={disabled} onClick={onStop}>
            {stopLabel}
          </Button>
          <p className="text-sm text-muted-foreground">{t("applications.interviewRun.stopHint")}</p>
        </div>
      )}
    </>
  );
}
