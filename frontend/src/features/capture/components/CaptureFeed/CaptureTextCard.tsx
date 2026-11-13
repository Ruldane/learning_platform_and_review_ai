import { useId } from "react";
import { t } from "@/shared/i18n/t";
import type { QuestionView } from "../viewTypes";
import { TextForm } from "./TextForm";

interface CaptureTextCardProps {
  interrupt: QuestionView;
  answered: boolean;
  disabled: boolean;
  /** Reçoit `{ answers: { text } }`, ou la valeur de l'option « Abandonner ». */
  onAnswer: (value: unknown) => void;
}

/**
 * La question « colle le texte » d'un lien illisible (`capture_text`) : une zone de texte de 20 000
 * caractères au plus et « Abandonner ». Abandonner n'envoie jamais le texte saisi : c'est pourquoi
 * la carte commune des questions n'est pas utilisée ici. Répondue, la carte se replie.
 */
export function CaptureTextCard({ interrupt, answered, disabled, onAnswer }: CaptureTextCardProps) {
  const id = useId();
  return (
    <section aria-labelledby={id} className="rounded-xl border-2 border-primary bg-card px-4 py-3">
      <p id={id} className="font-medium">
        {interrupt.question}
      </p>
      {answered ? (
        <p className="mt-1 text-sm text-muted-foreground">{t("capture.textCard.answered")}</p>
      ) : (
        <TextForm interrupt={interrupt} disabled={disabled} onAnswer={onAnswer} />
      )}
    </section>
  );
}
