import { PRESET_NAMES, TIERS } from "./types";
import type { ModelChoice, PresetMap, TierChoices } from "./types";

type RawChoices = Record<string, ModelChoice | undefined> | undefined;

const EMPTY_CHOICE: ModelChoice = { provider: "", model: "" };

/** The four levels, from the contract (free keys) to a complete record. */
export function readTiers(raw: RawChoices): TierChoices {
  const pick = (tier: (typeof TIERS)[number]) => raw?.[tier] ?? EMPTY_CHOICE;
  return {
    fast: pick("fast"),
    standard: pick("standard"),
    strong: pick("strong"),
    vision: pick("vision"),
  };
}

/** The four presets of the contract, each with its four levels. */
export function readPresets(raw: Record<string, RawChoices>): PresetMap {
  const entries = PRESET_NAMES.map((name) => [name, readTiers(raw[name])] as const);
  return Object.fromEntries(entries) as PresetMap;
}
