/**
 * Types d'affichage des composants de la feature. Les composants n'ont pas le droit d'importer
 * `types.ts` ni `shared/api` (règle de découpage) : ils décrivent donc ici, structurellement, ce
 * qu'ils reçoivent. `types.ts` vérifie à la compilation que les types générés les satisfont.
 */

export const TIERS = ["rapide", "standard", "fort", "vision"] as const;
export type Tier = (typeof TIERS)[number];

export const PRESET_NAMES = ["all_haiku", "haiku_sonnet_strong", "all_glm", "all_openai"] as const;
export type PresetName = (typeof PRESET_NAMES)[number];

export interface ModelChoice {
  provider: string;
  model: string;
}

/** Le modèle choisi pour chacun des quatre niveaux. */
export type TierChoices = Record<Tier, ModelChoice>;

export type PresetMap = Record<PresetName, TierChoices>;

/** Un fournisseur proposé dans les listes déroulantes (`models` nul : saisie libre). */
export interface ProviderOption {
  name: string;
  label: string;
  has_key: boolean;
  models: string[] | null;
}

/** Une clé telle qu'affichée : jamais en clair, seulement les 4 derniers caractères. */
export interface ApiKeyEntry {
  provider: string;
  label: string;
  source: "ui" | "env" | null;
  last4: string | null;
  readable: boolean;
  last_test_ok: boolean | null;
}

export interface KeyTestView {
  ok: boolean;
  message: string;
}
