import { useState } from "react";
import type { FormEvent, ReactNode } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { GoalInput } from "../viewTypes";
import { GoalFields } from "./GoalFields";
import { parseGoal, type GoalDraft, type GoalErrors } from "./parseGoal";

interface GoalFormProps {
  onSubmit: (input: GoalInput) => void;
  launchMenu?: ReactNode;
  /** The goal is being sent: the form is locked. */
  busy: boolean;
}

const EMPTY: GoalDraft = { text: "", targetRole: "", deadline: "", weeklyHours: "" };

/**
 * New goal (SPEC 3.1, step 1): what January wants to learn (5 to 500 characters), the role
 * targeted, an upcoming deadline and hours per week (1 to 40). Validated on submit, field by field.
 */
export function GoalForm({ onSubmit, busy, launchMenu }: GoalFormProps) {
  const [draft, setDraft] = useState<GoalDraft>(EMPTY);
  const [errors, setErrors] = useState<GoalErrors>({});

  const change = (field: keyof GoalDraft, value: string) => {
    setDraft({ ...draft, [field]: value });
    setErrors({ ...errors, [field]: undefined });
  };

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (busy) return;
    const parsed = parseGoal(draft);
    if ("errors" in parsed) return setErrors(parsed.errors);
    onSubmit(parsed.input);
  };

  return (
    <form
      onSubmit={submit}
      noValidate
      aria-label={t("learning.goals.form.label")}
      className="flex flex-col gap-4 rounded-xl border border-border bg-card px-4 py-4"
    >
      <GoalFields draft={draft} errors={errors} disabled={busy} onChange={change} />
      {launchMenu}
      <Button type="submit" disabled={busy} className="self-start">
        {busy ? t("learning.goals.form.busy") : t("learning.goals.form.submit")}
      </Button>
    </form>
  );
}
