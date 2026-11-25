import { useId } from "react";
import { t } from "@/shared/i18n/t";
import type { QuestionView } from "../viewTypes";
import { TextForm } from "./TextForm";

interface CaptureTextCardProps {
  interrupt: QuestionView;
  answered: boolean;
  disabled: boolean;
  /** Receives `{ answers: { text } }`, or the value of the « Abandonner » option. */
  onAnswer: (value: unknown) => void;
  /** The typed text, kept outside the dialog; cleared on send and on « Abandonner ». */
  draft: string;
  onDraft: (text: string) => void;
}

/**
 * The « colle le texte » question for an unreadable link (`capture_text`): a text area of 20,000
 * characters at most, and « Abandonner ». Abandoning never sends the typed text: that is why
 * the shared question card is not used here. Once answered, the card collapses.
 */
export function CaptureTextCard(props: CaptureTextCardProps) {
  const { interrupt, answered, disabled, onAnswer, draft, onDraft } = props;
  const id = useId();
  return (
    <section aria-labelledby={id} className="rounded-xl border-2 border-primary bg-card px-4 py-3">
      <p id={id} className="font-medium">
        {interrupt.question}
      </p>
      {answered ? (
        <p className="mt-1 text-sm text-muted-foreground">{t("capture.textCard.answered")}</p>
      ) : (
        <TextForm
          interrupt={interrupt}
          disabled={disabled}
          onAnswer={onAnswer}
          text={draft}
          onText={onDraft}
        />
      )}
    </section>
  );
}
