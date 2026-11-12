import { useId, useState } from "react";
import { t } from "@/shared/i18n/t";
import type { TutorOptionView } from "../viewTypes";
import { AnswerForm } from "./AnswerForm";

const cardClass =
  "rounded-xl border-2 border-primary bg-card px-4 py-3 motion-safe:animate-in motion-safe:fade-in motion-safe:duration-200";

interface TutorQuestionCardProps {
  question: string;
  /**
   * Les options de l'interruption (`stuck`, `skip`). Le libellé de « stuck » porte le compte des
   * indices (« Je bloque (1/3) », puis « Voir la solution ») : la carte l'affiche tel quel et ne
   * compte rien, le back reste la seule source.
   */
  options: TutorOptionView[];
  answered: boolean;
  /** Une réponse est en route : plus rien n'est modifiable. */
  disabled: boolean;
  onAnswer: (text: string) => void;
  onStuck: () => void;
  onSkip: () => void;
}

/**
 * Question du Tuteur (section, exercice ou question finale) : un champ de réponse, « Je bloque »
 * (indice, puis solution) et « Passer ». Une fois répondue, la carte se replie : la question, la
 * réponse saisie dans cet onglet en lecture seule et « Réponse envoyée ».
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
