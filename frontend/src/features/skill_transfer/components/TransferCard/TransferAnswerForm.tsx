import { useId, useState } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { fieldClass } from "@/shared/ui/fieldClass";
import type { AnswerView } from "../viewTypes";

interface Props {
  view: AnswerView;
  busy: boolean;
  onAnswer: (answer: string) => void;
}

export function TransferAnswerForm({ view, busy, onAnswer }: Props) {
  const id = useId();
  const [draft, setDraft] = useState(view.text);
  const answer = view.retry ? view.text : draft;
  return (
    <form
      className="grid gap-3"
      onSubmit={(event) => {
        event.preventDefault();
        if (answer.trim()) onAnswer(answer);
      }}
    >
      <h4 className="font-semibold">{view.title}</h4>
      <p className="whitespace-pre-wrap">{view.question}</p>
      <label htmlFor={id} className="text-sm font-medium">{t("skillTransfer.answer")}</label>
      <textarea
        id={id}
        className={fieldClass}
        rows={5}
        maxLength={8000}
        readOnly={view.retry}
        value={answer}
        onChange={(event) => setDraft(event.target.value)}
        required
      />
      <Button className="justify-self-start" type="submit" disabled={!answer.trim() || busy}>
        {t(view.retry ? "skillTransfer.retryAnswer" : "skillTransfer.submit")}
      </Button>
    </form>
  );
}
