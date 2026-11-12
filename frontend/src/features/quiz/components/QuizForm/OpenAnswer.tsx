import { t } from "@/shared/i18n/t";
import { cn } from "@/shared/lib/utils";
import { fieldClass } from "@/shared/ui/fieldClass";

/** Même plafond que le champ `text` d'une réponse côté back. */
const MAX_ANSWER_LENGTH = 4000;

interface OpenAnswerProps {
  rank: number;
  rows: number;
  text: string;
  disabled: boolean;
  onText: (text: string) => void;
}

/** La zone de texte des réponses ouvertes (courte, lecture de code, « explique »). */
export function OpenAnswer({ rank, rows, text, disabled, onText }: OpenAnswerProps) {
  return (
    <label className="mt-2 flex flex-col gap-1">
      <span className="sr-only">{t("quiz.form.answerLabel", { rank })}</span>
      <textarea
        value={text}
        disabled={disabled}
        maxLength={MAX_ANSWER_LENGTH}
        rows={rows}
        onChange={(event) => onText(event.target.value)}
        className={cn(fieldClass, "h-auto min-h-16 py-1.5")}
      />
    </label>
  );
}
