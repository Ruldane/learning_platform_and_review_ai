import { t } from "@/shared/i18n/t";
import { cn } from "@/shared/lib/utils";
import { fieldClass } from "@/shared/ui/fieldClass";

/** Same cap as the `text` field of an answer on the back end. */
const MAX_ANSWER_LENGTH = 4000;

interface OpenAnswerProps {
  rank: number;
  rows: number;
  text: string;
  disabled: boolean;
  onText: (text: string) => void;
}

/** The free-text answer box (short, code reading, « explique »). */
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
