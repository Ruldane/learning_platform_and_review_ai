import { readPresets, readTiers } from "./tierChoices";
import type { ApiKeyEntry, ModelsOut, SettingsOut, TierChoices } from "./types";

/** What the keys read allow for the first run. */
export interface KeyPlan {
  /** The only model providers (`GET /settings/models`): Brave is not one. */
  entries: ApiKeyEntry[];
  /** The models have a key (as is, or once `tiers` is written): the CV import can go ahead. */
  ready: boolean;
  /** The levels to write when leaving the key step; `null`: nothing to change. */
  tiers: TierChoices | null;
  /** The provider the models move to, when `tiers` is written. */
  moveTo: string | null;
  /** A key exists but no preset matches its provider: to set in Models. */
  unmatched: string | null;
}

const providersOf = (tiers: TierChoices) =>
  new Set(Object.values(tiers).map((tier) => tier.provider));

/**
 * A key is only useful if it belongs to the model levels' provider: the key-read API
 * also lists Brave, and agents fail (`llm_key_missing`) without the key of
 * their provider, with no fallback to another. If the models have no key but another
 * model provider has one, its preset (all levels on it) is offered;
 * without a preset, we say so and the import is not opened.
 */
export function planKeys(
  allKeys: ApiKeyEntry[],
  models: ModelsOut,
  settings: SettingsOut,
): KeyPlan {
  const llm = new Set(models.providers.map((provider) => provider.name));
  const entries = allKeys.filter((entry) => llm.has(entry.provider));
  const keyed = entries.filter((entry) => entry.source !== null && entry.readable);
  const keyedNames = new Set(keyed.map((entry) => entry.provider));
  const current = readTiers(settings.tiers);
  const base = { entries, tiers: null, moveTo: null, unmatched: null };
  if ([...providersOf(current)].every((provider) => keyedNames.has(provider))) {
    return { ...base, ready: true };
  }
  const presets = Object.values(readPresets(models.presets));
  for (const entry of keyed) {
    const preset = presets.find((tiers) =>
      [...providersOf(tiers)].every((p) => p === entry.provider),
    );
    if (preset) return { ...base, ready: true, tiers: preset, moveTo: entry.label };
  }
  return { ...base, ready: false, unmatched: keyed[0]?.label ?? null };
}
