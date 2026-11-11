import { useId, useState, type FormEvent } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { fieldClass } from "@/shared/ui/fieldClass";

interface ApiKeyFormProps {
  /** Nom du fournisseur, pour l'étiquette du champ. */
  providerLabel: string;
  pending: boolean;
  /** Peut renvoyer une promesse : si elle échoue, la saisie est conservée pour réessayer. */
  onSave: (key: string) => void | Promise<void>;
}

/** Saisie d'une clé : champ masqué, jamais prérempli, vidé une fois la clé enregistrée. */
export function ApiKeyForm({ providerLabel, pending, onSave }: ApiKeyFormProps) {
  const [value, setValue] = useState("");
  const inputId = useId();
  const typed = value.trim();

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!typed || pending) return;
    try {
      await onSave(typed);
      setValue("");
    } catch {
      // L'écran affiche l'erreur ; on garde la saisie pour que l'utilisateur puisse réessayer.
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex gap-2">
      <label htmlFor={inputId} className="sr-only">
        {t("settings.keys.inputLabel", { provider: providerLabel })}
      </label>
      <input
        id={inputId}
        type="password"
        autoComplete="off"
        autoCapitalize="off"
        spellCheck={false}
        value={value}
        onChange={(event) => setValue(event.target.value)}
        className={fieldClass}
      />
      <Button type="submit" disabled={pending || !typed}>
        {t("settings.keys.save")}
      </Button>
    </form>
  );
}
