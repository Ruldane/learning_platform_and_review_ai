import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";

interface SendConfirmProps {
  /** The numbers of the questions left unanswered. */
  ranks: number[];
  disabled: boolean;
  onSend: () => void;
  onBack: () => void;
}

/** The confirmation in the card when some questions are empty (never `window.confirm`). */
export function SendConfirm({ ranks, disabled, onSend, onBack }: SendConfirmProps) {
  return (
    <div className="flex flex-col gap-2 rounded-xl border border-amber-700/40 bg-amber-50 p-3 text-amber-900">
      <p role="alert" className="text-sm">
        {t(ranks.length === 1 ? "quiz.form.confirm.one" : "quiz.form.confirm.many", {
          count: ranks.length,
          ranks: ranks.join(", "),
        })}
      </p>
      <div className="flex flex-wrap gap-2">
        <Button type="button" disabled={disabled} onClick={onSend}>
          {t("quiz.form.confirm.send")}
        </Button>
        <Button type="button" variant="outline" autoFocus onClick={onBack}>
          {t("quiz.form.confirm.back")}
        </Button>
      </div>
    </div>
  );
}
