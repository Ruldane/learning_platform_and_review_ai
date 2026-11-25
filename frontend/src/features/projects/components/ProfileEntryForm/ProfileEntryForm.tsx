import { useState, type FormEvent } from "react";
import { t } from "@/shared/i18n/t";
import type { ProfileEntryView } from "../viewTypes";
import { cleanEntry, type EntryErrors } from "./cleanEntry";
import { EntryField } from "./EntryField";
import { EntryFooter } from "./EntryFooter";

interface ProfileEntryFormProps {
  /** The entry proposed from the project; editable before adding. */
  entry: ProfileEntryView;
  /** The entry is already in the master profile. */
  added: boolean;
  /** The version of the master profile that received the entry (shown once added). */
  version?: number | null;
  /** Receives the cleaned entry: name and description trimmed, empty achievement lines removed. */
  onAdd: (entry: ProfileEntryView) => void;
  /** The addition is in progress. */
  busy?: boolean;
}

/**
 * Adds a project to the master profile. Nothing enters without January's click: the reminder is
 * written, and the entry sent is cleaned (the server refuses an empty achievement line).
 * The form reads `entry` only once: the page gives it a `key` that follows the entry.
 */
export function ProfileEntryForm(props: ProfileEntryFormProps) {
  const { entry, added, version = null, onAdd, busy = false } = props;
  const [name, setName] = useState(entry.name);
  const [description, setDescription] = useState(entry.description);
  const [lines, setLines] = useState(entry.achievements.join("\n"));
  const [errors, setErrors] = useState<EntryErrors>({});
  const locked = added || busy;

  // The form is never submitted: Enter in « Nom du projet » adds nothing to the master profile
  // (a write that cannot be undone); only the « Ajouter » button calls `add`.
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
