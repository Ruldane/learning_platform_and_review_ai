import { PRESET_NAMES, TIERS } from "../viewTypes";
import type { PresetMap, PresetName, TierChoices } from "../viewTypes";

/** Préréglage dont chaque niveau a le même fournisseur et le même modèle, sinon `null`. */
export function matchPreset(current: TierChoices, presets: PresetMap): PresetName | null {
  return (
    PRESET_NAMES.find((name) =>
      TIERS.every(
        (tier) =>
          presets[name][tier].provider === current[tier].provider &&
          presets[name][tier].model === current[tier].model,
      ),
    ) ?? null
  );
}
