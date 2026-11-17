import { useId } from "react";
import { t } from "@/shared/i18n/t";
import type { FeatureOption } from "../viewTypes";

interface FeaturePickerProps {
  options: FeatureOption[];
  selected: readonly string[];
  onToggle: (feature: string) => void;
}

/** Les features que le jeton peut voir : aucune de cochée au départ, on ouvre ce qu'on choisit. */
export function FeaturePicker({ options, selected, onToggle }: FeaturePickerProps) {
  const prefix = useId();
  return (
    <fieldset className="flex flex-col gap-2">
      <legend className="text-sm font-medium">{t("mcp.form.features")}</legend>
      <p className="text-sm text-muted-foreground">{t("mcp.form.featuresHint")}</p>
      {options.length === 0 ? (
        <p className="text-sm text-muted-foreground">{t("mcp.form.noFeatures")}</p>
      ) : null}
      <ul className="grid gap-2 sm:grid-cols-2">
        {options.map((option) => (
          <li key={option.id} className="flex items-start gap-2">
            <input
              id={`${prefix}-${option.id}`}
              type="checkbox"
              className="mt-1"
              checked={selected.includes(option.id)}
              aria-describedby={`${prefix}-${option.id}-counts`}
              onChange={() => onToggle(option.id)}
            />
            <div className="flex flex-col">
              <label htmlFor={`${prefix}-${option.id}`} className="text-sm font-medium">
                {option.label}
              </label>
              <span id={`${prefix}-${option.id}-counts`} className="text-xs text-muted-foreground">
                {t("mcp.form.featureCounts", {
                  read: option.read,
                  write: option.write,
                  confirm: option.confirm,
                })}
              </span>
            </div>
          </li>
        ))}
      </ul>
    </fieldset>
  );
}
