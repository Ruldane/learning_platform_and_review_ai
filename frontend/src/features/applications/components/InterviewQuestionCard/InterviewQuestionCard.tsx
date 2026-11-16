import { useId, useState } from "react";
import { t } from "@/shared/i18n/t";
import { AnswerFields } from "./AnswerFields";
import { SentLine, type Sent } from "./SentLine";

interface InterviewQuestionCardProps {
  /** Le rang de la question principale (à partir de 1), `null` tant qu'on ne le connaît pas. */
  number: number | null;
  total: number;
  /** C'est la relance de la question `number`. */
  followUp: boolean;
  answered: boolean;
  disabled: boolean;
  /** L'étiquette de l'option « terminer » du serveur ; `null` : pas d'option. */
  stopLabel: string | null;
  onAnswer: (text: string) => void;
  onStop: () => void;
}

function heading(number: number | null, total: number, followUp: boolean): string {
  if (number === null) {
    return t(
      followUp
        ? "applications.interviewRun.followUpBare"
        : "applications.interviewRun.questionBare",
    );
  }
  const key = followUp
    ? "applications.interviewRun.followUp"
    : "applications.interviewRun.question";
  return t(key, { number, total });
}

/**
 * La question posée par l'intervieweur, avec son champ de réponse écrite (une zone de texte, le
 * focus y arrive) et « Terminer l'entretien ». La question elle-même est la bulle juste au-dessus.
 * Une fois répondue, la carte se replie : « Réponse envoyée » et ce que January a écrit.
 */
export function InterviewQuestionCard(props: InterviewQuestionCardProps) {
  const { number, total, followUp, answered, disabled, stopLabel, onAnswer, onStop } = props;
  const titleId = useId();
  const [sent, setSent] = useState<Sent | null>(null);

  return (
    <section
      aria-labelledby={titleId}
      className="rounded-xl border-2 border-primary bg-card px-4 py-3 motion-safe:animate-in motion-safe:fade-in motion-safe:duration-200"
    >
      <h2 id={titleId} className="font-medium">
        {heading(number, total, followUp)}
      </h2>
      {answered ? (
        <div className="mt-2 flex flex-col gap-1 text-sm">
          <p className="text-muted-foreground">{t("applications.interviewRun.sent")}</p>
          <SentLine sent={sent} />
        </div>
      ) : (
        <AnswerFields
          disabled={disabled}
          stopLabel={stopLabel}
          onAnswer={(text) => {
            setSent({ kind: "answer", text });
            onAnswer(text);
          }}
          onStop={() => {
            setSent({ kind: "stop" });
            onStop();
          }}
        />
      )}
    </section>
  );
}
