import { t } from "@/shared/i18n/t";
import { cn } from "@/shared/lib/utils";
import { Button } from "@/shared/ui/button";
import { PRESET_NAMES } from "../viewTypes";
import type { PresetMap, PresetName, TierChoices } from "../viewTypes";
import { matchPreset } from "./matchPreset";

interface PresetPickerProps {
  presets: PresetMap;
  /** Choix actuels des quatre niveaux : sert à repérer le préréglage en vigueur. */
  current: TierChoices;
  onApply: (name: PresetName) => void;
  disabled?: boolean;
}

/** Préréglages en un clic ; « Personnalisé » est l'état affiché hors préréglage. */
export function PresetPicker({ presets, current, onApply, disabled = false }: PresetPickerProps) {
  const active = matchPreset(current, presets);
  return (
    <div role="group" aria-label={t("settings.presets.label")} className="flex flex-wrap gap-2">
      {PRESET_NAMES.map((name) => (
        <Button
          key={name}
          variant={active === name ? "default" : "outline"}
          aria-pressed={active === name}
          disabled={disabled}
          onClick={() => onApply(name)}
        >
          {t(`settings.presets.${name}`)}
        </Button>
      ))}
      <span
        aria-current={active === null ? "true" : undefined}
        className={cn(
          "inline-flex h-8 items-center rounded-lg border px-2.5 text-sm",
          active === null
            ? "border-primary bg-secondary font-medium"
            : "border-dashed border-border text-muted-foreground",
        )}
      >
        {t("settings.presets.custom")}
      </span>
    </div>
  );
}
