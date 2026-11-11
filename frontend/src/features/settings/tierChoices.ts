import { PRESET_NAMES, TIERS } from "./types";
import type { ModelChoice, PresetMap, TierChoices } from "./types";

type RawChoices = Record<string, ModelChoice | undefined> | undefined;

const EMPTY_CHOICE: ModelChoice = { provider: "", model: "" };

/** Les quatre niveaux, du contrat (clés libres) vers un enregistrement complet. */
export function readTiers(raw: RawChoices): TierChoices {
  const pick = (tier: (typeof TIERS)[number]) => raw?.[tier] ?? EMPTY_CHOICE;
  return {
    rapide: pick("rapide"),
    standard: pick("standard"),
    fort: pick("fort"),
    vision: pick("vision"),
  };
}

/** Les quatre préréglages du contrat, chacun avec ses quatre niveaux. */
export function readPresets(raw: Record<string, RawChoices>): PresetMap {
  const entries = PRESET_NAMES.map((name) => [name, readTiers(raw[name])] as const);
  return Object.fromEntries(entries) as PresetMap;
}
