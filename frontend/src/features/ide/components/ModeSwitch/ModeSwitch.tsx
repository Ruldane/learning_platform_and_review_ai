import { useId } from "react";
import { t } from "@/shared/i18n/t";
import { cn } from "@/shared/lib/utils";
import type { PreferencesView } from "../viewTypes";

interface ModeSwitchProps {
  preferences: PreferencesView;
  /** Une écriture est en cours : les réglages ne bougent plus avant la réponse. */
  pending: boolean;
  onChange: (next: PreferencesView) => void;
}

/**
 * Les deux réglages du professeur : intervenir tout seul après une erreur (sinon, seulement sur
 * demande) et, en option coupée par défaut, proposer de l'aide après 30 s sans bouger de ligne.
 */
export function ModeSwitch({ preferences, pending, onChange }: ModeSwitchProps) {
  const idleId = useId();
  const { auto, idle } = preferences;
  return (
    <fieldset className="flex flex-col gap-3 rounded-xl border border-border bg-card p-3">
      <legend className="px-1 text-sm font-medium">{t("ide.mode.title")}</legend>
      <div className="flex items-center gap-3">
        <button
          type="button"
          role="switch"
          aria-checked={auto}
          aria-disabled={pending}
          onClick={() => !pending && onChange({ auto: !auto, idle })}
          className={cn(
            "relative inline-flex h-6 w-11 shrink-0 items-center rounded-full border border-border outline-none transition-colors",
            "focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring aria-disabled:opacity-50",
            auto ? "bg-primary" : "bg-muted",
          )}
        >
          <span className="sr-only">{t("ide.mode.auto")}</span>
          <span
            aria-hidden="true"
            className={cn(
              "size-4 rounded-full bg-background shadow transition-transform",
              auto ? "translate-x-6" : "translate-x-1",
            )}
          />
        </button>
        <span className="text-sm font-medium">
          {auto ? t("ide.mode.autoOn") : t("ide.mode.autoOff")}
        </span>
      </div>
      <div className="flex items-start gap-2">
        <input
          id={idleId}
          type="checkbox"
          checked={idle}
          aria-disabled={pending}
          onChange={(event) => !pending && onChange({ auto, idle: event.target.checked })}
          className="mt-1"
        />
        <label htmlFor={idleId} className="text-sm">
          {t("ide.mode.idle")}
          <span className="block text-xs text-muted-foreground">{t("ide.mode.idleHint")}</span>
        </label>
      </div>
    </fieldset>
  );
}
