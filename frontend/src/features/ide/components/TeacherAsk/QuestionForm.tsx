import { useId, useState } from "react";
import { t } from "@/shared/i18n/t";
import { cn } from "@/shared/lib/utils";
import { Button } from "@/shared/ui/button";
import { fieldClass } from "@/shared/ui/fieldClass";

interface QuestionFormProps {
  busy: boolean;
  onQuestion: (question: string) => void;
}

/** Le champ de question : jamais envoyée vide, vidé une fois partie. */
export function QuestionForm({ busy, onQuestion }: QuestionFormProps) {
  const fieldId = useId();
  const [question, setQuestion] = useState("");
  const empty = question.trim() === "";
  return (
    <form
      className="flex flex-col gap-2"
      onSubmit={(event) => {
        event.preventDefault();
        if (empty || busy) return;
        onQuestion(question.trim());
        setQuestion("");
      }}
    >
      <label htmlFor={fieldId} className="text-sm font-medium">
        {t("ide.teacher.question")}
      </label>
      <textarea
        id={fieldId}
        rows={2}
        value={question}
        maxLength={2000}
        onChange={(event) => setQuestion(event.target.value)}
        className={cn(fieldClass, "h-auto py-1.5")}
      />
      <Button type="submit" size="sm" className="self-start" disabled={empty} aria-disabled={busy}>
        {t("ide.teacher.questionAction")}
      </Button>
    </form>
  );
}
