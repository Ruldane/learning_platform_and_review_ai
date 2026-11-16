import { useId } from "react";
import { t } from "@/shared/i18n/t";
import { fieldClass } from "@/shared/ui/fieldClass";

interface RepoUrlFieldProps {
  value: string;
  disabled: boolean;
  error: string | undefined;
  onChange: (value: string) => void;
}

/** Le lien du dépôt : une adresse http(s) de 2 048 caractères au plus, son indication et son erreur. */
export function RepoUrlField({ value, disabled, error, onChange }: RepoUrlFieldProps) {
  const id = useId();
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-sm font-medium">
        {t("projects.submission.repoUrl")}
      </label>
      <input
        id={id}
        type="text"
        inputMode="url"
        value={value}
        disabled={disabled}
        aria-invalid={error !== undefined}
        aria-describedby={`${id}-hint${error ? ` ${id}-error` : ""}`}
        onChange={(event) => onChange(event.target.value)}
        className={fieldClass}
      />
      <p id={`${id}-hint`} className="text-xs text-muted-foreground">
        {t("projects.submission.repoUrlHint")}
      </p>
      {error ? (
        <p id={`${id}-error`} role="alert" className="text-sm text-destructive">
          {error}
        </p>
      ) : null}
    </div>
  );
}
