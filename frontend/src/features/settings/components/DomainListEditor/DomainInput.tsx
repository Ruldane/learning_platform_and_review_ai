import { useId } from "react";
import type { KeyboardEvent } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { fieldClass } from "@/shared/ui/fieldClass";

interface DomainInputProps {
  draft: string;
  error: string | null;
  onDraftChange: (draft: string) => void;
  onAdd: () => void;
}

/**
 * Add field and its button. Enter adds without submitting a parent form: the field must not
 * wrap in its own `<form>`, which would be nested inside the settings form.
 */
export function DomainInput({ draft, error, onDraftChange, onAdd }: DomainInputProps) {
  const errorId = useId();
  function onKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key !== "Enter") return;
    event.preventDefault();
    onAdd();
  }
  return (
    <>
      <div className="flex gap-2">
        <input
          type="text"
          aria-label={t("settings.search.domains.add")}
          aria-invalid={error !== null}
          aria-describedby={error ? errorId : undefined}
          autoCapitalize="off"
          autoComplete="off"
          spellCheck={false}
          value={draft}
          onChange={(event) => onDraftChange(event.target.value)}
          onKeyDown={onKeyDown}
          className={fieldClass}
        />
        <Button type="button" variant="outline" onClick={onAdd}>
          {t("settings.search.domains.addButton")}
        </Button>
      </div>
      {error && (
        <p id={errorId} role="alert" className="text-sm text-destructive">
          {error}
        </p>
      )}
    </>
  );
}
