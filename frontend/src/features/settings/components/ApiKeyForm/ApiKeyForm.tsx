import { useId, useRef, useState, type FormEvent } from "react";
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

/**
 * Saisie d'une clé : champ masqué, jamais prérempli, vidé une fois la clé enregistrée.
 * Le champ est non contrôlé : un champ contrôlé recopie sa valeur dans l'attribut HTML `value`,
 * donc la clé serait lisible dans le DOM (copie du HTML, extensions, sélecteurs CSS). Seul un
 * booléen (« y a-t-il du texte ? ») passe par l'état ; la clé n'est lue qu'à l'envoi.
 */
export function ApiKeyForm({ providerLabel, pending, onSave }: ApiKeyFormProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [hasText, setHasText] = useState(false);
  const inputId = useId();

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const input = inputRef.current;
    const typed = input?.value.trim() ?? "";
    if (!input || !typed || pending) return;
    try {
      await onSave(typed);
      input.value = "";
      setHasText(false);
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
        // « new-password » décourage les gestionnaires de mots de passe mieux que « off ».
        autoComplete="new-password"
        autoCapitalize="off"
        spellCheck={false}
        ref={inputRef}
        onChange={(event) => setHasText(event.target.value.trim() !== "")}
        className={fieldClass}
      />
      <Button type="submit" disabled={pending || !hasText}>
        {t("settings.keys.save")}
      </Button>
    </form>
  );
}
