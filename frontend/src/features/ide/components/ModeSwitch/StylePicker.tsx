import { useId } from "react";
import { t } from "@/shared/i18n/t";
import type { PreferencesView } from "../viewTypes";

const STYLES = ["guide", "pair"] as const;

interface StylePickerProps {
  value: PreferencesView["style"];
  pending: boolean;
  onPick: (style: PreferencesView["style"]) => void;
}

/** The teacher's help style: two exclusive choices, each described. */
export function StylePicker({ value, pending, onPick }: StylePickerProps) {
  const name = useId();
  return (
    <fieldset className="flex flex-col gap-2">
      <legend className="text-sm font-medium">{t("ide.mode.style.title")}</legend>
      {STYLES.map((style) => (
        <label key={style} className="flex items-start gap-2 text-sm">
          <input
            type="radio"
            name={name}
            value={style}
            checked={value === style}
            aria-disabled={pending}
            onChange={() => !pending && onPick(style)}
            className="mt-1"
          />
          <span>
            {t(`ide.mode.style.${style}`)}
            <span className="block text-xs text-muted-foreground">
              {t(`ide.mode.style.${style}Hint`)}
            </span>
          </span>
        </label>
      ))}
    </fieldset>
  );
}
