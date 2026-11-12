import { useState } from "react";
import type { FormEvent } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { GoalInput } from "../viewTypes";
import { GoalFields } from "./GoalFields";
import { parseGoal, type GoalDraft, type GoalErrors } from "./parseGoal";

interface GoalFormProps {
  onSubmit: (input: GoalInput) => void;
  /** L'objectif part : le formulaire est verrouillé. */
  busy: boolean;
}

const EMPTY: GoalDraft = { text: "", targetRole: "", deadline: "", weeklyHours: "" };

/**
 * Nouvel objectif (SPEC 3.1, étape 1) : ce que January veut apprendre (5 à 500 caractères), le poste
 * visé, une échéance à venir et ses heures par semaine (1 à 40). Valide à l'envoi, champ par champ.
 */
export function GoalForm({ onSubmit, busy }: GoalFormProps) {
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
      <Button type="submit" disabled={busy} className="self-start">
        {busy ? t("learning.goals.form.busy") : t("learning.goals.form.submit")}
      </Button>
    </form>
  );
}
