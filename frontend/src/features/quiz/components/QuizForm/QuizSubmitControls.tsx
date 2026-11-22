import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { QuestionView } from "../viewTypes";
import { SendConfirm } from "./SendConfirm";

interface Props {
  total: number;
  empties: QuestionView[];
  asking: boolean;
  disabled: boolean;
  onSend: () => void;
  onBack: () => void;
}

export function QuizSubmitControls({ total, empties, asking, disabled, onSend, onBack }: Props) {
  return (
    <>
      <p className="text-sm text-muted-foreground">
        {t("quiz.form.progress", { done: total - empties.length, total })}
      </p>
      {asking && empties.length > 0 ? (
        <SendConfirm
          ranks={empties.map((question) => question.rank)}
          disabled={disabled}
          onSend={onSend}
          onBack={onBack}
        />
      ) : (
        <Button type="submit" className="self-start" disabled={disabled}>
          {t("quiz.form.send")}
        </Button>
      )}
    </>
  );
}
