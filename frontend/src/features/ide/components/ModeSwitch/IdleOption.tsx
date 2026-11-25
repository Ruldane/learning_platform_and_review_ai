import { useId } from "react";
import { t } from "@/shared/i18n/t";

interface IdleOptionProps {
  checked: boolean;
  pending: boolean;
  onToggle: (checked: boolean) => void;
}

/** The « aide après 30 s sans bouger de ligne » option (off by default: each call costs). */
export function IdleOption({ checked, pending, onToggle }: IdleOptionProps) {
  const id = useId();
  return (
    <div className="flex items-start gap-2">
      <input
        id={id}
        type="checkbox"
        checked={checked}
        aria-disabled={pending}
        onChange={(event) => !pending && onToggle(event.target.checked)}
        className="mt-1"
      />
      <label htmlFor={id} className="text-sm">
        {t("ide.mode.idle")}
        <span className="block text-xs text-muted-foreground">{t("ide.mode.idleHint")}</span>
      </label>
    </div>
  );
}
