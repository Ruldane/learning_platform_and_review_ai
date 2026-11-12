import { useState } from "react";
import type { FormEvent } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { NewTaskInput, WeekView } from "../viewTypes";
import { AddTaskFields } from "./AddTaskFields";
import { EMPTY_DRAFT, parseTask } from "./parseTask";
import type { TaskDraft, TaskErrors } from "./parseTask";

interface AddTaskFormProps {
  weeks: WeekView[];
  /** Une `Promise` rejetée garde la saisie : l'erreur du serveur s'affiche par `error`. */
  onAdd: (input: NewTaskInput) => void | Promise<unknown>;
  /** Refus venu du serveur (semaine au-delà de son plafond, par exemple). */
  error?: string | null;
}

/** Formulaire d'ajout d'une tâche : titre, type, durée de 15 à 120 minutes, critère de fin, jour. */
export function AddTaskForm({ weeks, onAdd, error }: AddTaskFormProps) {
  const [draft, setDraft] = useState<TaskDraft>(EMPTY_DRAFT);
  const [errors, setErrors] = useState<TaskErrors>({});
  const [busy, setBusy] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (busy) return;
    const parsed = parseTask(draft);
    setErrors(parsed.errors);
    if (!parsed.input) return;
    setBusy(true);
    try {
      await onAdd(parsed.input);
      setDraft({ ...EMPTY_DRAFT, type: draft.type, plannedDate: draft.plannedDate });
    } catch {
      // Le refus s'affiche par `error` ; la saisie reste en place pour être corrigée.
    } finally {
      setBusy(false);
    }
  }

  return (
    <form
      noValidate
      aria-label={t("program.add.heading")}
      onSubmit={(event) => void handleSubmit(event)}
      className="flex flex-col gap-3 rounded-xl border bg-card p-4"
    >
      <h3 className="text-base font-semibold">{t("program.add.heading")}</h3>
      <AddTaskFields
        draft={draft}
        errors={errors}
        weeks={weeks}
        disabled={busy}
        onChange={(patch) => setDraft((current) => ({ ...current, ...patch }))}
      />
      {error && (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      )}
      <Button type="submit" disabled={busy} className="self-start">
        {t("program.add.submit")}
      </Button>
    </form>
  );
}
