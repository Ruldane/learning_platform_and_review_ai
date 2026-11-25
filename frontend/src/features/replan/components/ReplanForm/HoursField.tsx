import { useId } from "react";
import { t } from "@/shared/i18n/t";
import { cn } from "@/shared/lib/utils";
import { fieldClass } from "@/shared/ui/fieldClass";

interface HoursFieldProps {
  value: string;
  invalid: boolean;
  disabled: boolean;
  onChange: (value: string) => void;
}

/**
 * The week's hours field (the back end reads a total, including hours already done): its
 * hint becomes the error when the input is refused.
 */
export function HoursField({ value, invalid, disabled, onChange }: HoursFieldProps) {
  const id = useId();
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-sm font-medium">
        {t("replan.form.hours")}
      </label>
      <input
        id={id}
        type="text"
        inputMode="decimal"
        value={value}
        disabled={disabled}
        aria-invalid={invalid}
        aria-describedby={`${id}-hint`}
        onChange={(event) => onChange(event.target.value)}
        className={cn(fieldClass, "max-w-40")}
      />
      <p
        id={`${id}-hint`}
        className={cn("text-xs", invalid ? "text-destructive" : "text-muted-foreground")}
      >
        {invalid ? t("replan.form.hoursInvalid") : t("replan.form.hoursHint")}
      </p>
    </div>
  );
}
