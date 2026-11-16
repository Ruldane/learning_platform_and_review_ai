import { useState, type FormEvent } from "react";
import { t } from "@/shared/i18n/t";
import type { ProfileEntryView } from "../viewTypes";
import { cleanEntry, type EntryErrors } from "./cleanEntry";
import { EntryField } from "./EntryField";
import { EntryFooter } from "./EntryFooter";

interface ProfileEntryFormProps {
  /** L'entrée proposée à partir du projet ; modifiable avant l'ajout. */
  entry: ProfileEntryView;
  /** L'entrée est déjà dans le profil maître. */
  added: boolean;
  /** Reçoit l'entrée nettoyée : nom et description coupés, lignes de réalisation vides retirées. */
  onAdd: (entry: ProfileEntryView) => void;
  /** L'ajout est en cours. */
  busy?: boolean;
}

/**
 * L'ajout d'un projet au profil maître. Rien n'y entre sans le clic de January : le rappel est
 * écrit, et l'entrée envoyée est nettoyée (le serveur refuse une ligne de réalisation vide).
 */
export function ProfileEntryForm({ entry, added, onAdd, busy = false }: ProfileEntryFormProps) {
  const [name, setName] = useState(entry.name);
  const [description, setDescription] = useState(entry.description);
  const [lines, setLines] = useState(entry.achievements.join("\n"));
  const [errors, setErrors] = useState<EntryErrors>({});
  const locked = added || busy;

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (locked) return;
    const cleaned = cleanEntry(name, description, lines);
    setErrors(cleaned.errors);
    if (Object.keys(cleaned.errors).length === 0) onAdd(cleaned.entry);
  };

  return (
    <form
      onSubmit={submit}
      noValidate
      aria-label={t("projects.entry.label")}
      aria-busy={busy}
      className="flex flex-col gap-3 rounded-xl border bg-card p-4"
    >
      <EntryField
        label={t("projects.entry.name")}
        value={name}
        disabled={locked}
        error={errors.name}
        onChange={setName}
      />
      <EntryField
        label={t("projects.entry.description")}
        value={description}
        disabled={locked}
        error={errors.description}
        rows={3}
        onChange={setDescription}
      />
      <EntryField
        label={t("projects.entry.achievements")}
        hint={t("projects.entry.achievementsHint")}
        value={lines}
        disabled={locked}
        error={errors.achievements}
        rows={4}
        onChange={setLines}
      />
      <EntryFooter added={added} busy={busy} locked={locked} />
    </form>
  );
}
