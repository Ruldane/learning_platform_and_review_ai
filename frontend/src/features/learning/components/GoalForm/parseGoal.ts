import { t } from "@/shared/i18n/t";
import type { GoalInput } from "../viewTypes";

/** Ce que January a tapé, champ par champ. */
export interface GoalDraft {
  text: string;
  targetRole: string;
  deadline: string;
  weeklyHours: string;
}

export type GoalErrors = Partial<Record<keyof GoalDraft, string>>;

export const TEXT_MIN = 5;
export const TEXT_MAX = 500;
export const ROLE_MAX = 120;
const HOURS_MIN = 1;
const HOURS_MAX = 40;

/** Aujourd'hui, à l'heure locale, au format `AAAA-MM-JJ` (celui d'un champ date). */
export function todayIso(now: Date = new Date()): string {
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${now.getFullYear()}-${month}-${day}`;
}

function textError(text: string): string | undefined {
  if (text.length < TEXT_MIN) return t("learning.goals.form.errors.textShort");
  return text.length > TEXT_MAX ? t("learning.goals.form.errors.textLong") : undefined;
}

function hoursError(hours: string): string | undefined {
  if (hours === "") return undefined;
  const value = Number(hours);
  const valid = /^\d+$/.test(hours) && value >= HOURS_MIN && value <= HOURS_MAX;
  return valid ? undefined : t("learning.goals.form.errors.weeklyHours");
}

/** Valide la saisie (texte de 5 à 500, poste ≤ 120, échéance à venir, 1 à 40 h) ; les champs vides facultatifs deviennent `null`. */
export function parseGoal(
  draft: GoalDraft,
  today: string = todayIso(),
): { input: GoalInput } | { errors: GoalErrors } {
  const text = draft.text.trim();
  const role = draft.targetRole.trim();
  const errors: GoalErrors = {
    text: textError(text),
    targetRole: role.length > ROLE_MAX ? t("learning.goals.form.errors.targetRoleLong") : undefined,
    deadline:
      draft.deadline !== "" && draft.deadline <= today
        ? t("learning.goals.form.errors.deadlinePast")
        : undefined,
    weeklyHours: hoursError(draft.weeklyHours.trim()),
  };
  if (Object.values(errors).some((message) => message !== undefined)) {
    return { errors: Object.fromEntries(Object.entries(errors).filter(([, v]) => v)) };
  }
  return {
    input: {
      text,
      targetRole: role === "" ? null : role,
      deadline: draft.deadline === "" ? null : draft.deadline,
      weeklyHours: draft.weeklyHours.trim() === "" ? null : Number(draft.weeklyHours),
    },
  };
}
