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
  /** La version du profil maître qui a reçu l'entrée (dite une fois ajoutée). */
  version?: number | null;
  /** Reçoit l'entrée nettoyée : nom et description coupés, lignes de réalisation vides retirées. */
  onAdd: (entry: ProfileEntryView) => void;
  /** L'ajout est en cours. */
  busy?: boolean;
}

/**
 * L'ajout d'un projet au profil maître. Rien n'y entre sans le clic de January : le rappel est
 * écrit, et l'entrée envoyée est nettoyée (le serveur refuse une ligne de réalisation vide).
 * Le formulaire ne lit `entry` qu'une fois : la page lui donne une `key` qui suit l'entrée.
 */
export function ProfileEntryForm(props: ProfileEntryFormProps) {
  const { entry, added, version = null, onAdd, busy = false } = props;
  const [name, setName] = useState(entry.name);
  const [description, setDescription] = useState(entry.description);
  const [lines, setLines] = useState(entry.achievements.join("\n"));
  const [errors, setErrors] = useState<EntryErrors>({});
  const locked = added || busy;

  // Le formulaire ne se soumet jamais : Entrée dans « Nom du projet » n'ajoute rien au profil
  // maître (une écriture qui ne s'annule pas) ; seul le bouton « Ajouter » appelle `add`.
  const add = () => {
    if (locked) return;
    const cleaned = cleanEntry(name, description, lines);
    setErrors(cleaned.errors);
    if (Object.keys(cleaned.errors).length === 0) onAdd(cleaned.entry);
  };
  const ignoreEnter = (event: FormEvent) => event.preventDefault();

  return (
    <form
      onSubmit={ignoreEnter}
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
      <EntryFooter added={added} version={version} busy={busy} onAdd={add} />
    </form>
  );
}
