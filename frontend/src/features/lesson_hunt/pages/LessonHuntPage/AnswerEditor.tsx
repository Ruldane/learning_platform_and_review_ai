import { useState } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";

interface Props {
  initial: string[] | null;
  submitting: boolean;
  submit: (values: string[]) => void;
}

export function AnswerEditor({ initial, submitting, submit }: Props) {
  const [first, setFirst] = useState(initial?.[0] ?? "");
  const [second, setSecond] = useState(initial?.[1] ?? "");
  const valid = first.trim().length >= 4 && second.trim().length >= 4;
  const fields = [
    { id: "first", value: first, set: setFirst, title: t("lessonHunt.first") },
    { id: "second", value: second, set: setSecond, title: t("lessonHunt.second") },
  ];
  return (
    <form
      className="flex flex-col gap-4"
      onSubmit={(event) => {
        event.preventDefault();
        if (valid && !submitting) submit([first.trim(), second.trim()]);
      }}
    >
      {fields.map(({ id, value, set, title }) => (
        <label key={id} className="flex flex-col gap-1 text-sm font-medium">
          {title}
          <textarea
            className="min-h-24 rounded-md border border-input bg-background p-2 focus-visible:ring-2 focus-visible:ring-ring"
            value={value}
            onChange={(event) => set(event.target.value)}
            maxLength={2400}
            required
            disabled={submitting}
          />
        </label>
      ))}
      <Button type="submit" className="w-fit" disabled={!valid || submitting}>
        {t("lessonHunt.submit")}
      </Button>
    </form>
  );
}
