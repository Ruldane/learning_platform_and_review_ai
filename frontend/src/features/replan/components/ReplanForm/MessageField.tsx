import { useId } from "react";
import { t } from "@/shared/i18n/t";
import { cn } from "@/shared/lib/utils";
import { fieldClass } from "@/shared/ui/fieldClass";

/** Le contrat borne le message à 1 000 caractères. */
export const MAX_MESSAGE = 1000;

interface MessageFieldProps {
  value: string;
  disabled: boolean;
  onChange: (value: string) => void;
}

/** Le message facultatif pour le Stratège. */
export function MessageField({ value, disabled, onChange }: MessageFieldProps) {
  const id = useId();
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-sm font-medium">
        {t("replan.form.message")}
      </label>
      <textarea
        id={id}
        rows={3}
        value={value}
        maxLength={MAX_MESSAGE}
        disabled={disabled}
        aria-describedby={`${id}-hint`}
        onChange={(event) => onChange(event.target.value)}
        className={cn(fieldClass, "h-auto min-h-20 py-1.5")}
      />
      <p id={`${id}-hint`} className="text-xs text-muted-foreground">
        {t("replan.form.messageHint")}
      </p>
    </div>
  );
}
