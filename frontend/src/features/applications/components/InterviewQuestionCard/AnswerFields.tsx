import { t } from "@/shared/i18n/t";
import { FreeTextAnswer } from "@/shared/session-ui";
import { Button } from "@/shared/ui/button";
import { VoicePlayback } from "@/shared/voice";

/** The limit of an answer (`max_length` of the `interview_answer` question). */
const MAX_ANSWER = 4000;

interface AnswerFieldsProps {
  disabled: boolean;
  stopLabel: string | null;
  onAnswer: (text: string) => void;
  onStop: () => void;
  question?: string;
}

/** The written answer field, the length limit and « Terminer l'entretien » (if the server offers
 * it). */
export function AnswerFields({
  disabled,
  stopLabel,
  onAnswer,
  onStop,
  question,
}: AnswerFieldsProps) {
  return (
    <>
      {question && !disabled && <VoicePlayback text={question} />}
      <FreeTextAnswer
        multiline
        voice
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
