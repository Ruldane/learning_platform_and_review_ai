import { useState } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { ExerciseDraft } from "../viewTypes";
import { TextField } from "./TextField";

interface ManualExerciseFormProps {
  pending: boolean;
  /** True when the exercise is added: the fields are then cleared. */
  onCreate: (draft: ExerciseDraft) => Promise<boolean>;
}

const EMPTY: ExerciseDraft = { title: "", statement: "", starter: "", tests: "" };

/** Write an exercise by hand: title, statement, starter code and, optionally, pytest tests. */
export function ManualExerciseForm({ pending, onCreate }: ManualExerciseFormProps) {
  const [draft, setDraft] = useState<ExerciseDraft>(EMPTY);
  const set = (key: keyof ExerciseDraft) => (value: string) =>
    setDraft((current) => ({ ...current, [key]: value }));
  const ready = draft.title.trim() !== "" && draft.statement.trim() !== "";
  return (
    <form
      className="flex flex-col gap-3"
      onSubmit={async (event) => {
        event.preventDefault();
        if (ready && !pending && (await onCreate(draft))) setDraft(EMPTY);
      }}
    >
      <h3 className="font-medium">{t("ide.form.manual")}</h3>
      <TextField
        label={t("ide.form.name")}
        value={draft.title}
        maxLength={120}
        onChange={set("title")}
      />
      <TextField
        label={t("ide.form.statement")}
        value={draft.statement}
        rows={4}
        maxLength={8000}
        onChange={set("statement")}
      />
      <TextField
        label={t("ide.form.starter")}
        value={draft.starter}
        rows={5}
        mono
        onChange={set("starter")}
      />
      <TextField
        label={t("ide.form.tests")}
        value={draft.tests}
        rows={4}
        mono
        hint={t("ide.form.testsHint")}
        onChange={set("tests")}
      />
      <Button type="submit" className="self-start" disabled={!ready} aria-disabled={pending}>
        {t("ide.form.create")}
      </Button>
    </form>
  );
}
