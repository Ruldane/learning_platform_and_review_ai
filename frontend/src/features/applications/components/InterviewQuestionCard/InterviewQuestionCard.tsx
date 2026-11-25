import { useId, useState } from "react";
import { t } from "@/shared/i18n/t";
import { AnswerFields } from "./AnswerFields";
import { SentLine, type Sent } from "./SentLine";

interface InterviewQuestionCardProps {
  /** The rank of the main question (from 1), `null` until it is known. */
  number: number | null;
  total: number;
  /** This is the follow-up to question `number`. */
  followUp: boolean;
  answered: boolean;
  disabled: boolean;
  /** The label of the server's « terminer » option; `null`: no option. */
  stopLabel: string | null;
  onAnswer: (text: string) => void;
  onStop: () => void;
  question?: string;
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
 * The question asked by the interviewer, with its written answer field (a text area, where
 * focus lands) and « Terminer l'entretien ». The question itself is the bubble just above.
 * Once answered, the card folds: « Réponse envoyée » and what January wrote.
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
          question={props.question}
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
