import { t } from "@/shared/i18n/t";
import { PresetPicker } from "../PresetPicker";
import { TierModelTable } from "../TierModelTable";
import { VisionWarning } from "../VisionWarning";
import type {
  ModelChoice,
  PresetMap,
  PresetName,
  ProviderOption,
  Tier,
  TierChoices,
} from "../viewTypes";

interface TiersSectionProps {
  tiers: TierChoices;
  presets: PresetMap;
  providers: ProviderOption[];
  /** False if the vision level points to a model without vision. */
  visionEnabled: boolean;
  /** A save is in progress: the choices are disabled. */
  disabled: boolean;
  onApplyPreset: (name: PresetName) => void;
  onChangeTier: (tier: Tier, choice: ModelChoice) => void;
}

/** « Modèle par niveau » section: presets, vision warning and the levels table. */
export function TiersSection({
  tiers,
  presets,
  providers,
  visionEnabled,
  disabled,
  onApplyPreset,
  onChangeTier,
}: TiersSectionProps) {
  return (
    <section className="flex flex-col gap-3">
      <h2 className="text-lg font-medium">{t("settings.tiers.title")}</h2>
      <p className="text-muted-foreground">{t("settings.tiers.intro")}</p>
      <PresetPicker presets={presets} current={tiers} disabled={disabled} onApply={onApplyPreset} />
      <VisionWarning visible={!visionEnabled} />
      <TierModelTable
        tiers={tiers}
        providers={providers}
        disabled={disabled}
        onChange={onChangeTier}
      />
    </section>
  );
}
