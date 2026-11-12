import { t } from "@/shared/i18n/t";
import { TASK_MAX_MINUTES, TASK_MIN_MINUTES } from "../viewTypes";
import type { NewTaskInput, TaskType } from "../viewTypes";

export interface TaskDraft {
  title: string;
  type: TaskType;
  minutes: string;
  doneCriterion: string;
  plannedDate: string;
}

export type TaskErrors = Partial<
  Record<"title" | "minutes" | "doneCriterion" | "plannedDate", string>
>;

export const EMPTY_DRAFT: TaskDraft = {
  title: "",
  type: "lire",
  minutes: "30",
  doneCriterion: "",
  plannedDate: "",
};

/** Valide la saisie du formulaire d'ajout : titre, durée entière de 15 à 120, critère, jour. */
export function parseTask(draft: TaskDraft): { input?: NewTaskInput; errors: TaskErrors } {
  const errors: TaskErrors = {};
  const title = draft.title.trim();
  const doneCriterion = draft.doneCriterion.trim();
  const rawMinutes = draft.minutes.trim();
  const minutes = /^\d+$/.test(rawMinutes) ? Number(rawMinutes) : Number.NaN;
  if (!title) errors.title = t("program.add.errors.title");
  if (!(minutes >= TASK_MIN_MINUTES && minutes <= TASK_MAX_MINUTES)) {
    errors.minutes = t("program.add.errors.minutes");
  }
  if (!doneCriterion) errors.doneCriterion = t("program.add.errors.criterion");
  if (!draft.plannedDate) errors.plannedDate = t("program.add.errors.day");
  if (Object.keys(errors).length > 0) return { errors };
  return {
    errors,
    input: { title, type: draft.type, minutes, doneCriterion, plannedDate: draft.plannedDate },
  };
}
