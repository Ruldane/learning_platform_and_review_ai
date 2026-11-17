import { useId } from "react";
import { cn } from "@/shared/lib/utils";
import { fieldClass } from "@/shared/ui/fieldClass";

interface TextFieldProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  /** Absent : une ligne ; sinon une zone de texte de `rows` lignes. */
  rows?: number;
  mono?: boolean;
  maxLength?: number;
  hint?: string;
}

/** Un champ de formulaire avec son libellé (et, au besoin, une aide lue avec le champ). */
export function TextField({ label, value, onChange, rows, mono, maxLength, hint }: TextFieldProps) {
  const id = useId();
  const hintId = `${id}-hint`;
  const shared = {
    id,
    value,
    maxLength,
    "aria-describedby": hint ? hintId : undefined,
  };
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="text-sm font-medium">
        {label}
      </label>
      {rows ? (
        <textarea
          {...shared}
          rows={rows}
          onChange={(event) => onChange(event.target.value)}
          className={cn(fieldClass, "h-auto py-1.5", mono && "font-mono")}
        />
      ) : (
        <input
          {...shared}
          onChange={(event) => onChange(event.target.value)}
          className={fieldClass}
        />
      )}
      {hint ? (
        <p id={hintId} className="text-xs text-muted-foreground">
          {hint}
        </p>
      ) : null}
    </div>
  );
}
