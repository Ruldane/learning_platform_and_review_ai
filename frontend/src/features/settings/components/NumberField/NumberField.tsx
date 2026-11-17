import { useId } from "react";
import { t } from "@/shared/i18n/t";
import { fieldClass } from "@/shared/ui/fieldClass";
import { errorHint } from "../errorHint";

interface NumberFieldProps {
  label: string;
  /** Du texte : la saisie peut être vide ou incomplète sans que le champ la réécrive. */
  value: string;
  min?: number;
  max?: number;
  /** Les bornes dites sous le champ ; par défaut « Entre {min} et {max}. ». */
  hint?: string;
  /** Hors bornes (rouge, `aria-invalid`). */
  invalid: boolean;
  /** Refusé par le serveur : la valeur n'est jamais citée, seulement le champ. */
  refused?: boolean;
  /** Identifiant d'un message de plus qui décrit ce champ (ex. l'ordre des deux bornes). */
  describedBy?: string;
  onChange: (value: string) => void;
}

function rangeHint(min?: number, max?: number): string {
  return min !== undefined && max !== undefined ? t("settings.fields.range", { min, max }) : "";
}

/** Un nombre entier avec ses bornes dites sous le champ (rouges quand elles sont dépassées). */
export function NumberField({
  label,
  value,
  min,
  max,
  hint,
  invalid,
  refused = false,
  describedBy,
  onChange,
}: NumberFieldProps) {
  const hintId = useId();
  const bad = invalid || refused;
  const text = errorHint(
    bad,
    refused && !invalid ? t("settings.fields.refused") : (hint ?? rangeHint(min, max)),
  );
  return (
    <div className="flex flex-col gap-1">
      <label className="text-sm font-medium">
        {label}
        <input
          type="number"
          inputMode="numeric"
          min={min}
          max={max}
          step={1}
          value={value}
          aria-invalid={bad}
          aria-describedby={describedBy ? `${hintId} ${describedBy}` : hintId}
          onChange={(event) => onChange(event.target.value)}
          className={`${fieldClass} mt-1 max-w-40`}
        />
      </label>
      <p id={hintId} className={bad ? "text-sm text-destructive" : "text-sm text-muted-foreground"}>
        {text}
      </p>
    </div>
  );
}
