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
  /** Faux si le niveau vision pointe vers un modèle sans vision. */
  visionEnabled: boolean;
  /** Un enregistrement est en cours : les choix sont désactivés. */
  disabled: boolean;
  onApplyPreset: (name: PresetName) => void;
  onChangeTier: (tier: Tier, choice: ModelChoice) => void;
}

/** Section « Modèle par niveau » : préréglages, avertissement vision et tableau des niveaux. */
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
