import type { components } from "@/shared/api/schema";
import type { ApiKeyEntry, ProviderOption } from "./components/viewTypes";

export { PRESET_NAMES, TIERS } from "./components/viewTypes";
export type {
  ApiKeyEntry,
  KeyTestView,
  PresetMap,
  PresetName,
  ProviderOption,
  Tier,
  TierChoices,
} from "./components/viewTypes";

type Schemas = components["schemas"];

export type ApiKeyOut = Schemas["ApiKeyOut"];
export type KeyTestResult = Schemas["KeyTestResult"];
export type ModelChoice = Schemas["ModelChoice"];
export type ModelsOut = Schemas["ModelsOut"];
export type ProviderModels = Schemas["ProviderModels"];
export type SettingsOut = Schemas["SettingsOut"];
export type UserSettings = Schemas["UserSettings"];

type Assert<T extends true> = T;

/** Vérifié à la compilation : les types générés satisfont les types d'affichage des composants. */
export type ViewTypesMatchContract = [
  Assert<ApiKeyOut extends ApiKeyEntry ? true : false>,
  Assert<ProviderModels extends ProviderOption ? true : false>,
];
