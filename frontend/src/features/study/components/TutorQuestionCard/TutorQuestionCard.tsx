import { useId, useState } from "react";
import { t } from "@/shared/i18n/t";
import { VoicePlayback } from "@/shared/voice";
import type { TutorOptionView } from "../viewTypes";
import { AnswerForm } from "./AnswerForm";

const cardClass =
  "rounded-xl border-2 border-primary bg-card px-4 py-3 motion-safe:animate-in motion-safe:fade-in motion-safe:duration-200";

interface TutorQuestionCardProps {
  question: string;
  /**
   * The interruption's options (`stuck`, `skip`). The « stuck » label carries the count of
   * hints (« Je bloque (1/3) », then « Voir la solution »): the card shows it as-is and
   * counts nothing; the back end remains the only source.
   */
  options: TutorOptionView[];
  answered: boolean;
  /** An answer is under way: nothing can be changed any more. */
  disabled: boolean;
  onAnswer: (text: string) => void;
  onStuck: () => void;
  onSkip: () => void;
}

/**
 * Tutor's question (section, exercise or final question): an answer field, « Je bloque »
 * (hint, then solution) and « Passer ». Once answered, the card folds: the question, the
 * answer typed in this tab, read-only, and « Réponse envoyée ».
 */
export function TutorQuestionCard({
  question,
  options,
  answered,
  disabled,
  onAnswer,
  onStuck,
  onSkip,
}: TutorQuestionCardProps) {
  const questionId = useId();
  const [sent, setSent] = useState<string | null>(null);

  if (answered) {
    return (
      <section aria-labelledby={questionId} className={cardClass}>
        <p id={questionId} className="font-medium">
          {question}
        </p>
        {sent ? (
          <p className="mt-2 whitespace-pre-wrap rounded-lg bg-muted px-3 py-2 text-sm">{sent}</p>
        ) : null}
        <p className="mt-2 text-sm text-muted-foreground">{t("study.tutor.answered")}</p>
      </section>
    );
  }
  const labelOf = (value: string, fallback: string) =>
    options.find((option) => option.value === value)?.label ?? fallback;
  return (
    <section aria-labelledby={questionId} className={cardClass}>
      <p id={questionId} className="font-medium">
        {question}
      </p>
      {!disabled && <VoicePlayback text={question} />}
      <AnswerForm
        disabled={disabled}
        stuckLabel={labelOf("stuck", t("study.tutor.stuck"))}
        skipLabel={labelOf("skip", t("study.tutor.skip"))}
        onSubmit={(text) => {
          setSent(text);
          onAnswer(text);
        }}
        onStuck={onStuck}
        onSkip={onSkip}
      />
    </section>
  );
}
