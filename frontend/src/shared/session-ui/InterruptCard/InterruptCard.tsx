import { useId, useState } from "react";
import type { InterruptPayload } from "@/shared/realtime/types";
import { VoicePlayback } from "@/shared/voice";
import { AnswerInputs } from "./AnswerInputs";
import { FoldedCard } from "./FoldedCard";

const cardClass =
  "rounded-xl border-2 border-primary bg-card px-4 py-3 motion-safe:animate-in motion-safe:fade-in motion-safe:duration-200";

interface InterruptCardProps {
  interrupt: InterruptPayload;
  answered: boolean;
  disabled?: boolean;
  voice?: boolean;
  /**
   * An option sends its value; fields send `{ answers: { id: text } }` (and an option
   * clicked after typing sends these answers, never lost); otherwise the free text.
   */
  onAnswer: (value: unknown) => void;
  /**
   * Value sent when an option is clicked while fields are filled in; by default
   * `{ answers }`. Used when the option must take precedence (« Accepter » with a note).
   */
  optionWithAnswers?: (value: string, answers: Record<string, string>) => unknown;
}

/**
 * Team question, shown as a card in the feed (never `window.confirm`). The
 * options are buttons; with no option or field, a free-text field appears; with fields
 * (several questions), one field per question and a « Répondre » button. Keyboard:
 * focus lands on the first option (or the first field), Tab moves from one to the other.
 * Once answered, the card folds: the question, « Réponse envoyée » and the answers typed
 * in this tab, read-only, with no more fields, options or free text.
 */
export function InterruptCard({
  interrupt,
  answered,
  disabled = false,
  voice = false,
  onAnswer,
  optionWithAnswers,
}: InterruptCardProps) {
  const questionId = useId();
  const fields = interrupt.fields ?? [];
  const [draft, setDraft] = useState<Record<string, string>>({});

  if (interrupt.kind === "mcp_model") return <p>{interrupt.question}</p>;
  if (answered) {
    return (
      <FoldedCard
        questionId={questionId}
        question={interrupt.question}
        className={cardClass}
        fields={fields}
        draft={draft}
      />
    );
  }
  return (
    <section aria-labelledby={questionId} className={cardClass}>
      <p id={questionId} className="font-medium">
        {interrupt.question}
      </p>
      {voice && !disabled && <VoicePlayback text={interrupt.question} />}
      <AnswerInputs
        questionId={questionId}
        fields={fields}
        options={interrupt.options ?? []}
        draft={draft}
        onDraft={setDraft}
        disabled={disabled}
        voice={voice}
        onAnswer={onAnswer}
        optionWithAnswers={optionWithAnswers}
      />
    </section>
  );
}
