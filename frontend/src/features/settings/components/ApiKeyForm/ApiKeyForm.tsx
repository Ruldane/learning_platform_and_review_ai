import { useId, useRef, useState, type FormEvent } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { fieldClass } from "@/shared/ui/fieldClass";

interface ApiKeyFormProps {
  /** Provider name, for the field label. */
  providerLabel: string;
  pending: boolean;
  /** May return a promise: if it fails, the input is kept so the user can retry. */
  onSave: (key: string) => void | Promise<void>;
}

/**
 * Key input: masked field, never pre-filled, cleared once the key is saved.
 * The field is uncontrolled: a controlled field copies its value into the HTML `value` attribute,
 * so the key would be readable in the DOM (HTML copy, extensions, CSS selectors). Only a
 * boolean ("is there any text?") goes through state; the key is read only when sending.
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
      // The screen shows the error; the input is kept so the user can retry.
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
        // "new-password" discourages password managers better than "off".
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
