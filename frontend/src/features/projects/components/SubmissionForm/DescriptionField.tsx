import { useId } from "react";
import { t } from "@/shared/i18n/t";
import { fieldClass } from "@/shared/ui/fieldClass";
import { characterCount, DESCRIPTION_MAX } from "./rules";

interface DescriptionFieldProps {
  value: string;
  disabled: boolean;
  error: string | undefined;
  onChange: (value: string) => void;
}

/** La description du rendu, avec son compteur « 12 / 4 000 caractères » et son erreur quand elle est trop longue. */
export function DescriptionField({ value, disabled, error, onChange }: DescriptionFieldProps) {
  const id = useId();
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-sm font-medium">
        {t("projects.submission.description")}
      </label>
      <textarea
        id={id}
        rows={6}
        value={value}
        disabled={disabled}
        aria-invalid={error !== undefined}
        aria-describedby={`${id}-count${error ? ` ${id}-error` : ""}`}
        onChange={(event) => onChange(event.target.value)}
        className={`${fieldClass} h-auto py-2`}
      />
      <p id={`${id}-count`} className="text-xs text-muted-foreground tabular-nums">
        {t("projects.submission.counter", {
          count: characterCount(value).toLocaleString("en-GB"),
          max: DESCRIPTION_MAX.toLocaleString("en-GB"),
        })}
      </p>
      {error ? (
        <p id={`${id}-error`} role="alert" className="text-sm text-destructive">
          {error}
        </p>
      ) : null}
    </div>
  );
}
