import { readPresets, readTiers } from "./tierChoices";
import type { ApiKeyEntry, ModelsOut, SettingsOut, TierChoices } from "./types";

/** Ce que les clés lues permettent au premier lancement. */
export interface KeyPlan {
  /** Les seuls fournisseurs de modèles (`GET /settings/models`) : Brave n'en est pas un. */
  entries: ApiKeyEntry[];
  /** Les modèles ont une clé (telle quelle, ou une fois `tiers` écrits) : l'import du CV peut partir. */
  ready: boolean;
  /** Les niveaux à écrire en quittant l'étape de la clé ; `null` : rien à changer. */
  tiers: TierChoices | null;
  /** Le fournisseur sur lequel passent les modèles, quand `tiers` est écrit. */
  moveTo: string | null;
  /** Une clé existe mais aucun préréglage n'est celui de son fournisseur : à régler dans Modèles. */
  unmatched: string | null;
}

const providersOf = (tiers: TierChoices) =>
  new Set(Object.values(tiers).map((tier) => tier.provider));

/**
 * Une clé n'est utile que si elle est celle du fournisseur des niveaux de modèles : l'API de
 * lecture des clés liste aussi Brave, et les agents échouent (`llm_key_missing`) sans la clé de
 * leur fournisseur, sans repli sur un autre. Si les modèles n'ont pas de clé mais qu'un autre
 * fournisseur de modèles en a une, le préréglage de ce fournisseur (tous les niveaux chez lui) est
 * proposé ; faute de préréglage, on le dit et l'import n'est pas ouvert.
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
